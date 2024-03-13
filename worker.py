# coding=utf8

from threading import Lock
import time
import random
import traceback
from slack_sdk import WebClient
import json
import re
import regex
import signal
from dotenv import load_dotenv
import torch
from pathlib import Path
from transformers import T5Tokenizer, AutoModelForCausalLM
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1, language_v1
from data.intro import rinna_intro, rinna_inquiry_intro, una_intro, uka_intro, uno_intro, una_inquiry_intro, tatamo_intro, una_meaning_intro
from data.users import username_mapping
import firebase_admin
from firebase_admin import firestore
import os
import sys
from io import BytesIO
from datetime import datetime
from azure.cognitiveservices.vision.contentmoderator import ContentModeratorClient
from msrest.authentication import CognitiveServicesCredentials
from time import sleep
from typing import Any

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-application-credentials.json'

MODERATION_ALLOWLIST = ['えた', 'クリ']

load_dotenv()

mutex = Lock()

client = WebClient(token=os.environ['SLACK_TOKEN'])
language_client = language_v1.LanguageServiceClient()
content_moderator_client = ContentModeratorClient(
    endpoint=os.environ['CONTENT_MODERATOR_ENDPOINT'],
    credentials=CognitiveServicesCredentials(
        os.environ['CONTENT_MODERATOR_SUBSCRIPTION_KEY'])
)


app = firebase_admin.initialize_app()
db = firestore.client()

responses_ref = db.collection(u'rinna-responses')

tokenizer = T5Tokenizer.from_pretrained("rinna/japanese-gpt-1b")
model = AutoModelForCausalLM.from_pretrained("rinna/japanese-gpt-1b")

if torch.cuda.is_available() and sys.argv[1] == 'GPU':
    model = model.to("cuda")
    pass

print(f'Using {model.device} for processing rinna-signal')

character_configs = {
    'りんな': {
        'intro': rinna_intro,
        'inquiry_intro': rinna_inquiry_intro,
        'name_in_text': 'りんな',
        'slack_user_name': 'りんな',
        'slack_user_icon': 'https://huggingface.co/rinna/japanese-gpt-1b/resolve/main/rinna.png',
    },
    'うな': {
        'intro': una_intro,
        'inquiry_intro': una_inquiry_intro,
        'meaning_intro': una_meaning_intro,
        'name_in_text': 'ウナ',
        'slack_user_name': '今言うな',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/una_icon.png',
    },
    'うか': {
        'intro': uka_intro,
        'name_in_text': 'ウカ',
        'slack_user_name': '皿洗うか',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/uka_icon_edit.png',
    },
    'うの': {
        'intro': uno_intro,
        'name_in_text': 'ウノ',
        'slack_user_name': '皿洗うの',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/uno_icon.png',
    },
    'たたも': {
        'intro': tatamo_intro,
        'name_in_text': 'タタモ',
        'slack_user_name': '三脚たたも',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/user03.png',
    },
}

def get_weekday_str(weekday):
    return '月火水木金土日'[weekday]

def get_hour_str(hour):
    if hour <= 12:
        return f'午前{hour}'
    else:
        return f'午後{hour - 12}'

def normalize_text(text):
    text = re.sub(r'@りんな', '', text)
    text = re.sub(r'@うな', '', text)
    text = re.sub(r'@うか', '', text)
    text = re.sub(r'@うの', '', text)
    text = re.sub(r'@たたも', '', text)
    text = regex.sub(r'[\p{Ps}\p{Pe}\r\n]+', ' ', text)
    text = re.sub(r'<.+?>', '', text)
    text = re.sub(r'ワシ', '儂', text)
    text = re.sub(r'今言うな', 'ウナ', text)
    text = re.sub(r'皿洗うか', 'ウカ', text)
    text = re.sub(r'皿洗うの', 'ウノ', text)
    text = re.sub(r'三脚たたも', 'タタモ', text)

    for name, new_name in [('うな', 'ウナ'), ('うか', 'ウカ'), ('うの', 'ウノ'), ('たたも', 'タタモ')]:
        text = re.sub(f'^{name}', new_name, text)
        text = re.sub(f'{name}$', new_name, text)
        text = re.sub(f'{name}([はがのを])', f'{new_name}\\1', text)

    text = text.strip()

    return text

def has_offensive_term(terms):
    if terms is None:
        return False
    return any(map(lambda term: term.term not in MODERATION_ALLOWLIST, terms))

def moderate_message(message):
    document = language_v1.Document(
        content=message,
        type_=language_v1.Document.Type.PLAIN_TEXT,
        language="JA",
    )

    classification = language_client.classify_text(
        request={
            "document": document,
            "classification_model_options": {
                "v2_model": {
                    "content_categories_version": "V2",
                },
            },
        },
    )

    is_adult = any(map(lambda category: category.name == '/Adult', classification.categories))

    screen = content_moderator_client.text_moderation.screen_text(
        text_content_type='text/plain',
        text_content=BytesIO(message.encode()),
        language='jpn',
        autocorrect=False,
        pii=False,
        classify=False
    )

    is_offensive = has_offensive_term(screen.terms)

    moderations = {
        'google_language_service': classification._meta.parent.to_dict(classification),
        'azure_content_moderator': screen.as_dict(),
    }

    return is_adult or is_offensive, moderations

def rinna_response(messages, character, dry_run=False):
    character_config = character_configs[character]
    name_in_text = character_config['name_in_text']

    last_message_text = messages[-1]['text'] or ''
    is_inquiry = last_message_text.endswith('？') or last_message_text.endswith('?')

    print(f'{is_inquiry = }')

    token_ids_output: Any = None
    if is_inquiry and 'inquiry_intro' in character_config:
        formatted_dialog = f'質問「{last_message_text}」'
        text_input = character_config['inquiry_intro'] + '\n' + formatted_dialog + '\n' + '回答「'
        token_ids_output = tokenizer.encode(
            text_input, add_special_tokens=False, return_tensors="pt")
    else:
        formatted_messages = []
        for message in messages:
            if message['text'] is None:
                continue

            text = normalize_text(message['text'])

            if text == '':
                continue

            if message.get('bot_id') == 'BEHP604TV' and message.get('username') == '今言うな':
                user = 'ウナ'
            elif message.get('bot_id') == 'BEHP604TV' and message.get('username') == 'りんな':
                user = 'りんな'
            elif message.get('bot_id') == 'BEHP604TV' and message.get('username') == '皿洗うか':
                user = 'ウカ'
            elif message.get('bot_id') == 'BEHP604TV' and message.get('username') == '皿洗うの':
                user = 'ウノ'
            elif message.get('bot_id') == 'BEHP604TV' and message.get('username') == '三脚たたも':
                user = 'タタモ'
            elif message.get('user') in username_mapping:
                user = username_mapping[message.get('user')]
            else:
                user = message.get('user')

            if len(formatted_messages) >= 1 and formatted_messages[-1]['user'] == user:
                last_text: str = formatted_messages[-1]['text']
                if re.search(r'[!?！？。｡、､]$', last_text) is not None:
                    formatted_messages[-1]['text'] = last_text + ' ' + text
                else:
                    formatted_messages[-1]['text'] = last_text + '。' + text
            else:
                formatted_messages.append({
                    'text': text,
                    'user': user,
                })
        
        token_ids_output = None
        formatted_messages_bin = []

        formatted_messages.reverse()
        text_input = ''
        formatted_dialog = ''

        for formatted_message in formatted_messages:
            formatted_messages_bin.insert(0, formatted_message)

            formatted_dialog = '\n'.join(map(
                lambda message: message['user'] + '「' + message['text'] + '」', formatted_messages_bin))

            text_input = character_config['intro'] + '\n\n' + formatted_dialog + f'\n{name_in_text}「'

            date = datetime.now()

            text_input = text_input.replace(r'[MONTH]', str(date.month))
            text_input = text_input.replace(r'[DATE]', str(date.day))
            text_input = text_input.replace(r'[WEEKDAY]', get_weekday_str(date.weekday()))
            text_input = text_input.replace(r'[HOUR]', get_hour_str(date.hour))
            text_input = text_input.replace(r'[MINUTE]', str(date.minute))
            text_input = text_input.replace(r'[WEATHER]', 'くもり')

            token_ids = tokenizer.encode(
                text_input, add_special_tokens=False, return_tensors="pt")
            input_len = len(token_ids[0])

            if input_len > 920:
                break
            else:
                token_ids_output = token_ids

    if token_ids_output is None:
        print('token_ids_output is empty. Quitting...')
        return ''

    input_len = len(token_ids_output[0])
    print(f'{input_len = }')

    config = {
        'do_sample': True,
        'top_k': 500,
        'top_p': 1.0,
        'temperature': 0.8,
        'repetition_penalty': 1.05,
        'pad_token_id': tokenizer.pad_token_id,
        'bos_token_id': tokenizer.bos_token_id,
        'eos_token_id': tokenizer.eos_token_id,
        # bad_word_ids=[[tokenizer.unk_token_id]]
    }

    with torch.no_grad():
        output_ids = model.generate(
            token_ids_output.to(model.device),
            max_length=input_len + 100,
            min_length=input_len + 100,
            **config,
        )

    output = tokenizer.decode(output_ids.tolist()[0][input_len:])

    rinna_speech = output.split('」')[0]
    rinna_speech = rinna_speech.replace('[UNK]', '')
    rinna_speech = rinna_speech.replace('『', '「')
    rinna_speech = rinna_speech.replace('』', '」')
    rinna_speech = rinna_speech.replace('ウナ', 'うな')
    rinna_speech = rinna_speech.replace('ウカ', 'うか')
    rinna_speech = rinna_speech.replace('ウノ', 'うの')
    rinna_speech = rinna_speech.replace('タタモ', 'たたも')
    if character == 'たたも':
        rinna_speech = rinna_speech.replace('ワシ', '儂')

    speech_chunks = re.findall(r"[^!?！？♪｡。]*[!?！？♪｡。]*", rinna_speech)

    for rinna_message in speech_chunks:
        if len(rinna_message) == 0:
            continue

        if rinna_message.endswith('。') and not re.match(r'。{2,}$', rinna_message):
            rinna_message = re.sub(r'。$', '', rinna_message)

        sleep(1)
        is_censored, moderations = moderate_message(rinna_message)

        if is_censored:
            rinna_message = '##### CENSORED #####'

        if dry_run:
            print(f'Output: {rinna_message}')
            continue

        api_response = client.chat_postMessage(
            text=rinna_message,
            channel='C7AAX50QY',
            icon_url=character_config['slack_user_icon'],
            username=character_config['slack_user_name']
        )

        responses_ref.add({
            'createdAt': datetime.now(),
            'character': character,
            'inputMessages': messages,
            'inputText': text_input,
            'inputDialog': formatted_dialog,
            'inputTokenLength': input_len,
            'output': output,
            'outputSpeech': rinna_speech,
            'config': config,
            'message': api_response.data,
            'moderations': moderations,
        })

    return rinna_speech

def rinna_meaning(word, ts = None, character = 'うな', dry_run = False):
    # print(f'rinna_meaning({word = }, {character = })')

    character_config = character_configs[character]

    if 'meaning_intro' not in character_config:
        return None

    character_name = character_config['name_in_text']
    slack_username = character_config['slack_user_name']

    inquiry_message = f'ひでお「{character_name}、『{word}』ってわかる？」'
    response_message = f'{character_name}「『{word}』っていうのは、'

    text_input = character_config['meaning_intro'] + '\n' + inquiry_message + '\n' + response_message

    token_ids = tokenizer.encode(
        text_input, add_special_tokens=False, return_tensors="pt")
    input_len = len(token_ids[0])

    print(f'{input_len = }')
    if input_len > 920:
        return None

    config = {
        'do_sample': True,
        'top_k': 500,
        'top_p': 1.0,
        'temperature': 0.8,
        'repetition_penalty': 1.05,
        'pad_token_id': tokenizer.pad_token_id,
        'bos_token_id': tokenizer.bos_token_id,
        'eos_token_id': tokenizer.eos_token_id,
        # bad_word_ids=[[tokenizer.unk_token_id]]
    }

    with torch.no_grad():
        output_ids = model.generate(
            token_ids.to(model.device),
            max_length=input_len + 100,
            min_length=input_len + 100,
            **config,
        )

    output = tokenizer.decode(output_ids.tolist()[0][input_len:])

    rinna_speech = output.split('」')[0]
    rinna_speech = rinna_speech.replace('[UNK]', '')
    rinna_speech = rinna_speech.replace('『', '「')
    rinna_speech = rinna_speech.replace('』', '」')
    rinna_speech = rinna_speech.replace('ウナ', 'うな')
    rinna_speech = rinna_speech.replace('ウカ', 'うか')
    rinna_speech = rinna_speech.replace('ウノ', 'うの')
    rinna_speech = rinna_speech.replace('タタモ', 'たたも')
    if character == 'たたも':
        rinna_speech = rinna_speech.replace('ワシ', '儂')

    speech_chunks = re.findall(r"[^!?！？♪｡。]*[!?！？♪｡。]*", rinna_speech)

    for i, rinna_message in enumerate(speech_chunks):
        if len(rinna_message) == 0:
            continue

        if rinna_message.endswith('。') and not re.match(r'。{2,}$', rinna_message):
            rinna_message = re.sub(r'。$', '', rinna_message)

        if i == 0:
            rinna_message = f'{word}っていうのは、{rinna_message}'

        sleep(1)
        is_censored, moderations = moderate_message(rinna_message)

        if is_censored:
            rinna_message = '##### CENSORED #####'

        if dry_run:
            print(f'Output: {rinna_message}')
            continue

        post_message_kwargs = {
            'text': rinna_message,
            'channel': 'C7AAX50QY',
            'icon_url': character_config['slack_user_icon'],
            'username': f'おじさんが役に立たないときに助けてくれる{slack_username}',
        }

        if ts is not None:
            post_message_kwargs['thread_ts'] = ts
            post_message_kwargs['reply_broadcast'] = True

        api_response = client.chat_postMessage(**post_message_kwargs)

        responses_ref.add({
            'createdAt': datetime.now(),
            'character': character,
            'inputMessages': [],
            'inputText': text_input,
            'inputDialog': '',
            'inputTokenLength': input_len,
            'output': output,
            'outputSpeech': rinna_speech,
            'config': config,
            'message': api_response.data,
            'moderations': moderations,
        })

'''
for word in ['拙斎詩鈔', '太平洋諸島フォーラム', '備後の山中', '十把', 'クラスター', '死亡時画像診断', '耐えうる', '厄払いの図柄', 'アバイ', '自然エネルギー', 'RPS法', '徘徊したがる']:
    rinna_meaning(word, None, 'うな', True)

for i in range(10):
    print(rinna_response([
        {
            'user': 'U04G7TL4P',
            'text': 'たたもって何歳なんだろう',
        },
    ], 'たたも', True))

sys.exit()
'''

project_id = "hakatabot-firebase-functions"
subscription_id = "rinna-signal"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

publisher = pubsub_v1.PublisherClient()


def pubsub_callback(message) -> None:
    data_buf = message.data
    data = json.loads(data_buf.decode())
    print('received rinna-signal')

    if 'humanMessages' in data and data['type'] == 'rinna-signal' and isinstance(data['humanMessages'], list):
        mutex.acquire()

        trigger_text = data['humanMessages'][-1]['text']
        rinna_triggered = False

        try:
            if '@うな先生' in trigger_text:
                word = re.sub(r'^@うな先生', '', trigger_text)
                word = word.strip()
                response = rinna_meaning(word, None, 'うな')

            else:
                if 'りんな' in trigger_text:
                    response = rinna_response(data['humanMessages'], 'りんな')
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': 'りんな',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'うな' in trigger_text:
                    response = rinna_response(data['humanMessages'], 'うな')
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '今言うな',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'うか' in trigger_text:
                    response = rinna_response(data['humanMessages'], 'うか')
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '皿洗うか',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'うの' in trigger_text:
                    response = rinna_response(data['humanMessages'], 'うの')
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '皿洗うの',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'たたも' in trigger_text:
                    response = rinna_response(data['humanMessages'], 'たたも')
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '三脚たたも',
                        'text': response,
                    })
                    rinna_triggered = True

                if not rinna_triggered:
                    if '皿洗' in trigger_text:
                        character = random.choice(['うか', 'うの'])
                    else:
                        print('random.choice')
                        character = random.choice(['りんな', 'うな', 'うか', 'うの', 'たたも'])
                        print(f'character = {character}')
                    rinna_response(data['humanMessages'], character)

            message.ack()

        except Exception as e:
            traceback.print_exc()
            print(e)

        finally:
            mutex.release()

    if data['type'] == 'rinna-meaning':
        mutex.acquire()

        try:
            rinna_meaning(data.get('word'), data.get('ts'), 'うな')
            message.ack()

        except Exception as e:
            traceback.print_exc()
            print(e)

        finally:
            mutex.release()

    if data['type'] == 'rinna-ping':
        topic_id = data['topicId']
        ts = int(topic_id.split('-')[-1])
        current_time = time.time() * 1000
        if current_time - ts > 1000 * 20:
            print(f'Ignoring old ping: {topic_id}')
        else:
            topic_path = publisher.topic_path(project_id, topic_id)
            publish_future = publisher.publish(topic_path, json.dumps({
                'type': 'rinna-pong',
                'mode': sys.argv[1],
            }).encode())

            print(publish_future.result())

        message.ack()


streaming_pull_future = subscriber.subscribe(subscription_path, callback=pubsub_callback)
def cancel(signum, frame):
    print('Received signal', signum)
    streaming_pull_future.cancel()
signal.signal(signal.SIGINT, cancel)
signal.signal(signal.SIGTERM, cancel)

print(f"Listening for messages on {subscription_path}..\n")

with subscriber:
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()