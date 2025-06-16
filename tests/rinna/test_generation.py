import os

os.environ["LLAMA_USE_GPU"] = "0"

from rinna.generation import generate_rinna_response, generate_rinna_meaning

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

    # Mock the functions from transformer_models module
    mock_get_token_ids = mocker.patch('rinna.generation.get_token_ids')
    mock_generate_text = mocker.patch('rinna.generation.generate_text')
    
    # Setup return values for the mocked functions
    mock_get_token_ids.return_value = FakeTokens([mock_tokens])
    mock_generate_text.return_value = ('おはよう博多市', {})
    
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

    mock_get_token_ids.assert_called_with(expected_input)
    mock_generate_text.assert_called_once()

    assert isinstance(result, tuple)
    assert len(result) == 2

    speech_chunks, info = result

    assert isinstance(speech_chunks, list)
    assert len(speech_chunks) == 1
    assert speech_chunks[0] == 'おはよう博多市'

    assert isinstance(info, dict)
    assert info['text_input'] == expected_input
    assert info['formatted_dialog'] == '博多市「Hello」'
    assert info['output'] == 'おはよう博多市'
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

    # Mock the functions from transformer_models module
    mock_get_token_ids = mocker.patch('rinna.generation.get_token_ids')
    mock_generate_text = mocker.patch('rinna.generation.generate_text')
    
    # Setup return values for the mocked functions
    mock_get_token_ids.return_value = FakeTokens([mock_tokens])
    mock_generate_text.return_value = ('世界のことだよ', {})
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

    mock_get_token_ids.assert_called_with(expected_input)
    mock_generate_text.assert_called_once()

    assert isinstance(result, tuple)
    assert len(result) == 2

    speech_chunks, info = result

    assert isinstance(speech_chunks, list)
    assert len(speech_chunks) == 1
    assert speech_chunks[0] == '世界のことだよ'

    assert isinstance(info, dict)
    assert info['text_input'] == expected_input
    assert info['output'] == '世界のことだよ'
    assert info['rinna_speech'] == '世界のことだよ'
    assert info['speech_chunks'] == speech_chunks
    assert info['input_len'] == 4