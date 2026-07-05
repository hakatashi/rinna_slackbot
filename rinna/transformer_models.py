from dotenv import load_dotenv
load_dotenv()

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import sys
from time import time
import os
from gstop import GenerationStopper
from huggingface_hub import hf_hub_download
from logging import getLogger, INFO

"""
from ollama import chat, web_fetch, web_search
from ollama import ChatResponse
"""

# https://qiita.com/koyayashi/items/2bb1bafc33249aa4d7f3
if os.name == 'nt':
    for p in os.environ['PATH'].split(os.pathsep):
        if os.path.isdir(p):
            os.add_dll_directory(p)

from llama_cpp import Llama

logger = getLogger(__name__)
logger.setLevel(INFO)

logger.info('Loading models from huggingface...')

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
STOP_TOKENS = ['」', '！」', '！」', '？」', '?」', '。」', '…」', '……」']

is_llama_server_mode = '--llama-server' in sys.argv
is_llama_mode = '--llama' in sys.argv
is_gpu_mode = '--gpu' in sys.argv
print(f'{is_llama_server_mode = }')
print(f'{is_llama_mode = }')
print(f'{is_gpu_mode = }')

if is_llama_server_mode:
    import subprocess
    import requests as _requests
    import atexit
    import json as _json
    from pathlib import Path

    logger.info('Using llama-server mode')

    LLAMA_SERVER_BINARY = Path.home() / "Documents/GitHub/llama.cpp/build/bin/llama-server"
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 8080
    SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

    model_name = "mradermacher/Qwen3.5-35B-A3B-Base-GGUF"
    model_file = "Qwen3.5-35B-A3B-Base.Q6_K.gguf"
    model_path = hf_hub_download(
        model_name,
        filename=model_file,
        resume_download=True,
    )

    if not LLAMA_SERVER_BINARY.exists():
        raise FileNotFoundError(f"llama-server not found: {LLAMA_SERVER_BINARY}")

    cmd = [
        str(LLAMA_SERVER_BINARY),
        "-m", model_path,
        "--host", SERVER_HOST,
        "--port", str(SERVER_PORT),
        "-c", "8192",
        "-ngl", "-1" if is_gpu_mode else "0",
    ]

    logger.info(f'Starting llama-server: {" ".join(cmd)}')
    _server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    def _wait_for_server(url, timeout=360):
        logger.info('Waiting for llama-server to start...')
        from time import sleep as _sleep
        _sleep(3)
        start = time()
        while time() - start < timeout:
            try:
                resp = _requests.get(f"{url}/health", timeout=5)
                if resp.status_code == 200:
                    logger.info('llama-server is ready')
                    return True
            except Exception:
                pass
            _sleep(2)
        raise RuntimeError('llama-server failed to start within timeout')

    _wait_for_server(SERVER_URL)

    def _stop_server():
        import os as _os
        import signal as _signal
        try:
            _os.killpg(_os.getpgid(_server_process.pid), _signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        try:
            _server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _server_process.kill()
            _server_process.wait()
        logger.info('llama-server stopped')

    atexit.register(_stop_server)

    def stream_text(token_ids):
        """Generator that yields text pieces from llama-server streaming API.

        Tracks '「」' nesting depth and stops only when '」' appears at depth 0
        (the closing bracket of the outermost speech), so nested quotes like
        '「word」' inside the speech do not prematurely end generation.
        """
        logger.info('Streaming text via llama-server...')
        start_time = time()

        response = _requests.post(
            f"{SERVER_URL}/completion",
            json={
                "prompt": token_ids[0],
                "n_predict": 200,
                "stream": True,
                "seed": -1,
                "temperature": 0.6,
                "top_p": 0.85,
                "top_k": 30,
                "repeat_penalty": 1.2,
            },
            stream=True,
            timeout=300,
        )

        if response.status_code != 200:
            raise RuntimeError(f'llama-server /completion returned {response.status_code}: {response.text}')

        bracket_depth = 0

        for line in response.iter_lines():
            if not line:
                continue
            if not line.startswith(b'data: '):
                continue
            data = _json.loads(line[6:])
            piece = data.get('content', '')

            stop_idx = None
            for i, char in enumerate(piece):
                if char == '「':
                    bracket_depth += 1
                elif char == '」':
                    if bracket_depth == 0:
                        stop_idx = i
                        break
                    bracket_depth -= 1

            logger.info(f"stream_text: piece={piece!r} bracket_depth={bracket_depth} stop_idx={stop_idx} stop={data.get('stop', False)}")

            if stop_idx is not None:
                if stop_idx > 0:
                    yield piece[:stop_idx]
                end_time = time()
                logger.info(f"Finished (end of speech). Time taken: {end_time - start_time:.1f}s")
                return

            if piece:
                yield piece

            if data.get('stop', False):
                break

        end_time = time()
        logger.info(f"Finished. Time taken: {end_time - start_time:.1f}s")

    def generate_text(token_ids):
        logger.info('Generating text via llama-server...')
        start_time = time()

        response = _requests.post(
            f"{SERVER_URL}/completion",
            json={
                "prompt": token_ids[0],
                "n_predict": 200,
                "stop": ["」"],
                "seed": -1,
                "temperature": 0.6,
                "top_p": 0.85,
                "top_k": 30,
                "repeat_penalty": 1.2,
            },
            timeout=300,
        )

        if response.status_code != 200:
            raise RuntimeError(f'llama-server /completion returned {response.status_code}: {response.text}')

        output_text = response.json()["content"]
        end_time = time()
        logger.info(f"Finished. Time taken: {end_time - start_time} seconds")

        if len(output_text) == 0:
            raise ValueError('output_text is empty')

        return output_text, {'model_provider': 'llama-server', 'model_name': model_name + '/' + model_file}

    def get_token_ids(text_input):
        response = _requests.post(
            f"{SERVER_URL}/tokenize",
            json={"content": text_input, "add_special": False},
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f'llama-server /tokenize returned {response.status_code}: {response.text}')
        tokens = response.json()["tokens"]
        return [tokens]

elif is_llama_mode:
    logger.info('Using Llama model')

    # model_name = "mmnga/japanese-stablelm-base-gamma-7b-gguf"
    # model_file = "japanese-stablelm-base-gamma-7b-q6_K.gguf"
    # model_name = "mradermacher/Qwen2.5-14B-GGUF"
    # model_name = "mradermacher/Qwen3-14B-Base-GGUF"
    model_name = "mradermacher/Qwen3.5-35B-A3B-Base-GGUF"
    # model_file = "Qwen2.5-14B.Q4_K_S.gguf"
    # model_file = "Qwen3-14B-Base.Q4_K_S.gguf"
    model_file = "Qwen3.5-35B-A3B-Base.Q6_K.gguf"
    model_path = hf_hub_download(
        model_name,
        filename=model_file,
        resume_download=True,
    )

    model = Llama(
        model_path=model_path,
        n_gpu_layers=-1 if is_gpu_mode else 0,
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

        if len(output_text) == 0:
            raise ValueError('output_text is empty')

        return output_text, {'model_provider': "Llama.cpp", 'model_name': model_name + '/' + model_file}

    def get_token_ids(text_input):
        token_ids = model.tokenize(text_input.encode("utf-8"))
        return [token_ids]

else:
    logger.info('Using transformer model')

    tokenizer = AutoTokenizer.from_pretrained(
        # "stabilityai/japanese-stablelm-2-base-1_6b",
        "Qwen/Qwen3.5-35B-A3B-Base",
        trust_remote_code=True,
        token=HUGGINGFACE_TOKEN,
    )

    if is_gpu_mode:
        model = AutoModelForCausalLM.from_pretrained(
            # "stabilityai/japanese-stablelm-2-base-1_6b",
            "Qwen/Qwen3.5-35B-A3B-Base",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            device_map="cuda",
            trust_remote_code=True,
            token=HUGGINGFACE_TOKEN,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            # "stabilityai/japanese-stablelm-2-base-1_6b",
            "Qwen/Qwen3.5-35B-A3B-Base",
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
            'temperature': 0.7,
            'top_p': 0.9,
            'top_k': 50,
            'repetition_penalty': 1.1,
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

        config['model_provider'] = "Transformers"
        config['model_name'] = "stabilityai/japanese-stablelm-2-base-1_6b"

        return output, config

    def get_token_ids(text_input):
        token_ids = tokenizer.encode(
            text_input, add_special_tokens=False, return_tensors="pt")
        return token_ids
