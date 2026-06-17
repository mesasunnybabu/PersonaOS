# PersonaOS — Retrieval & Response Evaluation Report

**Evaluated:** 2026-06-17
**Samples:** 4 real conversation exchanges from live usage
**Method:** Custom LLM-as-judge pipeline (Groq `llama-3.3-70b-versatile`)

| Metric | Score | What it measures |
|---|---|---|
| Context Precision | 0.792 | Fraction of retrieved memories that were actually relevant to the question |
| Context Recall | 0.825 | Fraction of needed information that retrieval successfully surfaced |
| Faithfulness | 0.725 | Whether responses avoid fabricating claims about conversation history |
| Answer Relevancy | 0.750 | Whether responses directly address the question asked |

## Methodology
A test set of 4 real question/answer pairs was built from
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
