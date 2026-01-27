from __future__ import annotations
from typing import Dict, Any

from llm_gate.ollama_gate import health_check as _health, generate as _generate


class OllamaProvider:
    name = "ollama"

    def health(self) -> Dict[str, Any]:
        return _health()

    def generate(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        return _generate(prompt, system_prompt=system_prompt)
