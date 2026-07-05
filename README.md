# Equity Research War Room

A small web app that runs a coordinated team of research agents over a single company
and hands back a decision dossier — not financial advice, just the clearest picture
the team can put together.

The team runs in this order, each stage streaming live and building on the last:

1. **Analyst** — business model and financials (revenue, margins, debt, cash flow, ROE/ROCE)
2. **Valuation** — is it cheap or expensive vs. its own history and peers?
3. **Bull case** — the strongest honest case to buy at today's price
4. **Bear case** — the strongest honest case to avoid or wait, attacking the Bull case's weakest points
5. **Fact-check** — every number and claim above gets marked Verified / Unverified / Likely-wrong
6. **Judge** — weighs only what survived the fact-check and delivers the Decision Dossier

Each agent (other than the Judge) can search the web for current figures via Claude's
built-in web search tool, and is required to flag whether a number is current or
unsure rather than guess.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)   # or just `export ANTHROPIC_API_KEY=...`
```

## Run

```bash
uvicorn server:app --reload
```

Open http://127.0.0.1:8000, enter a company name or ticker, and click **Run the War
Room**. Each stage streams into its own card; the final Decision Dossier appears last.

## Notes

- Uses `claude-opus-4-8` with adaptive thinking and Anthropic's server-side web search
  tool — no separate financial-data API key needed.
- This is a single-request, single-user demo server (synchronous Anthropic calls per
  stage). It's not built for concurrent multi-user traffic.
- Output is research, not investment advice. Verify anything time-sensitive before
  acting on it.
