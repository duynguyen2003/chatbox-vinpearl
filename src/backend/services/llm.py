import json
import random
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _ProviderConfig:
    label: str
    model: str
    api_key: str
    base_url: str | None


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()

        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.api_key_backup = settings.llm_api_key_backup
        self.base_url = settings.llm_base_url
        self.fallback_model = settings.llm_fallback_model
        self.fallback_api_key = settings.llm_fallback_api_key
        self.fallback_base_url = settings.llm_fallback_base_url

        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries

    def _provider_configs(self) -> list[_ProviderConfig]:
        """Return configured endpoints without ever logging credential values."""
        providers: list[_ProviderConfig] = []
        if self.api_key:
            providers.append(
                _ProviderConfig("primary", self.model, self.api_key, self.base_url)
            )
        if self.api_key_backup:
            providers.append(
                _ProviderConfig(
                    "primary backup key",
                    self.model,
                    self.api_key_backup,
                    self.base_url,
                )
            )

        fallback_api_key = getattr(self, "fallback_api_key", None)
        if fallback_api_key:
            providers.append(
                _ProviderConfig(
                    "fallback endpoint",
                    getattr(self, "fallback_model", None) or self.model,
                    fallback_api_key,
                    getattr(self, "fallback_base_url", None),
                )
            )
        return providers

    def text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> str:
        last_error: Exception | None = None

        providers = self._provider_configs()

        if not providers:
            raise RuntimeError("No LLM API key configured.")

        for provider_index, provider in enumerate(
            providers,
            start=1,
        ):
            for attempt in range(
                1,
                self.max_retries + 1,
            ):
                try:
                    kwargs: dict[str, Any] = {
                        "model": provider.model,
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
                        "temperature": (
                            self.temperature if temperature is None else float(temperature)
                        ),
                        "max_tokens": self.max_tokens,
                        "timeout": self.timeout,
                        "api_key": provider.api_key,
                    }

                    if provider.base_url:
                        kwargs["api_base"] = provider.base_url

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
                    AuthenticationError,
                    Timeout,
                    APIError,
                ) as exc:
                    last_error = exc

                    print(
                        f"LLM {provider.label} "
                        f"failed: "
                        f"{type(exc).__name__} "
                        f"({attempt}/"
                        f"{self.max_retries})"
                    )

                    if attempt == self.max_retries:
                        break

                    wait_seconds = min(
                        5.0,
                        (2 ** attempt)
                        + random.uniform(0, 1),
                    )

                    time.sleep(wait_seconds)

            if provider_index < len(providers):
                print(f"Switching to {providers[provider_index].label}...")

        raise RuntimeError("All configured LLM endpoints failed.") from last_error

    def stream_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> Iterator[str]:
        """Yield final response text without retrying after visible output.

        Retrying after the first emitted token would duplicate or splice two
        provider responses in the browser. Provider/key retries are therefore
        allowed only before any non-empty delta has been yielded.
        """
        last_error: Exception | None = None
        providers = self._provider_configs()

        if not providers:
            raise RuntimeError("No LLM API key configured.")

        for provider_index, provider in enumerate(providers, start=1):
            for attempt in range(1, self.max_retries + 1):
                emitted = False
                response = None
                try:
                    kwargs: dict[str, Any] = {
                        "model": provider.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": (
                            self.temperature
                            if temperature is None
                            else float(temperature)
                        ),
                        "max_tokens": self.max_tokens,
                        "timeout": self.timeout,
                        "api_key": provider.api_key,
                        "stream": True,
                    }
                    if provider.base_url:
                        kwargs["api_base"] = provider.base_url

                    response = completion(**kwargs)
                    for chunk in response:
                        choices = getattr(chunk, "choices", None) or []
                        if not choices:
                            continue
                        delta = getattr(choices[0], "delta", None)
                        content = getattr(delta, "content", None)
                        if not content and isinstance(delta, dict):
                            content = delta.get("content")
                        if not isinstance(content, str) or not content:
                            continue
                        emitted = True
                        yield content

                    if not emitted:
                        raise ValueError("LLM returned an empty streamed response.")
                    return

                except (
                    RateLimitError,
                    ServiceUnavailableError,
                    APIConnectionError,
                    AuthenticationError,
                    Timeout,
                    APIError,
                ) as exc:
                    last_error = exc
                    if emitted:
                        raise RuntimeError(
                            "LLM stream failed after output started."
                        ) from exc

                    print(
                        f"LLM {provider.label} streaming failed: "
                        f"{type(exc).__name__} ({attempt}/{self.max_retries})"
                    )
                    if attempt == self.max_retries:
                        break
                    wait_seconds = min(5.0, (2**attempt) + random.uniform(0, 1))
                    time.sleep(wait_seconds)
                finally:
                    close = getattr(response, "close", None)
                    if callable(close):
                        close()

            if provider_index < len(providers):
                print(f"Switching to {providers[provider_index].label} for streaming...")

        raise RuntimeError("All configured LLM endpoints failed.") from last_error

    def json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Run a structured control/judgement call deterministically by default.

        Free-form answer generation still uses ``self.temperature`` through
        :meth:`text`. JSON calls in this project are routing, intent, memory,
        sufficiency, triage, or grounding decisions; letting them inherit the
        creative answer temperature makes the agent graph non-deterministic.
        """
        raw = self.text(
            system_prompt=(
                system_prompt
                + "\nReturn valid JSON only. "
                + "Do not use Markdown code fences."
            ),
            user_prompt=user_prompt,
            temperature=temperature,
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
