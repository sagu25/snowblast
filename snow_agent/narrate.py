"""LLM narration and chat over an already-computed BlastRadiusAssessment.

Uses llm_client.py's Azure OpenAI client, so this runs on the same "put
credentials in later" model as the rest of the agent.

The model never re-runs the correlation or invents a number: both
functions below hand it the finished assessment as data and ask it to
either narrate or answer a question grounded in exactly that data.
"""

from __future__ import annotations

from snow_agent.llm_client import build_client, deployment_name
from snow_agent.report import to_json

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
    response = client.chat.completions.create(
        model=deployment_name(),
        max_tokens=512,
        messages=[
            {"role": "system", "content": NARRATE_SYSTEM},
            {"role": "user", "content": to_json(assessment)},
        ],
    )
    return response.choices[0].message.content or ""


def ask(assessment, question: str) -> str:
    client = build_client()
    response = client.chat.completions.create(
        model=deployment_name(),
        max_tokens=512,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM},
            {"role": "user", "content": f"Assessment:\n{to_json(assessment)}\n\nQuestion: {question}"},
        ],
    )
    return response.choices[0].message.content or ""
