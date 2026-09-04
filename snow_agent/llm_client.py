"""Builds the Azure OpenAI client used for narration/chat.

This runs on the same "put credentials in later" model as the rest of the
agent -- nothing here works until you set these environment variables:

  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_ENDPOINT      e.g. https://your-resource.openai.azure.com/
  - AZURE_OPENAI_DEPLOYMENT    the deployment name you gave the model in
                                Azure AI Foundry (not the underlying model
                                name -- e.g. "gpt-4o", not "gpt-4o-2024-...")
  - AZURE_OPENAI_API_VERSION   optional, defaults to a recent stable version

Credentials are never read from anywhere but the environment.
"""

from __future__ import annotations

import os

from openai import AzureOpenAI

_REQUIRED = ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
_DEFAULT_API_VERSION = "2024-10-21"


class NoCredentialsConfigured(RuntimeError):
    pass


def build_client() -> AzureOpenAI:
    """Raises NoCredentialsConfigured immediately if nothing is set, instead
    of letting the SDK defer that failure to the first request."""
    missing = [var for var in _REQUIRED if not os.environ.get(var)]
    if missing:
        raise NoCredentialsConfigured(
            "set " + ", ".join(missing) + " as environment variables "
            "(Azure OpenAI: API key, endpoint, and the deployment name you "
            "gave the model in Azure AI Foundry)"
        )
    return AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", _DEFAULT_API_VERSION),
    )


def deployment_name() -> str:
    """The Azure deployment name, used as the `model` argument on chat
    completions. Separate from build_client() so callers can construct the
    client and resolve the deployment in one NoCredentialsConfigured-guarded
    step, without a second, uncaught KeyError further down."""
    return os.environ["AZURE_OPENAI_DEPLOYMENT"]
