import json
import random
import re
import time
from typing import Any

from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from src.config import get_settings


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()

        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url

        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries

    def text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        last_error: Exception | None = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "timeout": self.timeout,
                }

                if self.api_key:
                    kwargs["api_key"] = self.api_key

                if self.base_url:
                    kwargs["api_base"] = self.base_url

                response = completion(**kwargs)

                content = (
                    response.choices[0]
                    .message
                    .content
                )

                if not content:
                    raise ValueError(
                        "LLM returned an empty response."
                    )

                return content.strip()

            except (
                RateLimitError,
                ServiceUnavailableError,
                APIConnectionError,
                Timeout,
                APIError,
            ) as exc:
                last_error = exc

                if attempt == self.max_retries:
                    break

                wait_seconds = min(
                    30.0,
                    (2 ** attempt)
                    + random.uniform(0, 1),
                )

                print(
                    f"LLM request failed: "
                    f"{type(exc).__name__}. "
                    f"Retry after "
                    f"{wait_seconds:.1f}s "
                    f"({attempt}/"
                    f"{self.max_retries})"
                )

                time.sleep(wait_seconds)

        raise RuntimeError(
            "LLM request failed after retries."
        ) from last_error

    def json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        raw = self.text(
            system_prompt=(
                system_prompt
                + "\nReturn valid JSON only. "
                + "Do not use Markdown code fences."
            ),
            user_prompt=user_prompt,
        )

        try:
            return json.loads(raw)

        except json.JSONDecodeError:
            match = re.search(
                r"\{.*\}",
                raw,
                flags=re.DOTALL,
            )

            if not match:
                raise ValueError(
                    "The model did not return valid JSON. "
                    f"Raw output: {raw}"
                )

            return json.loads(
                match.group(0)
            )