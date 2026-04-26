# == claude_client.py == #
# Anthropic Claude implementation of BaseLLMClient.
#
# Cost strategy:
#   - Default model: claude-haiku-4-5-20251001 — cheapest, fast, good for summaries.
#   - Prompt caching on the system prompt: after the first call within a 5-minute
#     window, Anthropic serves the system prompt from cache at ~1/10 the normal cost.
#   - One API call for ALL courses combined — not one per course.
#   - The 7-day filter in run.py trims the prompt before it gets here.
#
# Streaming: response chunks are printed live so you see the brief building up
# rather than waiting in silence for the full response.

from __future__ import annotations
import logging
import os

import anthropic

from core.base_llm_client import BaseLLMClient, LLMError

log = logging.getLogger(__name__)

# == SYSTEM_PROMPT == #
# Describes Claude's role and output format.
# Marked for caching (cache_control: ephemeral) — Anthropic caches it for 5 minutes.
# On the second call in a session the system prompt tokens cost ~10% of normal.
SYSTEM_PROMPT = """You are a concise academic assistant.

Your job is to read structured course data and produce a clear weekly brief in Markdown.

Output format:
1. A short summary paragraph (2-3 sentences max) at the very top.
2. One "## Course Name" section per course.
   - Bullet list of assignments due within the next 7 days, with due dates.
   - Use relative language: "due tomorrow", "due in 3 days", "due Sunday".
   - If a course has nothing due this week, say so in one sentence.
   - "### Announcements" sub-section if there are announcements for that course.
3. A "## This Week's Priorities" section at the end listing the 3 most urgent
   items across all courses, in order of urgency.

Rules:
- Be concise. No padding or filler phrases.
- Do not invent information that is not in the data provided.
- If an assignment has no due date listed, note it as "No due date".
"""


class ClaudeClient(BaseLLMClient):
    # == ClaudeClient == #
    # Calls the Anthropic API and streams the response to stdout.
    #
    # Required in .env:
    #   ANTHROPIC_API_KEY
    #
    # Optional in config.yaml under llm.providers.claude:
    #   model:      defaults to claude-haiku-4-5-20251001
    #   max_tokens: defaults to 2048

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY environment variable is not set.\n"
                "Add it to your .env file:  ANTHROPIC_API_KEY=sk-ant-..."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate_brief(self, prompt: str) -> str:
        # == generate_brief == #
        # Stream a response from Claude and return the full text when done.
        # Prints each chunk as it arrives so the user sees live output.

        model      = self.config.get("model", "claude-haiku-4-5-20251001")
        max_tokens = int(self.config.get("max_tokens", 2048))

        log.info("Calling %s (streaming, max_tokens=%d)...", model, max_tokens)

        try:
            with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        # cache_control tells Anthropic to cache this block.
                        # After the first call, subsequent calls within 5 minutes
                        # pay ~1/10 the normal input token cost for the system prompt.
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                # Print each text chunk as it arrives.
                for chunk in stream.text_stream:
                    print(chunk, end="", flush=True)
                final = stream.get_final_message()

            print()    # newline after streaming finishes

            u = final.usage
            log.info(
                "Tokens used — input: %d, output: %d, cache_write: %d, cache_read: %d",
                u.input_tokens,
                u.output_tokens,
                u.cache_creation_input_tokens,
                u.cache_read_input_tokens,
            )
            # cache_read_input_tokens > 0 means the system prompt was served from
            # cache — the second run in a session will show this.

            for block in final.content:
                if block.type == "text":
                    return block.text

            raise LLMError("Claude returned a response with no text content.")

        except anthropic.AuthenticationError:
            raise LLMError(
                "Anthropic API key is invalid. "
                "Check ANTHROPIC_API_KEY in your .env file."
            )
        except anthropic.RateLimitError as exc:
            raise LLMError(f"Anthropic rate limit hit — try again in a moment. ({exc})")
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic API error {exc.status_code}: {exc.message}")
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Could not connect to Anthropic API: {exc}")
