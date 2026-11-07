"""SageMaker scikit-learn script-mode entry point: training AND inference handlers.

Model: TF-IDF (word + character n-grams) -> LogisticRegression, predicting the listing category
from "title + notes".
"""
import argparse
import csv
import json
import os

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline


def build_pipeline():
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True)),
    ])
    return Pipeline([("tfidf", features), ("clf", LogisticRegression(max_iter=2000, C=5.0))])


def load_rows(train_dir):
    path = os.path.join(train_dir, "seed_listings.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    texts = [f"{r['title']} {r['notes']}" for r in rows]
    labels = [r["category"] for r in rows]
    return texts, labels


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default=os.environ.get("SM_CHANNEL_TRAIN", "ml/data"))
    parser.add_argument("--model-dir", default=os.environ.get("SM_MODEL_DIR", "model"))
    args, _ = parser.parse_known_args()

    texts, labels = load_rows(args.train)
    print(f"loaded {len(texts)} listings, {len(set(labels))} categories")

    x_tr, x_te, y_tr, y_te = train_test_split(texts, labels, test_size=0.2, random_state=7, stratify=labels)
    check = build_pipeline().fit(x_tr, y_tr)
    acc = accuracy_score(y_te, check.predict(x_te))
    print(f"holdout_accuracy={acc:.4f}")

    final = build_pipeline().fit(texts, labels)  # refit on everything for the deployed model
    os.makedirs(args.model_dir, exist_ok=True)
    joblib.dump(final, os.path.join(args.model_dir, "model.joblib"))
    print("model saved")


# ----------------------------- inference handlers (used by the endpoint) -----------------------------
def model_fn(model_dir):
    return joblib.load(os.path.join(model_dir, "model.joblib"))


def input_fn(request_body, content_type="application/json"):
    data = json.loads(request_body)
    items = data if isinstance(data, list) else [data]
    return [f"{i.get('title', '')} {i.get('notes', '')}".strip() for i in items]


def predict_fn(texts, model):
    probs = model.predict_proba(texts)
    classes = model.classes_
    out = []
    for row in probs:
        best = int(row.argmax())
        out.append({"category": str(classes[best]), "confidence": round(float(row[best]), 4)})
    return out


def output_fn(prediction, accept="application/json"):
    return json.dumps(prediction), "application/json"
