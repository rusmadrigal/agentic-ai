import json
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


async def complete_json_model(
    *,
    system: str,
    user: str,
    model_type: type[T],
    temperature: float = 0.2,
) -> T:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("model returned non-json: %s", content[:500])
        raise RuntimeError("Model returned invalid JSON") from exc

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        logger.error("json failed validation: %s | errors=%s", content[:800], exc.errors())
        raise RuntimeError("Model JSON failed schema validation") from exc
