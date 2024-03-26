from transformers import T5Tokenizer, AutoModelForCausalLM
import torch
import sys
from vllm import LLM, SamplingParams
from time import time
from random import randint

is_gpu_mode = torch.cuda.is_available() and len(sys.argv) >= 2 and sys.argv[1] == 'GPU'

tokenizer = T5Tokenizer.from_pretrained("rinna/japanese-gpt-1b")

if is_gpu_mode:
    model = LLM(
        model="rinna/japanese-gpt-1b",
        gpu_memory_utilization=0.5,
    )
else:
    model = AutoModelForCausalLM.from_pretrained("rinna/japanese-gpt-1b")
    print(f'Using {model.device} for processing rinna-signal', flush=True)

def generate_text(token_ids):
    print('Generating text...', flush=True)

    input_len = len(token_ids[0])
    print(f'{input_len = }', flush=True)
    print(f'{is_gpu_mode = }', flush=True)

    if is_gpu_mode:
        config = {
            'top_k': 500,
            'top_p': 1.0,
            'temperature': 0.8,
            'repetition_penalty': 1.05,
            'max_tokens': input_len + 100,
            'seed': randint(0, 100000),
        }
        
        sampling_params = SamplingParams(**config)

        start_time = time()
        response = model.generate(
            prompt_token_ids=token_ids.tolist(),
            sampling_params=sampling_params,
        )
        output = response[0].outputs[0].text
        end_time = time()

        print(f"Finished. Time taken: {end_time - start_time} seconds", flush=True)

        return output, config
    else:
        config = {
            'do_sample': True,
            'top_k': 500,
            'top_p': 1.0,
            'temperature': 0.8,
            'repetition_penalty': 1.05,
            'pad_token_id': tokenizer.pad_token_id,
            'bos_token_id': tokenizer.bos_token_id,
            'eos_token_id': tokenizer.eos_token_id,
            # bad_word_ids=[[tokenizer.unk_token_id]]
        }

        if input_len > 920:
            return None, config

        start_time = time()
        with torch.no_grad():
            output_ids = model.generate(
                token_ids.to(model.device),
                max_length=input_len + 100,
                min_length=input_len + 100,
                **config,
            )

        output = tokenizer.decode(output_ids.tolist()[0][input_len:])
        end_time = time()

        print(f"Finished. Time taken: {end_time - start_time} seconds", flush=True)

        return output, config
