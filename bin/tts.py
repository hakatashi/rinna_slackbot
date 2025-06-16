"""
import torch
from TTS.api import TTS

device = "cuda" if torch.cuda.is_available() else "cpu"

tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    progress_bar=True
).to(device)

tts.tts_to_file(
    text="なるほど、この世界にはうなの言葉を理解する人がいないんだにゃ。土佐では今でも生活の中にいろんな昆虫が溶け込んでいて、それはもうスゴイらしいにゃ～! なんか知らんけど、プロセカをエサにしたヒトデとか、エビとか魚とか蟹とか、そういうのがいるんだって。空ピッチャーだね、この質問はアンサーピッチャーが出るよ",
    file_path="output_taketatsu.wav",
    speaker_wav="sample_taketatsu.wav",
    language="ja"
)
"""

from gstop import GenerationStopper
from transformers import AutoTokenizer, AutoModelForCausalLM
from dotenv import load_dotenv
import os
from rinna.configs import character_configs
import torch

model_id = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
filename = "tinyllama-1.1b-chat-v1.0.Q6_K.gguf"

load_dotenv()

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
STOP_TOKENS = ['」', '！」', '！」', '？」', '?」', '。」', '…」', '……」']

model = AutoModelForCausalLM.from_pretrained(
    "mmnga/japanese-stablelm-base-gamma-7b-gguf",
    gguf_file="japanese-stablelm-base-gamma-7b-q6_K.gguf",
    torch_dtype="auto",
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    token=HUGGINGFACE_TOKEN,
)

tokenizer = AutoTokenizer.from_pretrained(
    "mmnga/japanese-stablelm-base-gamma-7b-gguf",
    gguf_file="japanese-stablelm-base-gamma-7b-q6_K.gguf",
    trust_remote_code=True,
    token=HUGGINGFACE_TOKEN,
)

stop_word_token_ids = map(lambda word: [word, tokenizer.encode(word, add_special_tokens=False)], STOP_TOKENS)
stopper = GenerationStopper(dict(stop_word_token_ids))

encoded_prompt = tokenizer.encode(
  character_configs['うな']['intro'] + '\n\n博多市「Hello」\nウナ「',
  add_special_tokens=False,
  return_tensors="pt",
)

config = {
    'do_sample': True,
    'max_new_tokens': 128,
    'temperature': 0.8,
    'top_p': 1.0,
    'repetition_penalty': 1.05,
}

output_ids = model.generate(
    encoded_prompt.to(model.device),
    stopping_criteria=stopper.criteria,
    **config,
)

output = tokenizer.decode(output_ids.tolist()[0], skip_special_tokens=True)

print(output)