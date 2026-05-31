from multiprocessing import context
import re
import regex
from datetime import datetime
from typing import Any, List, Dict, Tuple, Generator, Optional
from rinna.utils import get_weekday_str, get_hour_str, normalize_text, split_speech_to_chunks, normalize_speech_chunk, SENTENCE_DELIMITERS
from rinna.configs import character_configs, username_mapping
from rinna.transformer_models import generate_text, get_token_ids
import rinna.transformer_models as _transformer_models
from logging import getLogger, INFO
from time import sleep

logger = getLogger(__name__)
logger.setLevel(INFO)


def format_message(message):
    if message['user'] == 'context':
        return f"({message['text']})"
    return f"{message['user']}「{message['text']}」"


def get_top2_human_usernames(messages: List[Dict]) -> tuple:
    """直近2人の人間ユーザーの表示名を (user1, user2) で返す。1人しかいなければ同じ名前を使う。"""
    seen = []
    for message in reversed(messages):
        if message.get('bot_id') is not None:
            continue
        user_id = message.get('user')
        if user_id and user_id != 'context' and user_id not in seen:
            seen.append(user_id)
        if len(seen) >= 2:
            break
    names = [username_mapping.get(uid, uid) for uid in seen]
    user1 = names[0] if len(names) >= 1 else None
    user2 = names[1] if len(names) >= 2 else user1
    return user1, user2


def _replace_intro_placeholders(intro: str, user1: Optional[str], user2: Optional[str]) -> str:
    intro = intro.replace('{user1}', user1 or '博多市')
    intro = intro.replace('{user2}', user2 or 'ひでお')
    return intro


def _apply_rinna_replacements(text: str, character: str) -> str:
    text = text.replace('[UNK]', '')
    text = text.replace('『', '「')
    text = text.replace('』', '」')
    text = text.replace('ウナ', 'うな')
    text = text.replace('ウカ', 'うか')
    text = text.replace('ウノ', 'うの')
    text = text.replace('タタモ', 'たたも')
    if character == 'たたも':
        text = text.replace('ワシ', '儂')
    return text


def _stream_speech_chunks(text_gen, character: str) -> Generator[str, None, None]:
    """Takes a text-piece generator and yields processed speech chunks.

    Detects sentence boundaries (。！？♪ etc.) the same way split_speech_to_chunks does,
    but operates incrementally on the streaming output so chunks can be posted to Slack
    as each sentence completes.
    """
    current_chunk = ''
    is_inside_parens = False
    pending_sentence_end = False

    for piece in text_gen:
        for char in piece:
            if pending_sentence_end:
                if char in SENTENCE_DELIMITERS:
                    current_chunk += char
                    continue
                else:
                    chunk = _apply_rinna_replacements(normalize_speech_chunk(current_chunk), character)
                    if chunk:
                        yield chunk
                    current_chunk = char
                    pending_sentence_end = False
            else:
                current_chunk += char

            if regex.match(r'\p{Ps}', char):
                is_inside_parens = True
            elif regex.match(r'\p{Pe}', char):
                is_inside_parens = False
            elif char in SENTENCE_DELIMITERS and not is_inside_parens:
                pending_sentence_end = True

    if current_chunk:
        chunk = _apply_rinna_replacements(normalize_speech_chunk(current_chunk), character)
        if chunk:
            yield chunk


def _prepare_generation(messages: List[Dict[str, Any]], character: str):
    """Shared setup: formats messages and tokenizes.

    Returns (token_ids_output, text_input, formatted_dialog) or
    (None, '', '') when the context is empty.
    """
    character_config = character_configs[character]
    name_in_text = character_config['name_in_text']

    last_message_text = messages[-1]['text'] or ''
    is_inquiry = last_message_text.endswith('？') or last_message_text.endswith('?')

    logger.info(f'{is_inquiry = }')

    use_instruction_prompt = False

    user1, user2 = get_top2_human_usernames(messages)

    token_ids_output: Any = None
    formatted_dialog = ''
    text_input = ''

    if is_inquiry and 'inquiry_intro' in character_config and not use_instruction_prompt:
        inquiry_intro = _replace_intro_placeholders(character_config['inquiry_intro'], user1, user2)
        formatted_dialog = f'質問「{last_message_text}」'
        text_input = inquiry_intro + '\n' + formatted_dialog + '\n' + '回答「'
        token_ids_output = get_token_ids(text_input)
    else:
        formatted_messages = []
        for message in messages:
            if message['text'] is None:
                continue

            message_text = message['text']

            context_match = re.match(r'^\((.+?)\).+$', message_text)
            if context_match:
                context = context_match.group(1)
                normalized_context = normalize_text(context)

                logger.info(f'Context found: {normalized_context}')
                message_text = message_text[message_text.index(')') + 1:].strip()

                formatted_messages.append({
                    'text': normalized_context,
                    'user': 'context',
                })

            text = normalize_text(message_text)

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
                if len(last_text) > 0 and last_text[-1] in SENTENCE_DELIMITERS:
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

        base_intro = _replace_intro_placeholders(character_config['intro'], user1, user2)

        for formatted_message in formatted_messages:
            formatted_messages_bin.insert(0, formatted_message)

            formatted_dialog = '\n'.join(map(format_message, formatted_messages_bin))

            intro = character_config['instruction_prompt'] + '\n' if use_instruction_prompt else base_intro + '\n'
            outro = f'\n{name_in_text}「' if not use_instruction_prompt else '\n'

            text_input = intro + '\n' + formatted_dialog + outro

            date = datetime.now()

            text_input = text_input.replace(r'[MONTH]', str(date.month))
            text_input = text_input.replace(r'[DATE]', str(date.day))
            text_input = text_input.replace(
                r'[WEEKDAY]', get_weekday_str(date.weekday()))
            text_input = text_input.replace(r'[HOUR]', get_hour_str(date.hour))
            text_input = text_input.replace(r'[MINUTE]', str(date.minute))
            text_input = text_input.replace(r'[WEATHER]', 'くもり')

            token_ids = get_token_ids(text_input)
            input_len = len(token_ids[0])
            logger.info(f'{input_len = }')

            if input_len > 2900:
                break
            else:
                token_ids_output = token_ids

    if token_ids_output is None:
        logger.info('token_ids_output is empty. Quitting...')

    return token_ids_output, text_input, formatted_dialog


def generate_rinna_response(messages: List[Dict[str, Any]], character: str) -> Tuple[List[str], Dict[str, Any]]:
    token_ids_output, text_input, formatted_dialog = _prepare_generation(messages, character)

    if token_ids_output is None:
        return '', {}

    input_len = len(token_ids_output[0])

    output, config = generate_text(token_ids_output)

    if output is None:
        return '', {}

    rinna_speech = output.split('」')[0]
    rinna_speech = _apply_rinna_replacements(rinna_speech, character)

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


def generate_rinna_response_streaming(messages: List[Dict[str, Any]], character: str) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """Generator that yields (chunk, info) tuples from llama-server streaming.

    Each yielded chunk is a complete sentence ready to post to Slack.
    The info dict is mutable and accumulates the full output across yields.
    """
    token_ids_output, text_input, formatted_dialog = _prepare_generation(messages, character)

    if token_ids_output is None:
        return

    input_len = len(token_ids_output[0])
    config = {
        'model_provider': 'llama-server',
        'model_name': _transformer_models.model_name + '/' + _transformer_models.model_file,
    }

    info: Dict[str, Any] = {
        'text_input': text_input,
        'formatted_dialog': formatted_dialog,
        'input_len': input_len,
        'config': config,
        'output': '',
        'rinna_speech': '',
        'speech_chunks': [],
    }

    for chunk in _stream_speech_chunks(_transformer_models.stream_text(token_ids_output), character):
        if len(info['output']) > 0:
            if info['output'][-1] not in SENTENCE_DELIMITERS:
                info['output'] += '。'
            else:
                info['output'] += ' '
        info['output'] += chunk
        info['rinna_speech'] = info['output']
        info['speech_chunks'].append(chunk)
        yield chunk, info


def generate_rinna_meaning(character: str, word: str, username1: Optional[str] = None, username2: Optional[str] = None) -> Tuple[List[str], Dict[str, Any]]:
    character_config = character_configs[character]
    character_name = character_config['name_in_text']

    meaning_intro = _replace_intro_placeholders(character_config['meaning_intro'], username1, username2)
    inquiry_name = username2 or 'ひでお'
    inquiry_message = f'{inquiry_name}「{character_name}、『{word}』ってわかる？」'
    response_message = f'{character_name}「『{word}』っていうのは、'

    text_input = meaning_intro + '\n' + inquiry_message + '\n' + response_message

    token_ids = get_token_ids(text_input)

    input_len = len(token_ids[0])

    output, config = generate_text(token_ids)

    if output is None:
        return None, None

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
