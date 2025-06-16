import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from fuzzywuzzy import fuzz
from comet import download_model, load_from_checkpoint

class RoBERTaEvaluator:
    def __init__(self, model_name):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)

    def evaluate(self, question, answer):
        inputs = self.tokenizer(question + " " + answer, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
        return probabilities[0][1].item()

def char_f1(y_pred: str, y_true: str) -> float:
    return fuzz.token_sort_ratio(y_pred, y_true) / 100.0

def set_f1(y_pred: str, y_true: str) -> float:
    set_y_true: list[str] = [x.strip() for x in y_true.split("\n")]
    set_y_pred: list[str] = list({x.strip() for x in y_pred.split("\n")})
    set_pre = sum([1 if y in set_y_true else 0 for y in set_y_pred]) / len(set_y_pred)
    set_rec = sum([1 if y in set_y_true else 0 for y in set_y_pred]) / len(set_y_true)
    set_f1 = (
        2 * (set_pre * set_rec) / (set_pre + set_rec) if (set_pre + set_rec) != 0 else 0
    )
    return set_f1

def commet_score(commet_srcs, commet_mt, commet_ref):
    print("--------downloading comet model to evaluate translation task--------")
    comet_model_path = download_model("Unbabel/wmt22-comet-da")
    comet_model = load_from_checkpoint(comet_model_path)
    comet_data = []
    for i in range(len(commet_srcs)):
        comet_instance = {}
        comet_instance["src"] = commet_srcs[i]
        comet_instance["mt"] = commet_mt[i]
        comet_instance["ref"] = commet_ref[i]
        comet_data.append(comet_instance)
    scores = comet_model.predict(comet_data, batch_size=8, gpus=1, progress_bar=False).scores
    #delete_model_directory(comet_model_path)
    return scores
