import httpx
from typing import Any

from src.infra.settings import settings
from src.infra.exceptions import ConfigException


class LLMService:

    async def generate(
        self,
        prompt: str
    ) -> str:
        return await self._generate_gemini(prompt)

    async def _generate_gemini(
        self,
        prompt: str
    ) -> str:

        if not settings.gemini_api_key:
            raise ConfigException(
                "GEMINI_API_KEY não está configurada. Defina a variável de ambiente GEMINI_API_KEY."
            )

        headers = {
            "x-goog-api-key": settings.gemini_api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.gemini_model,
            "input": prompt
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.gemini_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return self._parse_gemini_response(response.json())

    def _parse_gemini_response(
        self,
        data: Any
    ) -> str:

        if isinstance(data, dict):
            steps = data.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if isinstance(step, dict) and step.get("type") == "model_output":
                        content = step.get("content")
                        if isinstance(content, list) and content:
                            first = content[0]
                            if isinstance(first, dict) and "text" in first:
                                return first["text"]

            candidates = data.get("candidates")
            if isinstance(candidates, list) and candidates:
                first = candidates[0]
                if isinstance(first, dict) and "output" in first:
                    return first["output"]

            if "output" in data:
                return data["output"]

        return str(data)
