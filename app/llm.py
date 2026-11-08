import json

import httpx

from app.config import settings


class LLMError(Exception):
    """Raised when the language model cannot return a usable JSON draft."""


async def complete_json(system_prompt: str, user_prompt: str) -> dict:
    if not settings.llm_api_key or settings.llm_api_key == "replace-me":
        raise LLMError("Не задан LLM_API_KEY. Скопируйте .env.example в .env и укажите ключ.")

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        raise LLMError("Модель не ответила за отведённое время.") from exc
    except httpx.HTTPError as exc:
        raise LLMError("Не удалось связаться с LLM API.") from exc

    if response.status_code == 401:
        raise LLMError("LLM API отклонил ключ (401). Проверьте LLM_API_KEY.")
    if response.status_code == 429:
        raise LLMError("LLM API: слишком много запросов (429). Повторите позже.")
    if response.status_code >= 400:
        raise LLMError(f"LLM API вернул ошибку {response.status_code}.")

    try:
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise LLMError("Модель вернула ответ, который нельзя разобрать как JSON.") from exc
