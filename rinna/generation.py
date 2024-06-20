import re
from datetime import datetime
from typing import Any
from rinna.utils import get_weekday_str, get_hour_str, normalize_text, split_speech_to_chunks
from rinna.configs import character_configs, username_mapping
from rinna.transformer_models import tokenizer, generate_text
from typing import List, Dict, Tuple

def generate_rinna_response(messages: List[Dict[str, Any]], character: str) -> Tuple[List[str], Dict[str, Any]]:
    character_config = character_configs[character]
    name_in_text = character_config['name_in_text']

    last_message_text = messages[-1]['text'] or ''
    is_inquiry = last_message_text.endswith('？') or last_message_text.endswith('?')

    print(f'{is_inquiry = }', flush=True)

    token_ids_output: Any = None
    if is_inquiry and 'inquiry_intro' in character_config:
        formatted_dialog = f'質問「{last_message_text}」'
        text_input = character_config['inquiry_intro'] + '\n' + formatted_dialog + '\n' + '回答「'
        token_ids_output = tokenizer.encode(
            text_input, add_special_tokens=True, return_tensors="pt")
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
        print(formatted_messages)

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
                text_input, add_special_tokens=True, return_tensors="pt")
            print(token_ids)
            input_len = len(token_ids[0])
            print(input_len)

            if input_len > 1900:
                break
            else:
                token_ids_output = token_ids

    if token_ids_output is None:
        print('token_ids_output is empty. Quitting...', flush=True)
        return '', {}

    input_len = len(token_ids_output[0])
    
    output, config = generate_text(token_ids_output)

    if output is None:
        return '', {}

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

    text_input = character_config['meaning_intro'] + '\n' + inquiry_message + '\n' + response_message

    token_ids = tokenizer.encode(
        text_input, add_special_tokens=False, return_tensors="pt")

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