from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import sys
from dotenv import load_dotenv
from time import time
import os
from gstop import GenerationStopper

load_dotenv()

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
STOP_TOKENS = ['」', '！」', '！」', '？」', '?」', '。」', '…」', '……」']

is_gpu_mode = torch.cuda.is_available() and len(sys.argv) >= 2 and sys.argv[1] == 'GPU'

tokenizer = AutoTokenizer.from_pretrained(
    "stabilityai/japanese-stablelm-2-base-1_6b",
    trust_remote_code=True,
    token=HUGGINGFACE_TOKEN,
)

if is_gpu_mode:
    model = AutoModelForCausalLM.from_pretrained(
        "stabilityai/japanese-stablelm-2-base-1_6b",
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        device_map="auto",
        trust_remote_code=True,
        token=HUGGINGFACE_TOKEN,
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        "stabilityai/japanese-stablelm-2-base-1_6b",
        low_cpu_mem_usage=True,
        trust_remote_code=True,
        token=HUGGINGFACE_TOKEN,
    )

# model = AutoModelForCausalLM.from_pretrained("rinna/japanese-gpt-1b")
print(f'Using {model.device} for processing rinna-signal', flush=True)

stop_word_token_ids = map(lambda word: [word, tokenizer.encode(word, add_special_tokens=False)], STOP_TOKENS)
stopper = GenerationStopper(dict(stop_word_token_ids))

def generate_text(token_ids):
    print('Generating text...', flush=True)

    input_len = len(token_ids[0])
    print(f'{input_len = }', flush=True)
    print(f'{is_gpu_mode = }', flush=True)
    print(f'{stop_word_token_ids = }', flush=True)

    config = {
        'do_sample': True,
        'max_new_tokens': 128,
        'temperature': 0.8,
        'top_p': 1.0,
        'repetition_penalty': 1.05,
    }

    start_time = time()

    tokens = model.generate(
        token_ids.to(model.device),
        stopping_criteria=stopper.criteria,
        **config,
    )
    output = tokenizer.decode(tokens.tolist()[0][input_len:], skip_special_tokens=True)

    end_time = time()

    print(f"Finished. Time taken: {end_time - start_time} seconds", flush=True)

    return output, config