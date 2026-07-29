
# AI Test Case & Quality Risk Generator

An AI agent that takes a software requirements document (`.docx`) and automatically generates **test cases**, **edge cases**, and **quality risk flags** — grounded with RAG so output reflects real testing standards and past examples instead of generic LLM guesses.

**[Live Demo](https://app-testing-agent.streamlit.app/)** · **[Report a bug](https://github.com/roopvai/srs-test-agent/issues)**

---

## The problem

QA teams spend a large amount of time manually translating requirements documents into test cases. This process is inconsistent between engineers, prone to missed edge cases, and doesn't catch quality problems in the requirements themselves — ambiguity, missing acceptance criteria, untestable language — until much later, when they're expensive to fix.

This project explores whether an LLM agent, grounded with retrieval, can generate a strong first draft of test coverage and flag requirement-quality risks early, while keeping a human in the loop for final review.

## How it works

```
SRS Document (.docx)
        │
        ▼
  Parse & chunk into individual requirement units
        │
        ▼
  For each requirement:
        │
        ├──► Embed requirement (Amazon Titan Embeddings)
        │           │
        │           ▼
        │    Retrieve similar context from knowledge base (Pinecone)
        │           │
        ▼           ▼
  ┌─────────────────────────────────────────────┐
  │  Three independent generation passes          │
  │  (each with its own prompt + retrieval)       │
  │                                                │
  │  1. Test Cases   — coverage-focused           │
  │  2. Edge Cases   — adversarial, boundary/fail │
  │  3. Quality Risks — ambiguity, conflicts,     │
  │                     untestable requirements   │
  └─────────────────────────────────────────────┘
        │
        ▼
  Structured JSON validated against Pydantic schemas
        │
        ▼
  Streamlit UI — tables + CSV export
```

**Why three separate passes instead of one prompt?** Each task requires a different mode of reasoning. Test case generation is about coverage. Edge case generation is adversarial ("what would break this") and is given the already-generated test cases so it avoids duplicating them. Quality risk analysis needs the *whole document* as context (not just retrieved examples) to catch cross-requirement conflicts. Splitting these into focused passes with tailored prompts and retrieval produced noticeably better output than asking for everything in a single call.

**Why RAG?** A raw LLM call produces plausible but generic test cases. The knowledge base is seeded with testing heuristics (boundary-value analysis, negative testing conventions), past requirement/test-case pairs, and historical defect patterns — so generated output is grounded in what "good" looks like for this domain, and can be updated incrementally as conventions evolve, without retraining anything.

## Stack

| Layer | Technology |
|---|---|
| LLM inference | Amazon Bedrock (Claude) |
| Embeddings | Amazon Titan Embeddings v2 |
| Vector database | Pinecone |
| Schema validation | Pydantic |
| Document parsing | python-docx |
| UI | Streamlit |
| Hosting | Streamlit Community Cloud |

## Validation

Rather than just eyeballing output, the system was tested with a self-designed check: a 49-requirement sample SRS document included two deliberately vague, untestable requirements planted on purpose (e.g., *"the system should make user management easy and intuitive for administrators"*).

**Result:** the quality-risk pass correctly flagged the planted requirement as `untestable` in 5 separate detections, each with a distinct, specific rationale (subjective language, missing measurable criteria, non-mandatory "should" vs. "shall" phrasing).

The system also caught issues that weren't deliberately planted, including:
- A user-enumeration security gap (distinct "email not found" vs. "wrong password" error messages)
- Cross-requirement role-definition conflicts between separate sections of the document
- Missing malware/MIME-type validation on file upload requirements

Sample output: [`/samples`](./samples) contains the generated test cases, edge cases, and quality risks CSVs from a full run against the included sample SRS document.

## Getting started

### Prerequisites
- Python 3.11 (3.13 has known compatibility issues with some dependencies used here, e.g. `orjson`)
- An AWS account with Amazon Bedrock model access enabled (Anthropic Claude + Titan Embeddings)
- A Pinecone account (free tier is sufficient)

### Setup

```bash
git clone https://github.com/roopvai/srs-test-agent.git
cd srs-test-agent

python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=srs-agent-kb
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
EMBED_MODEL_ID=amazon.titan-embed-text-v2:0
```

Create a Pinecone index named to match `PINECONE_INDEX_NAME`, with dimension `1024` (matching Titan Embeddings v2) and cosine similarity metric.

### Run locally

```bash
streamlit run app.py
```

Open `http://localhost:8501`, upload an `.docx` requirements document, and click **Analyze**.

## Project structure

```
srs-test-agent/
├── app.py                  # Streamlit UI and orchestration loop
├── src/
│   ├── bedrock_client.py   # Bedrock InvokeModel wrapper
│   ├── vectorstore.py      # Embedding + Pinecone upsert/retrieve
│   ├── ingestion.py        # .docx parsing
│   ├── chunking.py         # Splits document into requirement units
│   ├── schemas.py          # Pydantic models for structured output
│   ├── prompts.py          # System prompts for each generation pass
│   ├── generators.py       # Retrieval + generation logic per pass
│   └── config.py           # Local .env / Streamlit Cloud secrets bridge
├── samples/                # Sample SRS input + generated output
└── requirements.txt
```

## Known limitations & next steps

This was built as a working prototype to validate the approach, not a production system. Known gaps and what I'd address next:

- **Chunking is regex-based** and depends on consistent requirement numbering in the source document. A more robust version would use an LLM call to semantically segment requirements, rather than relying on formatting patterns.
- **No formal evaluation harness yet.** Validation so far is the planted-ambiguity test described above. Next step: a golden dataset of requirements paired with human-approved test cases, scored for precision/recall, to benchmark prompt and retrieval changes objectively.
- **Sequential processing.** Each requirement is processed one at a time (3 Bedrock calls each), which is slow for large documents. A production version would batch or parallelize calls with rate-limit-aware concurrency.
- **No human-in-the-loop review gate yet** in the UI itself — low-confidence or borderline outputs should route to a reviewer queue rather than being treated identically to high-confidence output.
- **Single shared knowledge base.** A multi-tenant/consulting deployment would need per-client knowledge base isolation.

## License

MIT
EOF
