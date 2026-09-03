"""Builds the Anthropic client for whichever environment this runs in.

Some environments (e.g. a locked-down company laptop) block the first-party
Anthropic API but allow Claude via Microsoft Foundry (Azure), billed through
the Azure Marketplace at standard API rates. AnthropicFoundry exposes the
same request surface (including client.beta.messages.tool_runner), so the
rest of the agent code needs no changes -- only which client gets built.

Credentials are never read from anywhere but the environment. Set one of:
  - ANTHROPIC_API_KEY                                  (first-party Anthropic)
  - ANTHROPIC_FOUNDRY_API_KEY + ANTHROPIC_FOUNDRY_RESOURCE
    (or ANTHROPIC_FOUNDRY_BASE_URL instead of _RESOURCE)  (Microsoft Foundry)
"""

from __future__ import annotations

import os

import anthropic

_FOUNDRY_ENV_VARS = (
    "ANTHROPIC_FOUNDRY_API_KEY",
    "ANTHROPIC_FOUNDRY_RESOURCE",
    "ANTHROPIC_FOUNDRY_BASE_URL",
)


class NoCredentialsConfigured(RuntimeError):
    pass


def build_client() -> anthropic.Anthropic:
    """Raises NoCredentialsConfigured immediately if nothing is set, instead
    of letting the SDK defer that failure to the first request."""
    if any(os.environ.get(var) for var in _FOUNDRY_ENV_VARS):
        return anthropic.AnthropicFoundry()
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return anthropic.Anthropic()
    raise NoCredentialsConfigured(
        "set either ANTHROPIC_API_KEY (first-party Anthropic) or "
        "ANTHROPIC_FOUNDRY_API_KEY + ANTHROPIC_FOUNDRY_RESOURCE "
        "(Microsoft Foundry / Azure) as environment variables"
    )
