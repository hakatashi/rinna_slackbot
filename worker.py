# coding=utf8

from threading import Lock
import time
import random
import traceback
from slack_sdk import WebClient
import json
import re
import signal
from dotenv import load_dotenv
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1, language_v1
import firebase_admin
from firebase_admin import firestore
import os
import sys
from io import BytesIO
from datetime import datetime
from azure.cognitiveservices.vision.contentmoderator import ContentModeratorClient
from msrest.authentication import CognitiveServicesCredentials
from time import sleep
from rinna.utils import has_offensive_term
from rinna.generation import generate_rinna_response, generate_rinna_meaning
from rinna.configs import character_configs

load_dotenv()

mutex = Lock()

slack_client = WebClient(token=os.environ['SLACK_TOKEN'])
language_client = language_v1.LanguageServiceClient()
content_moderator_client = ContentModeratorClient(
    endpoint=os.environ['CONTENT_MODERATOR_ENDPOINT'],
    credentials=CognitiveServicesCredentials(
        os.environ['CONTENT_MODERATOR_SUBSCRIPTION_KEY'])
)

app = firebase_admin.initialize_app()
db = firestore.client()

responses_ref = db.collection(u'rinna-responses')

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

    speech_chunks, info = generate_rinna_response(messages, character)

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

        api_response = slack_client.chat_postMessage(
            text=rinna_message,
            channel='C7AAX50QY',
            icon_url=character_config['slack_user_icon'],
            username=character_config['slack_user_name']
        )

        responses_ref.add({
            'createdAt': datetime.now(),
            'character': character,
            'inputMessages': messages,
            'inputText': info['text_input'],
            'inputDialog': info['formatted_dialog'],
            'inputTokenLength': info['input_len'],
            'output': info['output'],
            'outputSpeech': info['rinna_speech'],
            'config': info['config'],
            'message': api_response.data,
            'moderations': moderations,
        })

    return speech_chunks

def rinna_meaning(word, ts = None, character = 'うな', dry_run = False):
    character_config = character_configs[character]

    if 'meaning_intro' not in character_config:
        return None

    slack_username = character_config['slack_user_name']

    speech_chunks, info = generate_rinna_meaning(character, word)

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

        api_response = slack_client.chat_postMessage(**post_message_kwargs)

        responses_ref.add({
            'createdAt': datetime.now(),
            'character': character,
            'inputMessages': [],
            'inputText': info['text_input'],
            'inputDialog': '',
            'inputTokenLength': info['input_len'],
            'output': info['output'],
            'outputSpeech': info['rinna_speech'],
            'config': info['config'],
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
    print(f'received rinna-signal: {data.get("type")} (lastSignal = {data.get("lastSignal")})')

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