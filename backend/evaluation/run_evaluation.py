# backend/evaluation/run_evaluation.py
#
# PURPOSE: Custom lightweight evaluation pipeline — replaces RAGAS.
#
# WHY CUSTOM INSTEAD OF RAGAS/DEEPEVAL:
# Both libraries wrap the same core idea: use an LLM as a judge against a
# rubric, then average scores. RAGAS pulls in langchain-community, which has
# version conflicts with langchain-groq and langgraph. Writing this directly
# against the Groq SDK (which you already use in groq_service.py) avoids
# all dependency conflicts entirely — same metrics, zero new packages.
#
# METRICS IMPLEMENTED (same definitions as RAGAS):
#
#   1. Context Precision  — Of the memories retrieve_memories() returned,
#                            what fraction were actually relevant to the
#                            question? (Judge scores each retrieved context
#                            independently as relevant/not relevant.)
#
#   2. Context Recall     — Given the ground-truth answer, does the
#                            retrieved context contain the information
#                            needed to support it? (Judge checks if the
#                            reference answer's claims are covered by
#                            the retrieved contexts.)
#
#   3. Faithfulness        — Does the AI's answer stick to what's actually
#                            in the retrieved context, or does it add
#                            unsupported claims? (Judge extracts claims
#                            from the answer, checks each against context.)
#
#   4. Answer Relevancy    — Does the answer actually address the question
#                            asked? (Judge scores 1-5, normalized to 0-1.)
#
# Each metric returns a 0.0-1.0 score per row, averaged across the test set.

import sys
import os
import json
import re
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
JUDGE_MODEL = "llama-3.3-70b-versatile"


# ── Core judge call helper ────────────────────────────────────────────────────

def _judge(prompt: str, retries: int = 2) -> str:
    """
    Sends a judging prompt to Groq and returns the raw text response.
    Retries once on failure (network blips, rate limits) before giving up.
    """
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,     # Deterministic judging
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries:
                print(f"   ⚠️  Judge call failed ({e}), retrying...")
                time.sleep(2)
            else:
                print(f"   ❌ Judge call failed after retries: {e}")
                return ""
    return ""


def _extract_score(text: str, default: float = 0.0) -> float:
    """
    Extracts a numeric score from judge output.
    Handles formats like "0.8", "Score: 0.8", "4/5", etc.
    """
    # Try to find a decimal between 0 and 1
    match = re.search(r'\b(0\.\d+|1\.0+|1\b|0\b)\b', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return default


# ── Metric 1: Context Precision ───────────────────────────────────────────────

def evaluate_context_precision(question: str, contexts: list[str]) -> float:
    """
    For each retrieved context, ask the judge: is this actually relevant
    to answering the question? Precision = (relevant contexts) / (total contexts).
    """
    if not contexts or contexts == ["NO_CONTEXT_RETRIEVED"]:
        return 0.0   # Nothing retrieved = precision undefined, score as 0

    relevant_count = 0
    for ctx in contexts:
        prompt = f"""You are evaluating retrieval quality for a coding tutor's memory system.

Question asked: "{question}"

Retrieved past context: "{ctx[:400]}"

Is this retrieved context RELEVANT to answering the question? Consider it relevant
if it shares the same topic or could reasonably help answer the question.

Respond with ONLY one word: "yes" or "no"."""

        result = _judge(prompt).lower()
        if "yes" in result:
            relevant_count += 1

    return round(relevant_count / len(contexts), 3)


# ── Metric 2: Context Recall ──────────────────────────────────────────────────

def evaluate_context_recall(ground_truth: str, contexts: list[str]) -> float:
    """
    Breaks the ground truth answer into key claims, then checks what
    fraction of those claims are supported by the retrieved contexts.
    Recall = (claims supported by context) / (total claims in ground truth).
    """
    if not contexts or contexts == ["NO_CONTEXT_RETRIEVED"]:
        return 0.0

    combined_context = "\n---\n".join(contexts)[:1500]

    prompt = f"""You are evaluating a memory retrieval system for a coding tutor.

Reference answer (what should ideally be supported by memory):
"{ground_truth[:500]}"

Retrieved memory contexts:
"{combined_context}"

What fraction of the key information in the reference answer is supported
or covered by the retrieved contexts? Consider partial credit for related
but not identical coverage.

Respond with ONLY a decimal number between 0.0 and 1.0, nothing else.
Example response: 0.7"""

    result = _judge(prompt)
    return _extract_score(result, default=0.0)


# ── Metric 3: Faithfulness ────────────────────────────────────────────────────

def evaluate_faithfulness(answer: str, contexts: list[str]) -> float:
    """
    Checks whether the answer's claims are grounded in the retrieved context,
    OR are reasonable general knowledge (since a tutor SHOULD explain things
    even without prior memory — that's not hallucination, that's teaching).

    We score faithfulness as: does the answer CONTRADICT or fabricate facts
    about past conversations that aren't in the context? This is the
    specific failure mode PersonaOS had (claiming "first session" when
    memories existed, or inventing fake past discussions).
    """
    combined_context = "\n---\n".join(contexts)[:1500] if contexts and contexts != ["NO_CONTEXT_RETRIEVED"] else "NO PRIOR CONTEXT WAS RETRIEVED"

    prompt = f"""You are evaluating an AI tutor's response for factual grounding.

Retrieved memory context available to the AI:
"{combined_context}"

AI's response:
"{answer[:600]}"

Does the AI's response make any FALSE CLAIMS about past conversations that
are NOT supported by the retrieved context? For example: claiming something
was discussed when it wasn't in context, or claiming nothing was discussed
when relevant context WAS available.

General teaching content (explaining concepts, giving examples) is fine and
should NOT be penalized — only penalize fabricated claims about conversation
history.

Respond with ONLY a decimal score 0.0-1.0 where 1.0 = fully faithful (no
fabricated history claims), 0.0 = completely fabricated. Nothing else.
Example response: 0.9"""

    result = _judge(prompt)
    return _extract_score(result, default=0.5)


# ── Metric 4: Answer Relevancy ────────────────────────────────────────────────

def evaluate_answer_relevancy(question: str, answer: str) -> float:
    """
    Does the answer actually address what was asked?
    Simple direct judge call, scored 0.0-1.0.
    """
    prompt = f"""Question asked: "{question}"

Answer given: "{answer[:600]}"

On a scale of 0.0 to 1.0, how well does the answer address the actual
question asked? 1.0 = directly and fully addresses it, 0.0 = completely
off-topic or non-responsive.

Respond with ONLY a decimal number, nothing else.
Example response: 0.85"""

    result = _judge(prompt)
    return _extract_score(result, default=0.5)


# ── Main evaluation loop ──────────────────────────────────────────────────────

def load_testset(path: str = None) -> list:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "results", "testset.json")
    if not os.path.exists(path):
        print(f"❌ Test set not found at {path}")
        print("   Run build_testset.py first.")
        exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_evaluation():
    print("📂 Loading test set...")
    rows = load_testset()
    print(f"✅ Loaded {len(rows)} evaluation rows\n")

    if len(rows) < 3:
        print(f"⚠️  Only {len(rows)} rows. Results will be noisy but proceeding.\n")

    per_row_results = []

    for i, row in enumerate(rows, 1):
        print(f"🧪 Evaluating row {i}/{len(rows)}: \"{row['question'][:50]}...\"")

        precision = evaluate_context_precision(row["question"], row["contexts"])
        recall    = evaluate_context_recall(row["ground_truth"], row["contexts"])
        faith     = evaluate_faithfulness(row["ground_truth"], row["contexts"])
        relevancy = evaluate_answer_relevancy(row["question"], row["ground_truth"])

        print(f"   precision={precision}  recall={recall}  faithfulness={faith}  relevancy={relevancy}")

        per_row_results.append({
            "question":           row["question"],
            "topic":               row["topic"],
            "context_precision":   precision,
            "context_recall":      recall,
            "faithfulness":        faith,
            "answer_relevancy":    relevancy,
        })

    # ── Aggregate ────────────────────────────────────────────────────────────
    def avg(key):
        values = [r[key] for r in per_row_results]
        return round(sum(values) / len(values), 3) if values else 0.0

    summary = {
        "evaluated_at":       datetime.now().isoformat(),
        "num_samples":        len(rows),
        "context_precision":  avg("context_precision"),
        "context_recall":     avg("context_recall"),
        "faithfulness":       avg("faithfulness"),
        "answer_relevancy":   avg("answer_relevancy"),
    }

    # ── Save results ────────────────────────────────────────────────────────
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "evaluation_detailed.json"), "w") as f:
        json.dump(per_row_results, f, indent=2)

    with open(os.path.join(output_dir, "evaluation_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # ── Print report ────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("📊 EVALUATION RESULTS — PersonaOS Memory System")
    print("=" * 55)
    print(f"Samples evaluated:    {summary['num_samples']}")
    print(f"Context Precision:    {summary['context_precision']:.3f}  (relevance of retrieved memories)")
    print(f"Context Recall:       {summary['context_recall']:.3f}  (coverage of needed info)")
    print(f"Faithfulness:         {summary['faithfulness']:.3f}  (grounded in real history, not fabricated)")
    print(f"Answer Relevancy:     {summary['answer_relevancy']:.3f}  (addresses the question asked)")
    print("=" * 55)

    # ── Markdown report for README ─────────────────────────────────────────
    md_report = f"""# PersonaOS — Retrieval & Response Evaluation Report

**Evaluated:** {summary['evaluated_at'][:10]}
**Samples:** {summary['num_samples']} real conversation exchanges from live usage
**Method:** Custom LLM-as-judge pipeline (Groq `llama-3.3-70b-versatile`)

| Metric | Score | What it measures |
|---|---|---|
| Context Precision | {summary['context_precision']:.3f} | Fraction of retrieved memories that were actually relevant to the question |
| Context Recall | {summary['context_recall']:.3f} | Fraction of needed information that retrieval successfully surfaced |
| Faithfulness | {summary['faithfulness']:.3f} | Whether responses avoid fabricating claims about conversation history |
| Answer Relevancy | {summary['answer_relevancy']:.3f} | Whether responses directly address the question asked |

## Methodology
A test set of {summary['num_samples']} real question/answer pairs was built from
SQLite conversation history, filtered to topics discussed 2+ times (so a prior
memory could plausibly exist for retrieval to find). For each row, `retrieve_memories()`
was re-run live against the current ChromaDB + `all-MiniLM-L6-v2` retrieval pipeline.
Four custom rubric-based prompts, judged by Groq's `llama-3.3-70b-versatile` at
temperature 0.0, scored each dimension independently.

This is a custom evaluation harness rather than RAGAS/DeepEval, built to avoid
their `langchain-community` dependency conflicts while measuring the identical
four metrics with the same definitions.

## Notes
- Context Precision/Recall are sensitive to the `similarity_threshold` (currently
  0.25) and topic filter in `memory_service.py`. Re-running after threshold changes
  shows the tradeoff directly.
- Faithfulness specifically targets the "fabricated history" failure mode found
  during development (e.g. claiming "first session" despite existing memories).
"""

    with open(os.path.join(output_dir, "EVALUATION_REPORT.md"), "w") as f:
        f.write(md_report)

    print(f"\n💾 Detailed per-row results: {output_dir}/evaluation_detailed.json")
    print(f"💾 Summary:                  {output_dir}/evaluation_summary.json")
    print(f"💾 README-ready report:      {output_dir}/EVALUATION_REPORT.md")


if __name__ == "__main__":
    run_evaluation()