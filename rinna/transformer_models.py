from transformers import T5Tokenizer, AutoModelForCausalLM
import torch
import sys

tokenizer = T5Tokenizer.from_pretrained("rinna/japanese-gpt-1b")
model = AutoModelForCausalLM.from_pretrained("rinna/japanese-gpt-1b")

if torch.cuda.is_available() and sys.argv[1] == 'GPU':
    model = model.to("cuda")
    pass

print(f'Using {model.device} for processing rinna-signal')
