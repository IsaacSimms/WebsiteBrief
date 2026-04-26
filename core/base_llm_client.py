# == base_llm_client.py == #
# Abstract base class for all AI/LLM provider clients.
#
# ADDING A NEW AI PROVIDER — checklist:
#   1. Create core/<name>_client.py
#   2. Subclass BaseLLMClient
#   3. Implement generate_brief(prompt) → str
#   4. Add a providers block in config.yaml under llm.providers.<name>
#   5. Add one elif branch in run.py's _build_llm_client()
#   That is all. The scraper and storage layers never need to change.

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    # == BaseLLMClient == #
    # Every LLM client must inherit this and implement generate_brief().
    # The rest of the pipeline only calls generate_brief(), so any provider
    # can be swapped in without changing run.py, storage, or the scrapers.

    def __init__(self, config: dict) -> None:
        # config is the dict from config.yaml under llm.providers.<name>
        # e.g. config["llm"]["providers"]["claude"]
        self.config = config

    @abstractmethod
    def generate_brief(self, prompt: str) -> str:
        # Send prompt to the AI and return the response as a Markdown string.
        # Raise LLMError on any non-recoverable API failure.
        ...


class LLMError(Exception):
    # == LLMError == #
    # Raised on any non-recoverable LLM API failure:
    # bad API key, rate limit, network error, empty response, etc.
    # run.py catches this and exits with code 1.
    pass
