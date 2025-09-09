from multiprocessing import context
import re
from datetime import datetime
from typing import Any, List, Dict, Tuple
from rinna.utils import get_weekday_str, get_hour_str, normalize_text, split_speech_to_chunks
from rinna.configs import character_configs, username_mapping, BOT_ID
from rinna.transformer_models import generate_text, get_token_ids
from logging import getLogger, INFO

logger = getLogger(__name__)
logger.setLevel(INFO)

# --- Constants ---
MAX_INPUT_TOKENS = 2900
BOT_USERNAME_MAPPING = {
    '今言うな': 'ウナ',
    'りんな': 'りんな',
    '皿洗うか': 'ウカ',
    '皿洗うの': 'ウノ',
    '三脚たたも': 'タタモ',
}

def _post_process_speech(text: str, character: str) -> str:
    """Cleans and formats the raw output from the language model."""
    processed_text = text.split('」')[0]
    processed_text = processed_text.replace('[UNK]', '')
    processed_text = processed_text.replace('『', '「')
    processed_text = processed_text.replace('』', '」')
    processed_text = processed_text.replace('ウナ', 'うな')
    processed_text = processed_text.replace('ウカ', 'うか')
    processed_text = processed_text.replace('ウノ', 'うの')
    processed_text = processed_text.replace('タタモ', 'たたも')
    if character == 'たたも':
        processed_text = processed_text.replace('ワシ', '儂')
    return processed_text


def format_message(message: Dict[str, Any]) -> str:
    """Formats a single message for inclusion in the prompt."""
    if message['user'] == 'context':
        return f"({message['text']})"
    return f"{message['user']}「{message['text']}」"


def _get_user_for_message(message: Dict[str, Any]) -> str:
    """Determines the user name for a given message."""
    bot_id = message.get('bot_id')
    username = message.get('username')
    user_id = message.get('user')

    if bot_id == BOT_ID and username in BOT_USERNAME_MAPPING:
        return BOT_USERNAME_MAPPING[username]
    if user_id in username_mapping:
        return username_mapping[user_id]
    return user_id


def _build_prompt_from_messages(messages: List[Dict[str, Any]], character_config: Dict[str, Any]) -> Tuple[str, str, Any]:
    """Builds the prompt for the language model from a list of messages."""
    formatted_messages = []
    for message in messages:
        if message['text'] is None:
            continue

        message_text = message['text']
        context_match = re.match(r'^\((.+?)\).+$', message_text)
        if context_match:
            context_text = normalize_text(context_match.group(1))
            logger.info(f'Context found: {context_text}')
            message_text = message_text[message_text.index(')') + 1:].strip()
            formatted_messages.append({'text': context_text, 'user': 'context'})

        text = normalize_text(message_text)
        if not text:
            continue

        user = _get_user_for_message(message)

        if formatted_messages and formatted_messages[-1]['user'] == user:
            last_text = formatted_messages[-1]['text']
            separator = ' ' if re.search(r'[!?！？。｡、､]$', last_text) else '。'
            formatted_messages[-1]['text'] += separator + text
        else:
            formatted_messages.append({'text': text, 'user': user})

    token_ids_output = None
    text_input = ''
    formatted_dialog = ''

    # Build the prompt backwards to ensure the most recent messages are included
    reversed_messages = reversed(formatted_messages)
    messages_for_prompt = []

    for formatted_message in reversed_messages:
        messages_for_prompt.insert(0, formatted_message)

        current_dialog = '\n'.join(map(format_message, messages_for_prompt))
        name_in_text = character_config['name_in_text']

        prompt = f"{character_config['intro']}\n\n{current_dialog}\n{name_in_text}「"

        date = datetime.now()
        prompt = prompt.replace(r'[MONTH]', str(date.month))
        prompt = prompt.replace(r'[DATE]', str(date.day))
        prompt = prompt.replace(r'[WEEKDAY]', get_weekday_str(date.weekday()))
        prompt = prompt.replace(r'[HOUR]', get_hour_str(date.hour))
        prompt = prompt.replace(r'[MINUTE]', str(date.minute))
        prompt = prompt.replace(r'[WEATHER]', 'くもり') # Placeholder

        token_ids = get_token_ids(prompt)
        input_len = len(token_ids[0])
        logger.info(f'{input_len = }')

        if input_len > MAX_INPUT_TOKENS:
            break

        token_ids_output = token_ids
        text_input = prompt
        formatted_dialog = current_dialog

    return text_input, formatted_dialog, token_ids_output


def generate_rinna_response(messages: List[Dict[str, Any]], character: str) -> Tuple[List[str], Dict[str, Any]]:
    character_config = character_configs[character]

    last_message_text = messages[-1].get('text', '')
    is_inquiry = last_message_text.endswith('？') or last_message_text.endswith('?')
    logger.info(f'{is_inquiry = }')

    token_ids_output: Any = None
    text_input = ''
    formatted_dialog = ''

    if is_inquiry and 'inquiry_intro' in character_config:
        formatted_dialog = f'質問「{last_message_text}」'
        text_input = f"{character_config['inquiry_intro']}\n{formatted_dialog}\n回答「"
        token_ids_output = get_token_ids(text_input)
    else:
        text_input, formatted_dialog, token_ids_output = _build_prompt_from_messages(messages, character_config)

    if token_ids_output is None:
        logger.info('token_ids_output is empty. Quitting...')
        return [], {}

    input_len = len(token_ids_output[0])
    output, config = generate_text(token_ids_output)

    if output is None:
        return [], {}

    rinna_speech = _post_process_speech(output, character)
    speech_chunks = split_speech_to_chunks(rinna_speech)

    info = {
        'text_input': text_input,
        'formatted_dialog': formatted_dialog,
        'output': output,
        'rinna_speech': rinna_speech,
        'speech_chunks': speech_chunks,
        'input_len': input_len,
        'config': config,
    }

    return speech_chunks, info


def generate_rinna_meaning(character: str, word: str) -> Tuple[List[str], Dict[str, Any]]:
    character_config = character_configs[character]
    character_name = character_config['name_in_text']

    inquiry_message = f'ひでお「{character_name}、『{word}』ってわかる？」'
    response_message = f'{character_name}「『{word}』っていうのは、'

    text_input = f"{character_config['meaning_intro']}\n{inquiry_message}\n{response_message}"

    token_ids = get_token_ids(text_input)
    input_len = len(token_ids[0])

    output, config = generate_text(token_ids)

    if output is None:
        return None, {}

    rinna_speech = _post_process_speech(output, character)
    speech_chunks = split_speech_to_chunks(rinna_speech)

    info = {
        'text_input': text_input,
        'output': output,
        'rinna_speech': rinna_speech,
        'speech_chunks': speech_chunks,
        'input_len': input_len,
        'config': config,
    }

    return speech_chunks, info
