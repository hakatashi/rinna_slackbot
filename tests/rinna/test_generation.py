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
    # Mock the tokenizer and model from rinna.transformer_models
    mocker.patch('rinna.generation.tokenizer.encode', return_value=FakeTokens([['博多市', '「', 'Hello', '」', 'りんな']]))
    mocker.patch('rinna.generation.tokenizer.decode', side_effect=lambda x: ''.join(map(str, x)))
    mocker.patch('rinna.generation.model.generate', return_value=FakeTokens([[1, 2, 3, 4, 5, 6]]))
    mocker.patch('nonexistent.hoge', 100)

    messages = [{'text': 'Hello', 'bot_id': 'BEHP604TV', 'username': '博多市'}]
    character = 'りんな'

    result = generate_rinna_response(messages, character)

    tokenizer.encode.assert_called_with('Hello', add_special_tokens=False, return_tensors="pt")
    tokenizer.decode.assert_called()
    model.generate.assert_called()

    assert isinstance(result, tuple)
    assert len(result) == 2

    speech_chunks, token_ids_output = result

    assert isinstance(speech_chunks, list)
    assert len(speech_chunks) == 1
    assert speech_chunks[0] == '456'

def test_generate_rinna_meaning(mocker):
    # Mock the tokenizer and model from rinna.transformer_models
    mocker.patch('rinna.generation.tokenizer', autospec=True)
    mocker.patch('rinna.generation.model', autospec=True)

    # Define a sample input
    character = 'りんな'
    word = 'Hello'

    # Call the function with the sample input
    result = generate_rinna_meaning(character, word)

    # Assert that the function calls are as expected
    tokenizer.encode.assert_called()
    model.generate.assert_called()

    # Assert that the result is as expected
    # This will depend on your specific requirements
    assert isinstance(result, tuple)
    assert len(result) == 2