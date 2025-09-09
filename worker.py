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
from rinna.configs import character_configs, BOT_ID
from concurrent.futures import ThreadPoolExecutor
import uuid
from logging import getLogger

logger = getLogger(__name__)

logger.info('Worker started')

load_dotenv()

# --- Environment Variables ---
SLACK_TOKEN = os.environ['SLACK_TOKEN']
CONTENT_MODERATOR_ENDPOINT = os.environ['CONTENT_MODERATOR_ENDPOINT']
CONTENT_MODERATOR_SUBSCRIPTION_KEY = os.environ['CONTENT_MODERATOR_SUBSCRIPTION_KEY']
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "hakatabot-firebase-functions")
PUBSUB_SUBSCRIPTION_ID = os.environ.get("PUBSUB_SUBSCRIPTION_ID", "rinna-signal")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "C7AAX50QY")

mutex = Lock()

# --- Client Initialization ---
slack_client = WebClient(token=SLACK_TOKEN)
language_client = language_v1.LanguageServiceClient()
content_moderator_client = ContentModeratorClient(
    endpoint=CONTENT_MODERATOR_ENDPOINT,
    credentials=CognitiveServicesCredentials(CONTENT_MODERATOR_SUBSCRIPTION_KEY)
)
app = firebase_admin.initialize_app()
db = firestore.client()
responses_ref = db.collection(u'rinna-responses')

# --- Character Definitions ---
CHARACTER_TRIGGERS = [
    {'name': 'りんな', 'triggers': ['りんな'], 'username': 'りんな'},
    {'name': 'うな', 'triggers': ['うな'], 'username': '今言うな'},
    {'name': 'うか', 'triggers': ['うか'], 'username': '皿洗うか'},
    {'name': 'うの', 'triggers': ['うの'], 'username': '皿洗うの'},
    {'name': 'たたも', 'triggers': ['たたも'], 'username': '三脚たたも'},
]

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

        thread_options = {'thread_ts': thread_ts, 'reply_broadcast': True} if thread_ts else {}

        logger.info(f'thread_options = {thread_options}')
        api_response = slack_client.chat_postMessage(
            text=rinna_message,
            channel=SLACK_CHANNEL_ID,
            icon_url=character_config['slack_user_icon'],
            username=character_config['slack_user_name'],
            **thread_options,
        )

        response_id = str(uuid.uuid4())

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
            'channel': SLACK_CHANNEL_ID,
            'icon_url': character_config['slack_user_icon'],
            'username': f'おじさんが役に立たないときに助けてくれる{slack_username}',
        }

        if ts is not None:
            post_message_kwargs['thread_ts'] = ts
            post_message_kwargs['reply_broadcast'] = True

        api_response = slack_client.chat_postMessage(**post_message_kwargs)

        response_id = str(uuid.uuid4())

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

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, PUBSUB_SUBSCRIPTION_ID)

publisher = pubsub_v1.PublisherClient()


def pubsub_callback(message) -> None:
    try:
        data = json.loads(message.data.decode())
        logger.info(f'Received pub/sub message of type: {data.get("type")}')

        message_type = data.get("type")

        if message_type == 'rinna-signal':
            handle_rinna_signal(data)
        elif message_type == 'rinna-meaning':
            handle_rinna_meaning(data)
        elif message_type == 'rinna-ping':
            handle_rinna_ping(data)
        elif message_type == 'llm-benchmark-submission':
            logger.info("llm-benchmark-submission type is currently not handled.")

        message.ack()

    except Exception:
        logger.exception("An error occurred processing Pub/Sub message:")
        # Deciding not to nack the message to avoid potential infinite retry loops.
        # Depending on the error, a different strategy might be better.
        message.ack()


def handle_rinna_signal(data):
    with mutex:
        try:
            if not ('humanMessages' in data and isinstance(data['humanMessages'], list) and data['humanMessages']):
                return

            last_message = data['humanMessages'][-1]
            trigger_text = last_message['text']
            trigger_ts_str = last_message['ts']

            now_ts = time()
            trigger_ts = float(trigger_ts_str)
            thread_ts = trigger_ts_str if (now_ts - trigger_ts > 15 * 60) else None

            if '@うな先生' in trigger_text:
                word = re.sub(r'^@うな先生', '', trigger_text).strip()
                rinna_meaning(word, None, 'うな')
                return

            triggered_character = None
            for char_info in CHARACTER_TRIGGERS:
                for trigger in char_info['triggers']:
                    if trigger in trigger_text:
                        response = rinna_response(data['humanMessages'], char_info['name'], thread_ts=thread_ts)
                        data['humanMessages'].append({
                            'bot_id': BOT_ID,
                            'username': char_info['username'],
                            'text': response,
                        })
                        triggered_character = char_info['name']
                        break
                if triggered_character:
                    break

            if not triggered_character:
                if '皿洗' in trigger_text:
                    character = random.choice(['うか', 'うの'])
                else:
                    character = random.choice(['りんな', 'うな', 'うか', 'うの'])
                rinna_response(data['humanMessages'], character, thread_ts=thread_ts)

        except Exception:
            logger.exception("Error in handle_rinna_signal:")


def handle_rinna_meaning(data):
    with mutex:
        try:
            rinna_meaning(data.get('word'), data.get('ts'), 'うな')
        except Exception:
            logger.exception("Error in handle_rinna_meaning:")


def handle_rinna_ping(data):
    topic_id = data['topicId']
    ts = int(topic_id.split('-')[-1])
    current_time = time() * 1000
    if current_time - ts > 1000 * 20:
        logger.info(f'Ignoring old ping: {topic_id}')
    else:
        topic_path = publisher.topic_path(GCP_PROJECT_ID, topic_id)
        publish_future = publisher.publish(topic_path, json.dumps({
            'type': 'rinna-pong',
            'mode': sys.argv[1],
        }).encode())
        logger.info(publish_future.result())


streaming_pull_future = subscriber.subscribe(
    subscription_path, callback=pubsub_callback)


def cancel(signum, frame):
    logger.info(f'Received signal {signum}')
    streaming_pull_future.cancel()


signal.signal(signal.SIGINT, cancel)
signal.signal(signal.SIGTERM, cancel)

logger.info(f"Listening for messages on {subscription_path}..\n")

with subscriber:
    try:
        streaming_pull_future.result()
    except (TimeoutError, KeyboardInterrupt):
        streaming_pull_future.cancel()
        streaming_pull_future.result()
