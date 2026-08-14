import json
import random
import re
import time
from typing import Any

from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from src.backend.config import get_settings


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()

        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.api_key_backup = settings.llm_api_key_backup
        self.base_url = settings.llm_base_url
        fallbacks = [
            item.strip()
            for item in (settings.llm_model_fallbacks or "").split(",")
            if item.strip()
        ]
        models: list[str] = []
        for item in [self.model, *fallbacks]:
            if item and item not in models:
                models.append(item)
        self.models = models or [self.model]

        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout
        # At least 3 attempts helps absorb short Gemini RPM spikes.
        self.max_retries = max(3, int(settings.llm_max_retries or 2))

    def text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        last_error: Exception | None = None

        api_keys = [
            key
            for key in [
                self.api_key,
                self.api_key_backup,
            ]
            if key
        ]

        if not api_keys:
            raise RuntimeError(
                "No LLM API key configured."
            )

        for model_index, model in enumerate(self.models, start=1):
            if model_index > 1:
                print(f"Switching Gemini model to {model}...")
            for key_index, api_key in enumerate(api_keys, start=1):
                if key_index > 1:
                    print("Switching to backup Gemini API key...")
                for attempt in range(1, self.max_retries + 1):
                    try:
                        kwargs: dict[str, Any] = {
                            "model": model,
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
                            "api_key": api_key,
                        }

                        if self.base_url:
                            kwargs["api_base"] = self.base_url

                        response = completion(**kwargs)
                        content = response.choices[0].message.content
                        if not content or not str(content).strip():
                            raise ValueError("LLM returned an empty response.")
                        return str(content).strip()

                    except AuthenticationError as exc:
                        last_error = exc
                        print(
                            f"Gemini {model} key {key_index} failed: "
                            f"AuthenticationError ({attempt}/{self.max_retries})"
                        )
                        break

                    except (
                        RateLimitError,
                        ServiceUnavailableError,
                        APIConnectionError,
                        Timeout,
                        APIError,
                        ValueError,
                    ) as exc:
                        last_error = exc
                        print(
                            f"Gemini {model} key {key_index} failed: "
                            f"{type(exc).__name__} ({attempt}/{self.max_retries})"
                        )
                        if attempt == self.max_retries:
                            break
                        if isinstance(exc, RateLimitError):
                            wait_seconds = min(
                                20.0,
                                (3 ** attempt) + random.uniform(0, 1),
                            )
                        else:
                            wait_seconds = min(
                                8.0,
                                (2 ** attempt) + random.uniform(0, 1),
                            )
                        time.sleep(wait_seconds)

        if isinstance(last_error, RateLimitError):
            raise RuntimeError(
                "Gemini rate limit exceeded. Please wait a moment and try again."
            ) from last_error
        if isinstance(last_error, AuthenticationError):
            raise RuntimeError(
                "Gemini API key is invalid or unauthorized."
            ) from last_error

        raise RuntimeError("All Gemini API keys failed.") from last_error

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
