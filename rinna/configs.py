from data.intro import rinna_intro, rinna_inquiry_intro, una_intro, uka_intro, uno_intro, una_inquiry_intro, tatamo_intro, una_meaning_intro

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
