from vllm import LLM, SamplingParams
from transformers import AutoTokenizer, AutoModelForCausalLM
from time import time
from rinna.configs import character_configs
from random import randint
import torch

def transformers_rinna():
    tokenizer = AutoTokenizer.from_pretrained("rinna/japanese-gpt-1b")
    model = AutoModelForCausalLM.from_pretrained("rinna/japanese-gpt-1b")

    model = model.to("cuda")

    context = character_configs['うな']['inquiry_intro'] + \
        '\n' + '質問「うなのファンって全国に何人いる？」' + '\n' + '回答「'

    start_time = time()

    token_ids = tokenizer.encode(
        context, add_special_tokens=False, return_tensors="pt")
    input_len = len(token_ids[0])

    print(f'{input_len = }', flush=True)
    if input_len > 920:
        return None

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

    with torch.no_grad():
        output_ids = model.generate(
            token_ids.to(model.device),
            max_length=input_len + 100,
            min_length=input_len + 100,
            **config,
        )

    output = tokenizer.decode(output_ids.tolist()[0][input_len:])

    print(output, flush=True)

    end_time = time()

    print(f"Time taken: {end_time - start_time} seconds", flush=True)

def vllm_rinna():
    tokenizer = AutoTokenizer.from_pretrained("rinna/japanese-gpt-1b", use_fast=False)
    
    context = character_configs['うな']['inquiry_intro'] + \
        '\n' + '質問「うなのファンって全国に何人いる？」' + '\n' + '回答「'

    model = LLM(
        model="rinna/japanese-gpt-1b",
    )

    start_time = time()

    token_ids = tokenizer.encode(
        context,
        add_special_tokens=False,
        return_tensors="pt",
    )

    input_len = len(token_ids[0])

    config = {
        'top_k': 500,
        'top_p': 1.0,
        'temperature': 0.8,
        'repetition_penalty': 1.05,
        'max_tokens': input_len + 100,
        'seed': randint(0, 1000),
    }
    
    # Define the sampling parameters
    sampling_params = SamplingParams(**config)
    # sampling_params = SamplingParams(temperature=0.8, top_p=0.95)

    print(token_ids, flush=True)
    print(token_ids.tolist(), flush=True)
    
    # Generate a response
    response = model.generate(
        prompt_token_ids=token_ids.tolist(),
        sampling_params=sampling_params,
    )
    
    # Print the response
    print(response, flush=True)
    print(response[0].outputs[0].text, flush=True)

    end_time = time()

    print(f"Time taken: {end_time - start_time} seconds", flush=True)


def stablelm():
    model_name = 'rinna/japanese-gpt-neox-3.6b-instruction-ppo'

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)

    model = LLM(
        model=model_name,
        dtype="float16",
        max_model_len=256,
    )

    context = "私は"

    start_time = time()

    token_ids = tokenizer.encode(context, add_special_tokens=False, return_tensors="pt")

    sampling_params = SamplingParams(
        ignore_eos=True,
        max_tokens=16,
    )

    print(token_ids, flush=True)
    print(token_ids.tolist(), flush=True)

    response = model.generate(
        prompt_token_ids=token_ids.input_ids,
        sampling_params=sampling_params,
    )

    print(response, flush=True)
    print(response[0].outputs[0].text, flush=True)

    end_time = time()

    print(f"Time taken: {end_time - start_time} seconds", flush=True)



if __name__ == "__main__":
    transformers_rinna()
    # rinna()
    # stablelm()

