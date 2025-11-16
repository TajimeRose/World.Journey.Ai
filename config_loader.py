"""Backward-compatible helpers for legacy modules that expect dict configs."""

from __future__ import annotations

from typing import Any, Dict, Optional

from world_journey_ai.configs import PromptRepo

_PROMPT_REPO = PromptRepo()


def get_prompts_config() -> Dict[str, Any]:
    """Return prompts in the legacy dictionary shape."""
    system_prompts = _PROMPT_REPO.get_prompt("chatbot/system", default={})
    answer_prompts = _PROMPT_REPO.get_prompt("chatbot/answer", default={})
    search_prompts = _PROMPT_REPO.get_prompt("chatbot/search", default={})
    return {
        "chatbot": answer_prompts,
        "chatbot_system": system_prompts,
        "chatbot_search": search_prompts,
        "gpt_service": {
            "system_prompt": system_prompts,
            "fallback_messages": answer_prompts.get("fallback", {}),
        },
    }


def get_parameters_config() -> Dict[str, Any]:
    """Return parameters dict similar to previous structure."""
    params = _PROMPT_REPO.get_model_params()
    chatbot_settings = _PROMPT_REPO.get_chatbot_settings()
    return {
        "gpt_service": {
            "model": params.get("default_model"),
            "temperature": params.get("chat", {}).get("temperature"),
            "max_completion_tokens": params.get("chat", {}).get("max_completion_tokens"),
            "presence_penalty": params.get("chat", {}).get("presence_penalty"),
            "frequency_penalty": params.get("chat", {}).get("frequency_penalty"),
            "greeting": params.get("greeting", {}),
        },
        "chatbot": {
            "default_province": chatbot_settings.get("default_province", "สมุทรสงคราม"),
        },
    }


def get_config_value(config: Dict[str, Any], *keys: str, default: Optional[Any] = None) -> Any:
    node: Any = config
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
    return node if node is not None else default
