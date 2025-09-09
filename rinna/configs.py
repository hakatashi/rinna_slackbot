import json
from pathlib import Path

BOT_ID = 'BEHP604TV'

try:
    with open(Path(__file__).parent.parent / 'data' / 'users.json', 'r', encoding='utf-8') as f:
        username_mapping = json.load(f)
except FileNotFoundError:
    username_mapping = {}

try:
    with open(Path(__file__).parent.parent / 'data' / 'intro.json', 'r', encoding='utf-8') as f:
        intro_mapping = json.load(f)
except FileNotFoundError:
    intro_mapping = {
        'rinna_intro': 'りんなです',
        'rinna_inquiry_intro': 'りんなです',
        'una_intro': 'うなです',
        'una_inquiry_intro': 'うなです',
        'una_meaning_intro': 'うなです',
        'uka_intro': 'うかです',
        'uno_intro': 'うのです',
        'tatamo_intro': 'たたもです',
    }

character_configs = {
    'りんな': {
        'intro': intro_mapping['rinna_intro'],
        'inquiry_intro': intro_mapping['rinna_inquiry_intro'],
        'name_in_text': 'りんな',
        'slack_user_name': 'りんな',
        'slack_user_icon': 'https://huggingface.co/rinna/japanese-gpt-1b/resolve/main/rinna.png',
    },
    'うな': {
        'intro': intro_mapping['una_intro'],
        'inquiry_intro': intro_mapping['una_inquiry_intro'],
        'meaning_intro': intro_mapping['una_meaning_intro'],
        'name_in_text': 'ウナ',
        'slack_user_name': '今言うな',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/una_icon.png',
    },
    'うか': {
        'intro': intro_mapping['uka_intro'],
        'name_in_text': 'ウカ',
        'slack_user_name': '皿洗うか',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/uka_icon_edit.png',
    },
    'うの': {
        'intro': intro_mapping['uno_intro'],
        'name_in_text': 'ウノ',
        'slack_user_name': '皿洗うの',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/uno_icon.png',
    },
    'たたも': {
        'intro': intro_mapping['tatamo_intro'],
        'name_in_text': 'タタモ',
        'slack_user_name': '三脚たたも',
        'slack_user_icon': 'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/user03.png',
    },
}
