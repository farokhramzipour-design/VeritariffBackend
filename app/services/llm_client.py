import json
import logging
from typing import Any

import anyio

logger = logging.getLogger("uvicorn.error")

EXTRACT_PROMPT = """
You are an AI that extracts invoice data. Output strict JSON only.
Schema:
{
  "vendor_name": string|null,
  "invoice_number": string|null,
  "invoice_date": string|null,
  "due_date": string|null,
  "currency": string|null,
  "subtotal": number|null,
  "tax": number|null,
  "total": number|null,
  "line_items": [
    {
      "description": string,
      "quantity": number|null,
      "unit_price": number|null,
      "tax_rate": number|null,
      "line_total": number|null,
      "sku": string|null,
      "confidence": number|null
    }
  ],
  "field_confidence": {"field": number},
  "confidence_score": number,
  "warnings": [string]
}
Only output valid JSON.
"""

REPAIR_PROMPT = """
You are a JSON repair bot. Given malformed JSON, output a corrected JSON that matches the schema.
Only output JSON, no markdown.
"""


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider
        self.model = model
        self._client = None
        if self.provider == "openai":
            from openai import OpenAI

            self._client = OpenAI()

    def parse_json(self, raw: str) -> dict[str, Any] | None:
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def _openai_call(self, prompt: str, text: str) -> str | None:
        if not self._client or not self.model:
            return None

        def _call() -> str | None:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": text}],
                    },
                ],
                temperature=0,
            )
            if hasattr(response, "output_text"):
                return response.output_text
            return None

        return await anyio.to_thread.run_sync(_call)

    async def extract_json(self, prompt: str, text: str) -> dict[str, Any] | None:
        if not self.provider:
            return None
        if self.provider == "openai":
            raw = await self._openai_call(prompt, text)
            if not raw:
                return None
            parsed = self.parse_json(raw)
            if parsed is not None:
                return parsed
            repaired = await self._openai_call(REPAIR_PROMPT, raw)
            if not repaired:
                return None
            return self.parse_json(repaired)
        return None
