import re
import regex

MODERATION_ALLOWLIST = ['えた', 'クリ']

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