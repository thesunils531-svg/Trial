"""Agent definitions and orchestration for the equity-research War Room."""

from dataclasses import dataclass
from typing import Iterator

import anthropic

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8000
MAX_CONTINUATIONS = 3

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}

COMMON_RULES = """\
You are one seat at a coordinated equity-research "War Room" — a team of expert agents
jointly investigating a single company for a smart, non-expert reader who wants the
clearest possible picture so they can decide for themselves. This is research, not
financial advice.

Ground rules for every seat:
- When you cite a number (revenue, margin, debt, P/E, etc.), search the web for it and
  say how current it is (e.g. "Q2 FY26, reported Aug 2026") and whether you are
  confident in it or unsure.
- Never invent a number. If you can't find something reliable, say so plainly instead
  of guessing.
- Use zero unexplained jargon — if you use a term like ROCE or EV/EBITDA, define it in
  one short clause the first time.
- Be concrete and specific. Avoid vague filler like "strong fundamentals" without the
  number behind it.
- Write for someone reading a research report, not a chat message: clear prose and
  markdown structure (##/### headers, bullet lists, bold for key figures), but no
  fluff, no restating the question, no meta-commentary about your own process.
"""


@dataclass
class Stage:
    id: str
    title: str
    use_search: bool
    prompt: str


STAGES = [
    Stage(
        id="analyst",
        title="1. Analyst — Business & Financials",
        use_search=True,
        prompt="""\
Explain in plain terms what this company actually makes money from (its real business
model, not the elevator pitch). Then pull the latest figures you can find and lay them
out clearly:
- Revenue and profit trend (last 3-5 years or quarters, whichever is more current)
- Margins (gross, operating, net) and the trend
- Debt load and balance-sheet health
- Cash flow (operating cash flow, free cash flow)
- Return ratios: ROE and/or ROCE/ROIC, with a one-line definition the first time you
  use the term

For every figure, mark it clearly as one of:
- **Current** (you found a recent, dated figure) — give the as-of date
- **Unsure** (you found something but it may be stale, from a secondary source, or you
  are not fully confident) — say why

End with a short "What I'm confident about vs. not" summary in 2-4 bullets.""",
    ),
    Stage(
        id="valuation",
        title="2. Valuation — Cheap or Expensive?",
        use_search=True,
        prompt="""\
Using the business/financials context above, answer: is this stock cheap or expensive
right now?

- Pull current P/E, P/B, and EV/EBITDA (define each briefly on first use)
- Compare each multiple against (a) the company's own historical range over the last
  few years and (b) its closest public peers/competitors — name the peers you're using
- State plainly whether the market currently looks optimistic, pessimistic, or
  roughly neutral about this company's future, and what that pricing seems to be
  betting on

Mark every multiple and comparison as Current or Unsure, same as above.""",
    ),
    Stage(
        id="bull",
        title="3. The Bull Case — Buy at Today's Price",
        use_search=True,
        prompt="""\
Using everything established above, build the single strongest, most honest case an
informed investor could make to BUY this stock at today's price. Steel-man it — this
is not a sales pitch, it's the best real argument.

Cover:
- The 2-4 specific growth drivers or catalysts that could play out (new products,
  market expansion, cost cuts, industry tailwind, etc.) — be concrete about what and
  when, not just "growth potential"
- Why the upside is real given the valuation and financials already discussed
- What would have to go right for this to work out

If you find supporting news, guidance, or analyst commentary, search for it and cite
how current it is.""",
    ),
    Stage(
        id="bear",
        title="4. The Bear Case — Avoid or Wait",
        use_search=True,
        prompt="""\
Using everything established above (including the Bull case), build the single
strongest, most honest case an informed investor could make to AVOID this stock or
WAIT before buying. Steel-man it the same way — the real risks, not throwaway
disclaimers.

Cover:
- Concrete risks: competition, regulation, debt/balance-sheet fragility, execution
  risk, customer concentration, whatever is actually specific to this company
- Directly attack the Bull case's weakest 1-2 claims — where is the bull thesis most
  fragile or dependent on things going right?
- What would have to go wrong for the stock to fall or underperform

If you find supporting news, downgrades, litigation, or risk disclosures, search for
them and cite how current they are.""",
    ),
    Stage(
        id="fact_checker",
        title="5. Fact-Check — Verify Every Number",
        use_search=True,
        prompt="""\
This is the most important step. Go through every important number and claim used by
the Analyst, Valuation, Bull, and Bear sections above, out loud and ruthlessly.

For each one:
- Search to verify it independently where you can
- Label it exactly one of: **Verified** (you confirmed it against a source),
  **Unverified** (plausible but you couldn't confirm it), or **Likely-wrong**
  (contradicted by what you found)
- If a claim is confident-sounding but unsupported, say so explicitly and either
  correct it with the right figure (cited) or flag it as unsupported — do not let it
  pass silently
- Note any numbers used inconsistently between sections (e.g. Bull and Bear citing
  different revenue figures)

End with a short list of which specific claims from the Bull case and which from the
Bear case actually survived fact-checking, since the Judge will only weigh those.""",
    ),
    Stage(
        id="judge",
        title="6. Judge — Decision Dossier",
        use_search=False,
        prompt="""\
You are the final judge. Weigh only what actually survived the fact-check above —
ignore any claim marked Likely-wrong, and treat Unverified claims as weaker evidence
than Verified ones. Do not re-open the research; synthesize what the team already
found.

Deliver a DECISION DOSSIER for a smart non-expert reader, using exactly these
sections, in this order, with these headers:

## The Read
Bullish, neutral, or cautious at today's price — and how confident you honestly are
(low/medium/high confidence), in 1-2 sentences.

## Why
The 3-4 factors that actually decided your call, using only claims that survived the
fact-check. One line each.

## Valuation Verdict
Cheap, fair, or expensive, in one line, with the one number that most supports it.

## The Biggest Risk
The single thing most likely to make this call wrong — be specific, not generic.

## What Would Change The View
The specific event or number that would flip your read (e.g. "if Q3 margins fall
below X%" or "if [product] launch slips past [date]").

## Verify Before You Act
The exact figures or claims the reader should personally confirm before acting,
because they may be stale, uncertain, or time-sensitive — reference the specific
Unverified items from the fact-check.

## Position Thinking (not advice)
How someone might size and stage an entry to manage risk, and what would make this a
"wait" instead of a "now" — framed as risk-management thinking, never as a
recommendation or instruction.

Then end with exactly one final line, on its own, reading essentially:
"This is research, not a recommendation, and prices and fundamentals change — some
figures above may already be out of date; verify anything that matters to your
decision."
""",
    ),
]


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def run_stage(stage: Stage, company: str, case_file: str) -> Iterator[dict]:
    """Run one War Room stage, yielding streaming events.

    Yields dicts of the form:
      {"type": "delta", "text": "..."}
      {"type": "search"}
      {"type": "done", "text": "<full stage text>"}
    """
    client = _client()

    user_content = f"Company under review: {company}\n\n"
    if case_file:
        user_content += (
            "Here is what the rest of the War Room team has found so far — "
            "build on it, don't repeat it:\n\n" + case_file + "\n---\n\n"
        )
    user_content += stage.prompt

    messages = [{"role": "user", "content": user_content}]
    tools = [WEB_SEARCH_TOOL] if stage.use_search else []

    full_text = ""
    continuations = 0

    while True:
        kwargs = dict(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=COMMON_RULES,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
        )
        if tools:
            kwargs["tools"] = tools

        with client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if getattr(event.content_block, "type", None) == "server_tool_use":
                        yield {"type": "search"}
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        full_text += event.delta.text
                        yield {"type": "delta", "text": event.delta.text}
            final = stream.get_final_message()

        if final.stop_reason == "pause_turn":
            continuations += 1
            if continuations > MAX_CONTINUATIONS:
                break
            messages.append({"role": "assistant", "content": final.content})
            continue

        break

    yield {"type": "done", "text": full_text}
