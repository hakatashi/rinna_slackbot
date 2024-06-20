from rinna.utils import get_weekday_str, get_hour_str, normalize_text, has_offensive_term, split_speech_to_chunks
import pytest


def test_get_weekday_str():
    assert get_weekday_str(0) == '月'
    assert get_weekday_str(6) == '日'
    with pytest.raises(IndexError):
        get_weekday_str(7)


def test_get_hour_str():
    assert get_hour_str(0) == '午前0'
    assert get_hour_str(12) == '午前12'
    assert get_hour_str(13) == '午後1'
    assert get_hour_str(23) == '午後11'
    with pytest.raises(TypeError):
        get_hour_str('noon')


def test_normalize_text():
    assert normalize_text('@りんな hello') == 'hello'
    assert normalize_text('ワシ') == '儂'
    assert normalize_text('今言うな') == 'ウナ'
    assert normalize_text('皿洗うか') == 'ウカ'
    assert normalize_text('皿洗うの') == 'ウノ'
    assert normalize_text('三脚たたも') == 'タタモ'
    assert normalize_text('うな') == 'ウナ'
    assert normalize_text('うなは') == 'ウナは'
    assert normalize_text('うなが') == 'ウナが'
    assert normalize_text('うなの') == 'ウナの'
    assert normalize_text('うなを') == 'ウナを'
    assert normalize_text('hello うな') == 'hello ウナ'
    assert normalize_text('hello うな hello') == 'hello うな hello'
    assert normalize_text('hello うなは') == 'hello ウナは'
    assert normalize_text('hello うなが') == 'hello ウナが'
    assert normalize_text('hello うなの') == 'hello ウナの'
    assert normalize_text('hello うなを') == 'hello ウナを'
    assert normalize_text('こうないえん') == 'こうないえん'


def test_has_offensive_term():
    class Term:
        def __init__(self, term):
            self.term = term

    assert has_offensive_term([Term('えた')]) == False
    assert has_offensive_term([Term('クリ')]) == False
    assert has_offensive_term([Term('offensive')]) == True
    assert has_offensive_term(None) == False


def test_split_speech_to_chunks_simple_sentence():
    assert split_speech_to_chunks("これはテストです。いいですね") == ["これはテストです", "いいですね"]


def test_split_speech_to_chunks_ends_with_period():
    assert split_speech_to_chunks("これはテストです。") == ["これはテストです"]


def test_split_speech_to_chunks_ends_with_period():
    assert split_speech_to_chunks("これはテストです。。。。") == ["これはテストです。。。。"]


def test_split_speech_to_chunks_multiple_sentences():
    assert split_speech_to_chunks("これはテストです。これもテストです。") == ["これはテストです", "これもテストです"]


def test_split_speech_to_chunks_with_exclamations_and_questions():
    assert split_speech_to_chunks("これはテストです！これは？") == ["これはテストです！", "これは？"]


def test_split_speech_to_chunks_with_parentheses():
    assert split_speech_to_chunks("これは（テスト！です）ね？") == ["これは（テスト！です）ね？"]


def test_split_speech_to_chunks_with_branckets():
    assert split_speech_to_chunks("私は「こんにちは。おはようございます。」です。よろしくね") == ["私は「こんにちは。おはようございます。」です", "よろしくね"]


def test_split_speech_to_chunks_with_unmatched_brackets():
    assert split_speech_to_chunks("これは「テストです。これは？") == ["これは「テストです。これは？"]


def test_split_speech_to_chunks_with_double_unmatched_brackets():
    assert split_speech_to_chunks("これは「テスト「です。これは？」。これも") == ["これは「テスト「です。これは？」", "これも"]


def test_split_speech_to_chunks_mixed_punctuation():
    assert split_speech_to_chunks("これは（テスト！です）。これも？") == ["これは（テスト！です）", "これも？"]


def test_split_speech_to_chunks_consecutive_punctuation():
    assert split_speech_to_chunks("これはテストです！！これは？？") == ["これはテストです！！", "これは？？"]


def test_split_speech_to_chunks_japanese_punctuation():
    assert split_speech_to_chunks("これはテストです｡これもテストです｡") == ["これはテストです", "これもテストです"]


def test_split_speech_to_chunks_empty_string():
    assert split_speech_to_chunks("") == []
