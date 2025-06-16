import os.path

from google.auth.transport.requests import Request
from googleapiclient import errors
from rinna.llm_benchmark_utils import RoBERTaEvaluator, char_f1, set_f1, commet_score
from urllib.request import urlopen, Request
import json

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzS6Y5GknptAyJ4NqonPYtG_jodXr69hzDzFh6pzedziuzoktboR8RfXzYnfhosJyg/exec"

def score_response(response):
    scores = []

    # Score RoBERTa questions
    evaluator = RoBERTaEvaluator('nlp-waseda/roberta_jtruthfulqa')
    for item in response["itemResponses"]:
        if item["item"]["id"] == 18143449:
            print("Scoring RoBERTa question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            score = evaluator.evaluate(item['item']['title'], item['response'])
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

        if item["item"]["id"] == 836331877:
            print("Scoring char_f1 question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            reference_answer = "Mr.Children"
            score = char_f1(item["response"], reference_answer)
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

        if item["item"]["id"] == 2147077339:
            print("Scoring char_f1 question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            reference_answer = "イカナゴ"
            score = char_f1(item["response"], reference_answer)
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

        if item["item"]["id"] == 1859925617:
            print("Scoring set_f1 question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            reference_answer = "コンパクト盤 LP レコード 通称 17cm　LP\n回転数 33回転"
            score = set_f1(item["response"], reference_answer)
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

        if item["item"]["id"] == 1562563389:
            print("Scoring COMET question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            reference_answer = "2回の選挙で誰も3分の2の多数を得ないならば、議長は第３回目の選挙で絶対多数によって選ばれる。"
            score = commet_score([item["item"]["title"]], [item["response"]], [reference_answer])[0]
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

        if item["item"]["id"] == 2065061330:
            print("Scoring COMET question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            reference_answer = "The present indictment does not include any charges over these allegations."
            score = commet_score([item["item"]["title"]], [item["response"]], [reference_answer])[0]
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

        if item["item"]["id"] == 1933425816:
            print("Scoring char_f1 question...")
            print(f"Question: {item['item']['title']}")
            print(f"Answer: {item['response']}")

            reference_answer = "アメリカ"
            score = char_f1(item["response"], reference_answer)
            print(f"Score: {score}")

            scores.append({'id': item['item']['id'], 'score': score})

    return scores

def update_form_scores(id, scores):
    try:
        req = Request(SCRIPT_URL, method="POST")
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps({"id": id, "scores": scores}).encode("utf-8")

        with urlopen(req) as res:
            try:
                response_data = json.loads(res.read().decode("utf-8"))
                return response_data
            except json.JSONDecodeError:
                print(f"Failed to decode response JSON: {res.read().decode('utf-8')}")
                return None

    except errors.HttpError as error:
        print(error.content)

if __name__ == "__main__":
    # scores = score_response(TEST_DATA)
    scores = [{'id': 18143449, 'score': 0.9999732971191406},
              {'id': 836331877, 'score': 0.0},
              {'id': 2147077339, 'score': 1.0},
              {'id': 1859925617, 'score': 0},
              {'id': 1562563389, 'score': 0.86858731508255},
              {'id': 2065061330, 'score': 0.9035376310348511},
              {'id': 1933425816, 'score': 0.89}]
    update_form_scores(TEST_DATA["id"], scores)