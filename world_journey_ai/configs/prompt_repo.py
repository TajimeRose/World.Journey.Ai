from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


class PromptRepo:
    """Central repository for prompts, parameters, and feature settings."""

    def __init__(self, env: Optional[str] = None) -> None:
        self._root = Path(__file__).resolve().parent
        self.env = env or os.getenv("APP_ENV", "dev")
        self._env_overrides = self._load_json(f"env.{self.env}.json").get("overrides", {})
        self._model_config = self._merge_dicts(
            self._load_json("models.json"),
            self._env_overrides.get("models", {}),
        )
        self._feature_config = self._merge_dicts(
            self._load_json("features.json"),
            self._env_overrides.get("features", {}),
        )

    def get_prompt(self, key: str, *, default: Any = "") -> Any:
        """Retrieve prompt payload by namespace path e.g. chatbot/system."""
        parts = [p for p in key.strip("/").split("/") if p]
        if not parts:
            return default
        namespace, *rest = parts
        prompts = self._load_prompt_namespace(namespace)
        node: Any = prompts
        for part in rest:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                node = None
                break
        if node is None:
            return default
        return node

    def get_feature(self, *keys: str, default: Any = None) -> Any:
        node: Any = self._feature_config
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key)
        return node if node is not None else default

    def get_model_params(self) -> Dict[str, Any]:
        """Return OpenAI model configuration with overrides applied."""
        openai_cfg = self._model_config.get("openai", {}).copy()
        supported = openai_cfg.get("supported", [])
        default_model = openai_cfg.get("default_model")
        # Guarantee required models are listed
        required_models = {"gpt-4o-mini", "gpt-4o", "gpt-4o-reasoning"}
        merged_supported = list(dict.fromkeys(list(supported) + list(required_models)))
        openai_cfg["supported"] = merged_supported
        if default_model not in merged_supported:
            openai_cfg["default_model"] = "gpt-4o"
        return openai_cfg

    def get_chatbot_settings(self) -> Dict[str, Any]:
        return self._feature_config.get("chatbot", {})

    @lru_cache(maxsize=None)
    def _load_prompt_namespace(self, namespace: str) -> Dict[str, Any]:
        namespace_path = self._root / "prompts" / namespace
        prompts: Dict[str, Any] = {}
        if namespace_path.is_dir():
            for file in namespace_path.glob("*.json"):
                prompts[file.stem] = self._load_json(f"prompts/{namespace}/{file.name}")
        else:
            prompts = self._load_json(f"prompts/{namespace}.json")
        return prompts

    @lru_cache(maxsize=None)
    def _load_json(self, relative_path: str) -> Dict[str, Any]:
        path = self._root / relative_path
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            print(f"[WARN] Config file missing: {path}")
        except json.JSONDecodeError as exc:
            print(f"[WARN] Invalid JSON in {path}: {exc}")
        return {}

    @staticmethod
    def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        if not override:
            return dict(base)
        merged = dict(base)
        for key, value in override.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = PromptRepo._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged
