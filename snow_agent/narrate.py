"""Claude narration and chat over an already-computed BlastRadiusAssessment.

Uses llm_client.py's dual Anthropic/Azure-Foundry client, so this mode
runs on the same "put credentials in later" model throughout -- no code
changes needed to switch between a home setup and a locked-down company
laptop.

The model never re-runs the correlation or invents a number: both
functions below hand it the finished assessment as data and ask it to
either narrate or answer a question grounded in exactly that data.
"""

from __future__ import annotations

from snow_agent.llm_client import build_client
from snow_agent.report import to_json

MODEL = "claude-opus-5"

NARRATE_SYSTEM = """\
You narrate a ServiceNow blast-radius assessment for a non-technical \
leadership audience, in plain language. You are given the assessment as \
JSON -- use only what's in it. Never invent an incident, number, or \
system that isn't present in the data. Keep it to 3-5 sentences: what \
happened, how far it spreads, how confident the system is, and what to \
do next. State plainly that this is advisory only and requires human \
review before any action.
"""

CHAT_SYSTEM = """\
You answer questions about a ServiceNow blast-radius assessment, given as \
JSON. Answer only from that data -- if the question asks about something \
not in the assessment, say it isn't in the data rather than guessing. \
Keep answers short and concrete (cite incident numbers, the confidence \
score, or specific match reasons where relevant).
"""


def narrate(assessment) -> str:
    client = build_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=NARRATE_SYSTEM,
        messages=[{"role": "user", "content": to_json(assessment)}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def ask(assessment, question: str) -> str:
    client = build_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=CHAT_SYSTEM,
        messages=[
            {"role": "user", "content": f"Assessment:\n{to_json(assessment)}\n\nQuestion: {question}"},
        ],
    )
    return next((b.text for b in response.content if b.type == "text"), "")
