"""
Auto Labeling with Foundation Models - IMDb Sentiment Demo
===========================================================

Written test (Wuwei Data): demonstrate how a foundation model can
automatically generate labels for a public dataset.

Dataset : IMDb movie reviews (https://huggingface.co/datasets/imdb), 50k reviews,
          each with a human-provided sentiment label (0 = negative, 1 = positive).
Task    : automatically label the sentiment of each review.
Model   :
    - backend "hf" (default): DistilBERT fine-tuned on SST-2, runs fully
      locally, no API key needed.
    - backend "llm": any OpenAI-compatible chat endpoint (set env vars
      OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL), demonstrating the
      LLM + prompt-template approach.

Usage:
    python demo_code.py --num-samples 50 --backend hf
    HF_ENDPOINT=https://hf-mirror.com python demo_code.py   # mainland China mirror
"""

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path

# Mainland-China-friendly default; harmless elsewhere.
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

DEFAULT_MODEL = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"

# ---------------------------------------------------------------------------
# Prompt template used by the "llm" backend (also shown in the report).
# The model must answer with a single JSON object: {"label": "positive"|"negative"}
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """You are a sentiment labeling assistant.
Label the sentiment of the following movie review as exactly one word:
"positive" or "negative".

Examples:
Review: "An absolute masterpiece - the acting, the pacing, the score, everything works."
Label: positive
Review: "Two hours of my life I will never get back. Boring and predictable."
Label: negative

Now label this review:
Review: "{text}"
Label:"""


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------
def load_imdb_samples(num_samples: int, split: str = "test", seed: int = 42) -> list[dict]:
    """Stream the IMDb dataset and return a class-balanced sample.

    Each item: {"text": str, "human_label": "positive" | "negative"}
    """
    from datasets import load_dataset

    want_each = num_samples // 2
    # "stanfordnlp/imdb" is the namespaced id used by datasets>=4.0
    stream = load_dataset("stanfordnlp/imdb", split=split, streaming=True)

    buckets = {"positive": [], "negative": []}
    for ex in stream:
        label = "positive" if ex["label"] == 1 else "negative"
        if len(buckets[label]) < want_each:
            buckets[label].append({"text": ex["text"], "human_label": label})
        if all(len(v) >= want_each for v in buckets.values()):
            break

    samples = buckets["positive"] + buckets["negative"]
    random.Random(seed).shuffle(samples)
    return samples[:num_samples]


# ---------------------------------------------------------------------------
# Labeling backends
# ---------------------------------------------------------------------------
def label_with_hf(samples: list[dict], model_name: str) -> list[dict]:
    """Label with a local HuggingFace transformer (no API key required)."""
    from transformers import pipeline

    print(f"[hf] loading model: {model_name}")
    classifier = pipeline("sentiment-analysis", model=model_name)

    results = []
    texts = [s["text"] for s in samples]
    print(f"[hf] labeling {len(texts)} reviews ...")
    predictions = classifier(texts, truncation=True, max_length=512, batch_size=8)

    for sample, pred in zip(samples, predictions):
        results.append({
            **sample,
            "model_label": pred["label"].lower(),      # POSITIVE / NEGATIVE
            "model_score": round(float(pred["score"]), 4),
        })
    return results


def label_with_llm(samples: list[dict], model_name: str) -> list[dict]:
    """Label with any OpenAI-compatible chat endpoint.

    Env vars: OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL (optional).
    """
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", ""),
    )
    chat_model = model_name or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    results = []
    for i, sample in enumerate(samples, 1):
        prompt = PROMPT_TEMPLATE.format(text=sample["text"][:2000])
        resp = client.chat.completions.create(
            model=chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip().lower()
        label = "positive" if "positive" in answer and "negative" not in answer else "negative"
        results.append({**sample, "model_label": label, "model_score": ""})
        print(f"[llm] {i}/{len(samples)} -> {label}")
        time.sleep(0.2)
    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def save_outputs(results: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # example_output.csv - one row per review
    csv_path = output_dir / "example_output.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "human_label", "model_label", "model_score", "correct", "text"])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "human_label": r["human_label"],
                "model_label": r["model_label"],
                "model_score": r["model_score"],
                "correct": r["human_label"] == r["model_label"],
                "text": r["text"],
            })

    # summary.json - metrics for the report
    total = len(results)
    correct = sum(1 for r in results if r["human_label"] == r["model_label"])
    per_class = {}
    for label in ("positive", "negative"):
        subset = [r for r in results if r["human_label"] == label]
        acc = (sum(1 for r in subset if r["model_label"] == label) / len(subset)) if subset else 0
        per_class[label] = {"n": len(subset), "accuracy": round(acc, 4)}

    summary = {
        "model": "hf:distilbert-sst2" if os.environ.get("BACKEND_TAG", "hf") == "hf" else "llm",
        "num_samples": total,
        "accuracy": round(correct / total, 4) if total else 0,
        "per_class_recall": per_class,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[output] {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto labeling demo: IMDb sentiment")
    parser.add_argument("--num-samples", type=int, default=50, help="how many reviews to label")
    parser.add_argument("--split", default="test", choices=["test", "train"])
    parser.add_argument("--backend", default="hf", choices=["hf", "llm"])
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF model id (hf backend)")
    parser.add_argument("--output-dir", default=".", help="where to write example_output.csv")
    args = parser.parse_args()

    samples = load_imdb_samples(args.num_samples, split=args.split)
    print(f"[dataset] loaded {len(samples)} balanced IMDb reviews ({args.split} split)")

    if args.backend == "hf":
        results = label_with_hf(samples, args.model)
    else:
        results = label_with_llm(samples, args.model)

    save_outputs(results, Path(args.output_dir))


if __name__ == "__main__":
    main()
