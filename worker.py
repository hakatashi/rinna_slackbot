# coding=utf8

from threading import Lock
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
from time import time, sleep
from rinna.utils import has_offensive_term
from rinna.generation import generate_rinna_response, generate_rinna_meaning
from rinna.configs import character_configs
# from rinna.llm_benchmark import score_response, update_form_scores
from concurrent.futures import ThreadPoolExecutor
import string
from logging import getLogger

logger = getLogger(__name__)

logger.info('Worker started')

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

    def classify_text():
        logger.info(f'Google moderation text: {message}')
        start_time = time()
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
        end_time = time()
        logger.info(
            f"Google moderation finished. Time taken: {end_time - start_time} seconds")
        return any(map(lambda category: category.name == '/Adult', classification.categories)), classification._meta.parent.to_dict(classification)

    def screen_text():
        logger.info(f'Azure moderation text: {message}')
        start_time = time()
        screen = content_moderator_client.text_moderation.screen_text(
            text_content_type='text/plain',
            text_content=BytesIO(message.encode()),
            language='jpn',
            autocorrect=False,
            pii=False,
            classify=False
        )
        end_time = time()
        logger.info(
            f"Azure moderation finished. Time taken: {end_time - start_time} seconds")
        return has_offensive_term(screen.terms), screen.as_dict()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_classify_text = executor.submit(classify_text)
        future_screen_text = executor.submit(screen_text)

        is_adult, classification = future_classify_text.result()
        is_offensive, screen = future_screen_text.result()

    moderations = {
        'google_language_service': classification,
        'azure_content_moderator': screen,
    }

    return is_adult or is_offensive, moderations


def rinna_response(messages, character, dry_run=False, thread_ts=None):
    character_config = character_configs[character]
    logger.info(f'thread_ts = {thread_ts}')

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
            logger.info(f'Output: {rinna_message}')
            continue

        if thread_ts is None:
            thread_options = {}
        else:
            thread_options = {
                'thread_ts': thread_ts,
                'reply_broadcast': True,
            }

        logger.info(f'thread_options = {thread_options}')
        api_response = slack_client.chat_postMessage(
            text=rinna_message,
            channel='C7AAX50QY',
            icon_url=character_config['slack_user_icon'],
            username=character_config['slack_user_name'],
            **thread_options,
        )

        response_id = ''.join(random.choice(
            string.ascii_letters + string.digits) for _ in range(20))

        responses_ref.document(response_id).set({
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
            'thread_ts': thread_ts,
        })

    return '。'.join(speech_chunks)


def rinna_meaning(word, ts=None, character='うな', dry_run=False):
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
            logger.info(f'Output: {rinna_message}')
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

        response_id = ''.join(random.choice(
            string.ascii_letters + string.digits) for _ in range(20))

        responses_ref.document(response_id).set({
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
    logger.info(rinna_response([
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
processed_submission_ids = set()


def pubsub_callback(message) -> None:
    data_buf = message.data
    data = json.loads(data_buf.decode())
    logger.info(
        f'received rinna-signal: {data.get("type")} (lastSignal = {data.get("lastSignal")})')

    if 'humanMessages' in data and data['type'] == 'rinna-signal' and isinstance(data['humanMessages'], list):
        mutex.acquire()

        trigger_text = data['humanMessages'][-1]['text']
        trigger_ts_str = data['humanMessages'][-1]['ts']
        trigger_ts = float(trigger_ts_str)
        now_ts = time()
        rinna_triggered = False
        logger.info(f'now_ts = {now_ts}, trigger_ts = {trigger_ts}')
        if now_ts - trigger_ts > 15 * 60:
            thread_ts = trigger_ts_str
        else:
            thread_ts = None

        try:
            if '@うな先生' in trigger_text:
                word = re.sub(r'^@うな先生', '', trigger_text)
                word = word.strip()
                response = rinna_meaning(word, None, 'うな')

            else:
                if 'りんな' in trigger_text:
                    response = rinna_response(
                        data['humanMessages'], 'りんな', thread_ts=thread_ts)
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': 'りんな',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'うな' in trigger_text:
                    response = rinna_response(
                        data['humanMessages'], 'うな', thread_ts=thread_ts)
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '今言うな',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'うか' in trigger_text:
                    response = rinna_response(
                        data['humanMessages'], 'うか', thread_ts=thread_ts)
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '皿洗うか',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'うの' in trigger_text:
                    response = rinna_response(
                        data['humanMessages'], 'うの', thread_ts=thread_ts)
                    data['humanMessages'].append({
                        'bot_id': 'BEHP604TV',
                        'username': '皿洗うの',
                        'text': response,
                    })
                    rinna_triggered = True

                if 'たたも' in trigger_text:
                    response = rinna_response(
                        data['humanMessages'], 'たたも', thread_ts=thread_ts)
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
                        logger.info('random.choice')
                        character = random.choice(
                            ['りんな', 'うな', 'うか', 'うの', 'たたも'])
                        logger.info(f'character = {character}')
                    rinna_response(data['humanMessages'],
                                   character, thread_ts=thread_ts)

            message.ack()

        except Exception as e:
            traceback.logger.info_exc()
            logger.info(e)

        finally:
            mutex.release()

    if data['type'] == 'rinna-meaning':
        mutex.acquire()

        try:
            rinna_meaning(data.get('word'), data.get('ts'), 'うな')
            message.ack()

        except Exception as e:
            traceback.logger.info_exc()
            logger.info(e)

        finally:
            mutex.release()

    if data['type'] == 'rinna-ping':
        topic_id = data['topicId']
        ts = int(topic_id.split('-')[-1])
        current_time = time() * 1000
        if current_time - ts > 1000 * 20:
            logger.info(f'Ignoring old ping: {topic_id}')
        else:
            topic_path = publisher.topic_path(project_id, topic_id)
            publish_future = publisher.publish(topic_path, json.dumps({
                'type': 'rinna-pong',
                'mode': sys.argv[1],
            }).encode())

            logger.info(publish_future.result())

        message.ack()

    if data['type'] == 'llm-benchmark-submission':
        mutex.acquire()

        try:
            logger.info('Processing llm-benchmark-submission...')
            submission_data = data['data']

            '''
            if 'id' in submission_data and submission_data['id'] not in processed_submission_ids:
                submission_id = submission_data['id']
                logger.info(f'Processing submission {submission_id}')

                scores = score_response(submission_data)
                logger.info(f'Scores: {scores}')

                result = update_form_scores(submission_id, scores)
                print(result)

                processed_submission_ids.add(submission_id)
            '''

            message.ack()

        except Exception as e:
            traceback.logger.info_exc()
            logger.info(e)

        finally:
            mutex.release()


streaming_pull_future = subscriber.subscribe(
    subscription_path, callback=pubsub_callback)


def cancel(signum, frame):
    logger.info('Received signal', signum)
    streaming_pull_future.cancel()


signal.signal(signal.SIGINT, cancel)
signal.signal(signal.SIGTERM, cancel)

logger.info(f"Listening for messages on {subscription_path}..\n")

with subscriber:
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()
