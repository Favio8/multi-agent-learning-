"""
LLM helper utilities.

This module centralizes provider initialization, text generation and a few
structured-output helpers used by the concept and quiz agents.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local", override=True)


class LLMHelper:
    """Thin wrapper around OpenAI-compatible chat APIs."""

    DEFAULT_MODELS = {
        "openai": "gpt-3.5-turbo",
        "zhipu": "glm-4",
        "qwen": "qwen-turbo",
        "deepseek": "deepseek-chat",
        "local": "local-model",
    }

    DEFAULT_BASE_URLS = {
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/",
        "deepseek": "https://api.deepseek.com",
    }

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 35.0,
        max_retries: int = 1,
    ):
        self.provider = (provider or "openai").lower()
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY")
        self.model = model or self.DEFAULT_MODELS.get(self.provider, "gpt-3.5-turbo")
        self.base_url = base_url or self.DEFAULT_BASE_URLS.get(self.provider)
        self.timeout_seconds = max(5.0, float(timeout_seconds))
        self.max_retries = max(0, int(max_retries))
        self.logger = logging.getLogger("nlp.LLMHelper")
        self.client = None

        if self.api_key:
            self._init_client()
        else:
            self.logger.warning(
                "No API key found for %s, LLM features disabled", self.provider
            )

    def _init_client(self) -> None:
        """Initialize an OpenAI-compatible client."""
        try:
            from openai import OpenAI
        except ImportError:
            self.logger.error("OpenAI package not installed. Run: pip install openai")
            return

        try:
            if self.base_url:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout_seconds,
                    max_retries=self.max_retries,
                )
            else:
                self.client = OpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout_seconds,
                    max_retries=self.max_retries,
                )

            self.logger.info(
                "%s client initialized with model: %s (timeout=%ss, retries=%s)",
                self.provider.capitalize(),
                self.model,
                self.timeout_seconds,
                self.max_retries,
            )
        except Exception as exc:
            self.logger.error("Failed to initialize LLM client: %s", exc)

    def is_available(self) -> bool:
        """Return whether the underlying API client is ready."""
        return self.client is not None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """Generate free-form text from the configured LLM."""
        if not self.is_available():
            self.logger.warning("LLM not available, returning None")
            return None

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout_seconds,
            )
            content = response.choices[0].message.content or ""
            self.logger.info("LLM generated response, length: %s", len(content))
            return content
        except Exception as exc:
            self.logger.error("LLM generation failed: %s", exc)
            return None

    def extract_concepts(self, text: str) -> List[Dict[str, Any]]:
        """Extract concepts from a text block using structured JSON output."""
        if not self.is_available():
            return []

        system_prompt = (
            "你是知识抽取助手。请从输入文本中提取最重要的概念，并返回严格 JSON 数组。"
            "每个元素格式为"
            '{"term":"概念名","definition":"简洁定义","aliases":["别名1","别名2"]}。'
            "要求：只保留文本中真实出现或被清楚定义的概念；term 2-20 字；"
            "definition 8-120 字；最多输出 6 个概念；不要输出任何额外说明。"
        )
        prompt = f"请从下面文本中提取关键概念并给出定义：\n\n{text}"
        response = self.generate(prompt, system_prompt, temperature=0.2, max_tokens=1200)
        payload = self._parse_json_response(response)

        if not isinstance(payload, list):
            return []

        concepts: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip()
            definition = str(item.get("definition", "")).strip()
            aliases = item.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []
            aliases = [str(alias).strip() for alias in aliases if str(alias).strip()]

            if term and definition:
                concepts.append(
                    {
                        "term": term,
                        "definition": definition,
                        "aliases": aliases,
                    }
                )

        self.logger.info("Extracted %s concepts using LLM", len(concepts))
        return concepts

    def generate_quiz_card(
        self, concept: Dict[str, str], card_type: str = "cloze"
    ) -> Optional[Dict[str, Any]]:
        """Generate a single quiz card with structured JSON output."""
        if not self.is_available():
            return None

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        if not term or not definition:
            return None

        prompts = {
            "cloze": (
                "你是出题助手。根据给定概念生成 1 道填空题，返回 JSON 对象："
                '{"stem":"带 ____ 的题干","answer":"答案","explanation":"简短解释"}。'
            ),
            "mcq": (
                "你是出题助手。根据给定概念生成 1 道选择题，返回 JSON 对象："
                '{"stem":"题干","choices":["A","B","C","D"],'
                '"answer":"正确选项原文","explanation":"简短解释"}。'
                "choices 必须互不重复，answer 必须在 choices 中。"
            ),
            "short": (
                "你是出题助手。根据给定概念生成 1 道简答题，返回 JSON 对象："
                '{"stem":"问题","answer":"参考答案","explanation":"评分要点"}。'
            ),
        }
        system_prompt = prompts.get(card_type)
        if not system_prompt:
            return None

        prompt = f"概念：{term}\n定义：{definition}\n\n请生成 1 道 {card_type} 卡片。"
        response = self.generate(prompt, system_prompt, temperature=0.5, max_tokens=700)
        payload = self._parse_json_response(response)

        if not isinstance(payload, dict):
            return None

        payload["type"] = card_type
        self.logger.info("Generated %s card using LLM", card_type)
        return payload

    def improve_text(self, text: str, task: str = "summarize") -> Optional[str]:
        """Use the LLM for simple rewrite/summarize tasks."""
        if not self.is_available():
            return None

        tasks = {
            "summarize": "请总结以下内容的重点：",
            "clarify": "请用更清晰的语言改写以下内容：",
            "simplify": "请用更易懂的方式解释以下内容：",
        }
        prompt = f"{tasks.get(task, tasks['summarize'])}\n\n{text}"
        return self.generate(prompt, temperature=0.4, max_tokens=1000)

    def _parse_json_response(self, response: Optional[str]) -> Optional[Any]:
        """Extract the first valid JSON object or array from a model response."""
        if not response:
            return None

        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        candidate = self._extract_first_json_block(text)
        if not candidate:
            self.logger.error("Failed to locate JSON block in LLM response")
            return None

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse LLM JSON response: %s", exc)
            return None

    def _extract_first_json_block(self, text: str) -> Optional[str]:
        """Return the first syntactically balanced JSON object or array."""
        for open_char, close_char in [("[", "]"), ("{", "}")]:
            start = text.find(open_char)
            while start != -1:
                depth = 0
                in_string = False
                escape = False
                for index in range(start, len(text)):
                    char = text[index]
                    if in_string:
                        if escape:
                            escape = False
                        elif char == "\\":
                            escape = True
                        elif char == '"':
                            in_string = False
                        continue

                    if char == '"':
                        in_string = True
                    elif char == open_char:
                        depth += 1
                    elif char == close_char:
                        depth -= 1
                        if depth == 0:
                            return text[start : index + 1]
                start = text.find(open_char, start + 1)
        return None


_llm_instance: Optional[LLMHelper] = None


def get_llm(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> LLMHelper:
    """Return the shared LLM helper instance."""
    global _llm_instance

    if _llm_instance is None:
        if provider is None:
            config_path = Path(__file__).resolve().parent.parent / "configs" / "settings.yaml"
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as file:
                    config = yaml.safe_load(file) or {}
                llm_config = config.get("models", {}).get("llm", {})

                if llm_config.get("enabled", False):
                    provider = llm_config.get("provider", "openai")
                    api_key = api_key or llm_config.get("api_key")
                    model = model or llm_config.get("model_name")
                    base_url = base_url or llm_config.get("base_url")
                    timeout_seconds = timeout_seconds or llm_config.get(
                        "request_timeout_seconds"
                    )
                    max_retries = (
                        max_retries
                        if max_retries is not None
                        else llm_config.get("max_retries")
                    )
            except Exception as exc:
                logging.getLogger("nlp.LLMHelper").warning(
                    "Failed to load LLM config: %s", exc
                )

        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        api_key = api_key or os.getenv("LLM_API_KEY")
        model = model or os.getenv("LLM_MODEL")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        timeout_seconds = timeout_seconds or os.getenv("LLM_TIMEOUT_SECONDS")
        max_retries = (
            max_retries
            if max_retries is not None
            else os.getenv("LLM_MAX_RETRIES")
        )

        _llm_instance = LLMHelper(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=float(timeout_seconds or 35),
            max_retries=int(max_retries or 1),
        )

    return _llm_instance
