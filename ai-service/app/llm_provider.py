# 展示说明：LLM Provider 抽象层，支持 Qwen3-Max 主模型、备用模型和模板降级，保证工单主链路不依赖外部大模型可用性。
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
# LLM 生成结果：把真实模型输出和降级信息统一成稳定结构，方便后续落库、审计和前端展示。
class LlmGeneration:
    summary: str
    suggested_reply: str
    mode: str
    model_name: str | None
    degraded_reason: str | None
    estimated_cost_usd: float


@dataclass(frozen=True)
# LLM 环境配置：集中读取模型开关、DashScope/OpenAI-compatible 地址、密钥、超时和重试参数。
class LlmSettings:
    enabled: bool
    base_url: str
    api_key: str | None
    model: str
    fallback_model: str | None
    timeout_seconds: float
    max_retries: int

    # 环境变量装配：默认关闭真实模型调用，避免本地演示因为缺少 API Key 或网络失败而中断。
    @classmethod
    def from_env(cls) -> "LlmSettings":
        enabled = os.getenv("LLM_ENABLED", "false").lower() == "true"
        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
        return cls(
            enabled=enabled,
            base_url=os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/"),
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "qwen3-max"),
            fallback_model=os.getenv("LLM_FALLBACK_MODEL", "qwen-plus"),
            timeout_seconds=max(float(os.getenv("LLM_TIMEOUT_SECONDS", "8")), 0.5),
            max_retries=max(int(os.getenv("LLM_MAX_RETRIES", "1")), 0),
        )


# Qwen3-Max 接入层：先保证模板兜底可用，再按主模型、备用模型的顺序尝试真实生成。
class LlmProvider:
    # 初始化 Provider：允许测试注入固定配置，生产/本地运行时默认从环境变量读取。
    def __init__(self, settings: LlmSettings | None = None) -> None:
        self.settings = settings or LlmSettings.from_env()

    # 生成坐席辅助文本：成功时返回 llm 模式，失败时保留安全模板摘要和回复并记录 degraded_reason。
    def generate(
        self,
        *,
        ticket_title: str,
        customer_message: str,
        intent: str,
        route: str,
        sla_risk: str,
        template_summary: str,
        template_reply: str,
        citations: list[dict],
    ) -> LlmGeneration:
        if not self.settings.enabled:
            return self._template(template_summary, template_reply, "llm_disabled")
        if not self.settings.api_key:
            return self._template(template_summary, template_reply, "missing_api_key")

        prompt = self._prompt(
            ticket_title=ticket_title,
            customer_message=customer_message,
            intent=intent,
            route=route,
            sla_risk=sla_risk,
            template_summary=template_summary,
            citations=citations,
        )
        models = [self.settings.model]
        if self.settings.fallback_model and self.settings.fallback_model not in models:
            models.append(self.settings.fallback_model)

        last_error = "unknown_llm_error"
        for model in models:
            for _ in range(self.settings.max_retries + 1):
                try:
                    started = time.perf_counter()
                    payload = self._chat_completion(model, prompt)
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    parsed = self._parse_generation(payload)
                    return LlmGeneration(
                        summary=parsed.get("summary") or template_summary,
                        suggested_reply=parsed.get("suggested_reply") or template_reply,
                        mode="llm",
                        model_name=model,
                        degraded_reason=None,
                        estimated_cost_usd=self._estimate_cost(model, latency_ms),
                    )
                except (TimeoutError, socket.timeout):
                    last_error = "llm_timeout"
                except (urllib.error.URLError, urllib.error.HTTPError) as exception:
                    last_error = f"llm_http_error:{getattr(exception, 'code', 'network')}"
                except (ValueError, KeyError, json.JSONDecodeError):
                    last_error = "llm_invalid_response"

        return self._template(template_summary, template_reply, last_error)

    # OpenAI-compatible Chat Completions 调用：当前面向 DashScope 兼容模式，便于切换 Qwen3-Max/qwen-plus。
    def _chat_completion(self, model: str, prompt: str) -> dict:
        request = urllib.request.Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(
                {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是企业客服坐席辅助系统，只能基于证据给出坐席建议。"
                                "不要承诺退款、赔偿或法律结论。请返回 JSON。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    # 提示词构造：把工单、意图、路由、SLA 和证据压缩成结构化 JSON 输出任务，禁止模型脱离证据承诺。
    def _prompt(
        *,
        ticket_title: str,
        customer_message: str,
        intent: str,
        route: str,
        sla_risk: str,
        template_summary: str,
        citations: list[dict],
    ) -> str:
        evidence = json.dumps(citations[:5], ensure_ascii=False)
        return (
            "请为客服坐席生成结构化辅助结果。\n"
            f"工单标题：{ticket_title}\n"
            f"客户消息：{customer_message}\n"
            f"意图：{intent}\n"
            f"路由：{route}\n"
            f"SLA风险：{sla_risk}\n"
            f"模板摘要：{template_summary}\n"
            f"可引用证据：{evidence}\n"
            '只返回 JSON：{"summary":"...","suggested_reply":"..."}'
        )

    @staticmethod
    # 模型输出解析：兼容字符串 JSON 和结构化对象两种返回形态，异常交给上层降级处理。
    def _parse_generation(payload: dict) -> dict[str, str]:
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, dict):
            return {"summary": str(content.get("summary", "")), "suggested_reply": str(content.get("suggested_reply", ""))}
        parsed = json.loads(content)
        return {
            "summary": str(parsed.get("summary", "")),
            "suggested_reply": str(parsed.get("suggested_reply", "")),
        }

    @staticmethod
    # 成本估算：用于演示运营字段，不作为真实账单；真实生产可替换成 token usage 计费。
    def _estimate_cost(model: str, latency_ms: int) -> float:
        base = 0.0006 if "max" in model else 0.0002
        return round(base + min(latency_ms, 10000) / 1000 * 0.00001, 6)

    @staticmethod
    # 模板兜底：外部模型未启用、无密钥、超时、限流或返回异常时统一返回可展示的安全结果。
    def _template(summary: str, reply: str, reason: str) -> LlmGeneration:
        return LlmGeneration(
            summary=summary,
            suggested_reply=reply,
            mode="template_fallback",
            model_name=None,
            degraded_reason=reason,
            estimated_cost_usd=0.0,
        )
