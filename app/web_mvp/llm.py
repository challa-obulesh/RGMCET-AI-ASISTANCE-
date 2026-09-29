"""Hosted LLM provider boundary. API keys remain server-side."""

from __future__ import annotations

import logging
from typing import Literal
from urllib.parse import quote

import httpx

from app.web_mvp import config

logger = logging.getLogger(__name__)
Provider = Literal["gemini", "openai"]


def _providers() -> list[Provider]:
    preferred = config.LLM_PROVIDER if config.LLM_PROVIDER in {"gemini", "openai"} else "gemini"
    credentials = {
        "gemini": bool(config.GEMINI_API_KEY),
        "openai": bool(config.OPENAI_API_KEY or config.LEGACY_LLM_API_KEY),
    }
    order = [preferred, "openai" if preferred == "gemini" else "gemini"]
    return [provider for provider in order if credentials[provider]]


def configured_provider() -> str | None:
    providers = _providers()
    return providers[0] if providers else None


def _openai_credentials() -> tuple[str, str, str]:
    key = config.OPENAI_API_KEY or config.LEGACY_LLM_API_KEY
    model = config.OPENAI_MODEL if config.OPENAI_API_KEY else config.LEGACY_LLM_MODEL
    url = config.LEGACY_LLM_BASE_URL
    return key, model, url


async def _call_openai(system_prompt: str, user_prompt: str, json_mode: bool, timeout: float) -> str:
    key, model, url = _openai_credentials()
    headers = {"Authorization": f"Bearer {key}"}
    payload: dict = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


async def _call_gemini(system_prompt: str, user_prompt: str, json_mode: bool, timeout: float) -> str:
    model = quote(config.GEMINI_MODEL, safe="-")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload: dict = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            json=payload,
        )
        response.raise_for_status()
    parts = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


async def complete(
    system_prompt: str,
    user_prompt: str,
    *,
    json_mode: bool = False,
    timeout: float = 12,
) -> str | None:
    """Try configured hosted providers in preference order; never raise on outage."""
    for provider in _providers():
        try:
            if provider == "gemini":
                result = await _call_gemini(system_prompt, user_prompt, json_mode, timeout)
            else:
                result = await _call_openai(system_prompt, user_prompt, json_mode, timeout)
            if result:
                return result
            logger.warning("LLM provider %s returned an empty response", provider)
        except Exception as exc:
            logger.warning("LLM provider %s failed (%s)", provider, type(exc).__name__)
    return None