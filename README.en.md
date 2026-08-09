<p align="center">
  <img width="100%"
    alt="Finbom consultation interface with Poki, its financial guidance mascot"
    src="https://github.com/user-attachments/assets/595c2145-4a2c-48f8-9661-accb862e3bec"
  />
</p>

<h1 align="center">Finbom</h1>

<p align="center">
  A multi-turn financial assistant grounded in Korean law and financial-product disclosures
</p>

<p align="center">
  <a href="README.md">한국어</a> · <strong>English</strong>
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img alt="Python 3.13" src="https://img.shields.io/badge/Python-3.13-5D8BB7?style=flat-square&labelColor=0B1220&logo=python&logoColor=white">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img alt="FastAPI 0.138+" src="https://img.shields.io/badge/FastAPI-0.138+-5D8BB7?style=flat-square&labelColor=0B1220&logo=fastapi&logoColor=white">
  </a>
  <a href="https://docs.langchain.com/oss/python/langchain/overview">
    <img alt="LangChain Core 1.4+" src="https://img.shields.io/badge/LangChain_Core-1.4+-5D8BB7?style=flat-square&labelColor=0B1220">
  </a>
  <a href="https://docs.langchain.com/oss/python/langgraph/overview">
    <img alt="LangGraph 1.2+" src="https://img.shields.io/badge/LangGraph-1.2+-5D8BB7?style=flat-square&labelColor=0B1220">
  </a>
  <a href="https://nextjs.org/">
    <img alt="Next.js 16" src="https://img.shields.io/badge/Next.js-16-5D8BB7?style=flat-square&labelColor=0B1220&logo=next.js&logoColor=white">
  </a>
</p>

<p align="center">
  <a href="#financial-guidance-that-shows-its-sources">Overview</a> ·
  <a href="#current-capabilities">Capabilities</a> ·
  <a href="#how-finbom-works">How it works</a> ·
  <a href="#run-finbom">Run</a> ·
  <a href="#data-and-verification-evidence">Data &amp; verification</a> ·
  <a href="docs/README.md">Development docs (KO)</a>
</p>

---

## Financial guidance that shows its sources

For financial questions, verifying **which sources support an answer** matters as much as receiving
the answer itself. Finbom retrieves Korean depositor-protection and financial-consumer laws,
compares bank time-deposit and installment-savings candidates from Korea's Finlife disclosures, and
presents each answer alongside its evidence.

The consultation mascot **Poki** is Finbom's guide and the speaker users meet in the conversation.
Poki presents statutory provisions and product comparisons in a more approachable form.

> [!IMPORTANT]
> Finbom's answers and displayed sources from Korean public institutions are for reference only.
> They have no legal effect and do not constitute legal or financial advice.

## Current capabilities

- **Verify legal grounds** — presents the law, article number, and effective date for questions
  about depositor protection and financial-consumer rights.
- **Compare deposit and installment-savings candidates** — sorts Finlife bank disclosures by term
  and either base or maximum interest rate; installment-savings results also show whether each
  product uses fixed or flexible installments.
- **Clarify conditions across turns** — asks for one missing condition at a time and reuses confirmed
  conditions in the same consultation.
- **Combine laws and products** — retrieves both legal evidence and product disclosures when a
  question requires them together.
- **Separate answers from evidence** — streams the answer while keeping the cited laws and financial
  products visible in dedicated areas.

## How Finbom works

### System request flow

![A user question moves through the Next.js interface, FastAPI, and the LangGraph agent before returning an answer grounded in Korean law and Finlife disclosures](docs/assets/finbom-consultation-flow.svg)

The Next.js interface forwards requests through `POST /api/chat` and consumes the FastAPI
`/ask-agent/stream` response as Server-Sent Events (SSE), displaying status and answer updates in
order. Inside FastAPI, the LangGraph agent uses law-retrieval and Finlife product results, then
returns the answer separately from the evidence that was actually used.

### How Poki builds an answer

**Analyze the question** → **Confirm missing conditions** → **Retrieve laws and products** →
**Present the answer and its evidence**

When a condition is missing, Poki asks for one detail. When a question falls outside the supported
scope, Poki explains what the consultation can cover. Confirmed conditions remain available for the
next question in the same consultation.

> [See the LangGraph branches and evidence flow (KO) →](docs/07-langgraph-agent/README.md)

## Run Finbom

### Prerequisites

- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- Node.js 20.9 or later
- An [Anthropic API key](https://console.anthropic.com/) and a Finlife API key
- A macOS or Linux shell environment

The legal index is generated locally from the XML sources in this repository. Financial-product
data is fetched from Finlife at runtime, so both API keys are required to exercise the full
consultation flow.

### One-time setup

```bash
git clone https://github.com/SWHee/finbom-agent.git
cd finbom-agent
cp .env.example .env

uv sync --locked
uv run python scripts/build_index.py
npm --prefix frontend ci
```

Configure the runtime keys and generation model in the root `.env` file:

```dotenv
CHATBOT_BACKEND=anthropic
ANTHROPIC_API_KEY=<your-anthropic-api-key>
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
FINLIFE_API_KEY=<your-finlife-api-key>
```

### Start both servers

```bash
./scripts/run.sh
```

- Chat UI: `http://localhost:3001`
- FastAPI docs: `http://127.0.0.1:8000/docs`
- Stop both servers: `Ctrl+C`

### Start the servers separately

Use two terminals when you want separate logs:

```bash
# terminal 1
uv run fastapi dev
```

```bash
# terminal 2
npm --prefix frontend run dev
```

## Data and verification evidence

The legal corpus is an XML snapshot collected from Korea's National Law Information Open API. It
currently covers four documents: the Financial Consumer Protection Act, the Depositor Protection
Act, and both enforcement decrees. The snapshot date is **2026-07-06**.

- [Legal XML sources and collection notes (KO)](data/laws/README.md)
- [Versioned legal source files](data/laws/)
- [RAG development and regression dataset (KO)](data/evaluation/README.md)

The Chroma index (`data/index/`) is a reproducible local artifact and is not committed. Inspect the
stored article and chunk counts and confirm that retrieval is ready with:

```bash
uv run python scripts/verify_index.py
```

Law retrieval is centered on KURE-v1 embeddings and Chroma semantic search, with a low-weight BM25
signal to recover exact law names and key expressions. Reciprocal Rank Fusion (RRF) combines the two
ranked lists before duplicate articles are removed and the top evidence is passed to the agent.

Time-deposit and installment-savings data is fetched at request time from the bank disclosures
provided by Korea's Finlife API. A deterministic Python comparison selects candidates by term and
the requested interest-rate criterion; the LLM does not reorder the ranking.

This public README does not present development-set measurements as final agent performance.
Evaluation conditions, results, and limitations are recorded in the following documents:

- [Hybrid Search and BM25 comparison (KO)](docs/00-performance-improvement/04-retrieval-robustness/01-hybrid-search-bm25.md)
- [RAG regression baseline before and after the LangGraph migration (KO)](docs/03-langsmith-evaluation/11-langgraph-migration-results.md)
- [Agent evaluation dataset and validation contract (KO)](docs/07-langgraph-agent/05-agent-evaluation-dataset-contract.md)

## Scope and limitations

- The legal corpus is a fixed snapshot and is not synchronized in real time.
- Financial-product retrieval currently supports **bank time deposits and installment savings**.
- Product comparisons are condition-based candidate lists, not personalized determinations of the
  best financial product.
- Verify current laws, actual enrollment terms, and depositor-protection coverage with the relevant
  authority and financial institution.

## Development documentation

This public README covers only the current runnable features and usage. Planned implementation,
README hotfixes, architecture decisions, evaluations, experiments, troubleshooting notes, and
retrospectives are organized in the [development documentation hub (KO)](docs/README.md).

## Repository layout

```text
finbom-agent/
├── frontend/                 Finbom chat UI (Next.js, localhost:3001)
├── src/chatbot/              Agent, RAG, and FastAPI
├── data/laws/                Versioned legal XML snapshot
├── data/evaluation/          Development/regression datasets and fixtures
├── scripts/                  Run, collection, indexing, and verification commands
├── tests/                    Backend unit and flow tests
└── docs/                     Development, evaluation, and design notes
```

The initial [from-scratch Transformer implementation](experiments/from_scratch/README.md) is
archived separately from the current application.
