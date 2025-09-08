from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import sys
from dotenv import load_dotenv
from time import time
import os
from gstop import GenerationStopper
from huggingface_hub import hf_hub_download
from logging import getLogger, INFO

# https://qiita.com/koyayashi/items/2bb1bafc33249aa4d7f3
for p in os.environ['PATH'].split(os.pathsep):
    if os.path.isdir(p):
        os.add_dll_directory(p)

from llama_cpp import Llama

logger = getLogger(__name__)
logger.setLevel(INFO)

logger.info('Loading models from huggingface...')

load_dotenv()

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
STOP_TOKENS = ['」', '！」', '！」', '？」', '?」', '。」', '…」', '……」']

is_llama_mode = len(sys.argv) >= 3 and sys.argv[2] == 'Llama'
is_gpu_mode = not is_llama_mode and torch.cuda.is_available() and len(
    sys.argv) >= 2 and sys.argv[1] == 'GPU'

if is_llama_mode:
    logger.info('Using Llama model')

    # model_name = "mmnga/japanese-stablelm-base-gamma-7b-gguf"
    # model_file = "japanese-stablelm-base-gamma-7b-q6_K.gguf"
    # model_name = "mradermacher/Qwen2.5-14B-GGUF"
    model_name = "mradermacher/Qwen3-14B-Base-GGUF"
    # model_file = "Qwen2.5-14B.Q4_K_S.gguf"
    model_file = "Qwen3-14B-Base.Q4_K_S.gguf"
    model_path = hf_hub_download(model_name, filename=model_file)

    model = Llama(
        model_path=model_path,
        n_gpu_layers=48 if is_gpu_mode else 0,
        n_ctx=4096,
    )

    def generate_text(token_ids):
        logger.info('Generating text...')

        start_time = time()

        output = model.create_completion(
            token_ids[0],
            max_tokens=512,
            stop=["」"],
            seed=-1,
            temperature=0.9,
            repeat_penalty=1.6,
        )
        output_text = output["choices"][0]["text"]

        end_time = time()

        logger.info(
            f"Finished. Time taken: {end_time - start_time} seconds")

        return output_text, {}

    def get_token_ids(text_input):
        token_ids = model.tokenize(text_input.encode("utf-8"))
        return [token_ids]

else:
    logger.info('Using transformer model')

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
    logger.info(
        f'Using {model.device} for processing rinna-signal')

    stop_word_token_ids = map(lambda word: [word, tokenizer.encode(
        word, add_special_tokens=False)], STOP_TOKENS)
    stopper = GenerationStopper(dict(stop_word_token_ids))

    def generate_text(token_ids):
        logger.info('Generating text...')

        input_len = len(token_ids[0])
        logger.info(f'{input_len = }')
        logger.info(f'{is_gpu_mode = }')
        logger.info(f'{stop_word_token_ids = }')

        config = {
            'do_sample': True,
            'max_new_tokens': 128,
            'temperature': 1.5,
            'top_p': 1.0,
            'repetition_penalty': 1.4,
        }

        start_time = time()

        tokens = model.generate(
            token_ids.to(model.device),
            stopping_criteria=stopper.criteria,
            **config,
        )
        output = tokenizer.decode(
            tokens.tolist()[0][input_len:], skip_special_tokens=True)

        end_time = time()

        logger.info(
            f"Finished. Time taken: {end_time - start_time} seconds")

        return output, config

    def get_token_ids(text_input):
        token_ids = tokenizer.encode(
            text_input, add_special_tokens=False, return_tensors="pt")
        return token_ids
