# FILEPATH: /c:/Users/hakatashi/Documents/GitHub/rinna_slackbot/tests/rinna/test_generation.py

from rinna.generation import generate_rinna_response, generate_rinna_meaning
from rinna.transformer_models import tokenizer, model

class FakeTokens:
    def __init__(self, ids):
        self.ids = ids
    
    def __getitem__(self, index):
        return self.ids[index]

    def to(self, device):
        return self

    def tolist(self):
        return self.ids

def test_generate_rinna_response(mocker):
    mock_tokens = [
        'りんなです', '博多市', '「', 'Hello', '」', 'リンナ', '「',
    ]
    mock_result = [
        'おはよう', '博多市', '」', '博多市', '「', 'Hello', '」', 'リンナ', '「',
    ]

    mocker.patch('rinna.generation.tokenizer.encode', return_value=FakeTokens([mock_tokens]))
    mocker.patch('rinna.generation.tokenizer.decode', side_effect=lambda x: ''.join(map(str, x)))
    mocker.patch('rinna.generation.model.generate', return_value=FakeTokens([mock_tokens + mock_result]))
    mocker.patch('rinna.generation.character_configs', {
        'りんな': {
            'intro': 'りんなです',
            'inquiry_intro': 'りんなです',
            'name_in_text': 'リンナ',
        }
    })
    mocker.patch('rinna.generation.username_mapping', {
        'U01234567': '博多市',
    })

    messages = [{'text': 'Hello', 'bot_id': 'BEHP604TV', 'user': 'U01234567'}]
    character = 'りんな'

    result = generate_rinna_response(messages, character)

    expected_input = 'りんなです\n\n博多市「Hello」\nリンナ「'

    tokenizer.encode.assert_called_with(expected_input, add_special_tokens=False, return_tensors="pt")
    model.generate.assert_called()
    tokenizer.decode.assert_called_with(mock_result)

    assert isinstance(result, tuple)
    assert len(result) == 2

    speech_chunks, info = result

    assert isinstance(speech_chunks, list)
    assert len(speech_chunks) == 1
    assert speech_chunks[0] == 'おはよう博多市'

    assert isinstance(info, dict)
    assert info['text_input'] == expected_input
    assert info['formatted_dialog'] == '博多市「Hello」'
    assert info['output'] == 'おはよう博多市」博多市「Hello」リンナ「'
    assert info['rinna_speech'] == 'おはよう博多市'
    assert info['speech_chunks'] == speech_chunks
    assert info['input_len'] == 7

def test_generate_rinna_meaning(mocker):
    mock_tokens = [
        'ひでお「リンナ、『Hello』ってわかる？」',
        'リンナ「『Hello』っていうのは、こんにちはだよ」',
        'ひでお「リンナ、『World』ってわかる？」',
        'リンナ「『World』っていうのは、',
    ]
    mock_result = [
        '世界', 'の', 'ことだよ', '」',
        'ひでお「リンナ、『Python』ってわかる？」',
        'リンナ「『Python』っていうのは、プログラミング言語だよ」',
    ]

    mocker.patch('rinna.generation.tokenizer.encode', return_value=FakeTokens([mock_tokens]))
    mocker.patch('rinna.generation.tokenizer.decode', side_effect=lambda x: ''.join(map(str, x)))
    mocker.patch('rinna.generation.model.generate', return_value=FakeTokens([mock_tokens + mock_result]))
    mocker.patch('rinna.generation.character_configs', {
        'りんな': {
            'meaning_intro': '\n'.join([
                'ひでお「リンナ、『Hello』ってわかる？」',
                'リンナ「『Hello』っていうのは、こんにちはだよ」',
            ]),
            'name_in_text': 'リンナ',
        }
    })

    character = 'りんな'
    word = 'World'

    result = generate_rinna_meaning(character, word)

    expected_input = 'ひでお「リンナ、『Hello』ってわかる？」\nリンナ「『Hello』っていうのは、こんにちはだよ」\nひでお「リンナ、『World』ってわかる？」\nリンナ「『World』っていうのは、'

    tokenizer.encode.assert_called_with(expected_input, add_special_tokens=False, return_tensors="pt")
    model.generate.assert_called()
    tokenizer.decode.assert_called_with(mock_result)

    assert isinstance(result, tuple)
    assert len(result) == 2

    speech_chunks, info = result

    assert isinstance(speech_chunks, list)
    assert len(speech_chunks) == 1
    assert speech_chunks[0] == '世界のことだよ'

    assert isinstance(info, dict)
    assert info['text_input'] == expected_input
    assert info['output'] == '世界のことだよ」ひでお「リンナ、『Python』ってわかる？」リンナ「『Python』っていうのは、プログラミング言語だよ」'
    assert info['rinna_speech'] == '世界のことだよ'
    assert info['speech_chunks'] == speech_chunks
    assert info['input_len'] == 4