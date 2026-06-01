package com.contactflow.ticket.integration;

// 展示说明：RabbitMQ AI Assist 完成事件监听器，完成 V0.2 ai.assist.completed 回写、Redis 幂等标记和落库审计。

import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.service.TicketService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(prefix = "contactflow.events.rabbit", name = "enabled", havingValue = "true")
// 条件化监听组件：仅在 RabbitMQ 开启时消费完成队列，本地测试可自动回退为无 MQ 模式。
public class AiAssistCompletedListener {
    private static final Duration AI_EVENT_TTL = Duration.ofHours(6);

    private final TicketService ticketService;
    private final TicketCacheService cacheService;
    private final ObjectMapper objectMapper;

    public AiAssistCompletedListener(TicketService ticketService, TicketCacheService cacheService, ObjectMapper objectMapper) {
        this.ticketService = ticketService;
        this.cacheService = cacheService;
        this.objectMapper = objectMapper;
    }

    @RabbitListener(queues = "${contactflow.events.rabbit.ai-assist-completed-queue}")
    // 完成事件处理：解析 envelope、按 sourceEventId 去重、调用 TicketService 幂等保存 AI Assist。
    public void handle(Map<String, Object> envelope) {
        Map<String, Object> payload = payload(envelope);
        String sourceEventId = required(payload, "sourceEventId");
        String idempotencyKey = "ai_event:" + sourceEventId;
        if (cacheService.get(idempotencyKey).isPresent()) {
            return;
        }

        ticketService.attachAiAssist(
                UUID.fromString(required(payload, "ticketId")),
                sourceEventId,
                required(payload, "intent"),
                required(payload, "summary"),
                required(payload, "suggestedReply"),
                bool(payload.get("handoffRecommended")),
                optionalString(payload.get("handoffReason")),
                SlaRisk.valueOf(required(payload, "slaRisk")),
                decimal(payload.get("confidence")).doubleValue(),
                citationsJson(payload.get("citations")),
                decimal(payload.get("latencyMs")).intValue(),
                decimal(payload.get("estimatedCostUsd"))
        );
        cacheService.put(idempotencyKey, "processed", AI_EVENT_TTL);
    }

    @SuppressWarnings("unchecked")
    // 兼容 envelope 与裸 payload 两种消息格式，便于本地脚本和真实 MQ 同时复用。
    private Map<String, Object> payload(Map<String, Object> envelope) {
        Object nested = envelope.get("payload");
        if (nested instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return envelope;
    }

    // 必填字段校验：缺失关键 AI Assist 字段时主动失败，交给 MQ 重试/死信链路处理。
    private static String required(Map<String, Object> payload, String field) {
        Object value = payload.get(field);
        if (value == null || value.toString().isBlank()) {
            throw new IllegalArgumentException("Missing required AI assist field: " + field);
        }
        return value.toString();
    }

    // 可选字符串转换：handoffReason 等字段为空时保持 null 语义。
    private static String optionalString(Object value) {
        return value == null ? null : value.toString();
    }

    // 布尔字段转换：兼容 JSON boolean 与字符串形式的布尔值。
    private static boolean bool(Object value) {
        return Boolean.parseBoolean(String.valueOf(value));
    }

    // 数值字段转换：统一处理 confidence、latencyMs、estimatedCostUsd 等数值。
    private static BigDecimal decimal(Object value) {
        if (value == null) {
            return BigDecimal.ZERO;
        }
        if (value instanceof Number number) {
            return BigDecimal.valueOf(number.doubleValue());
        }
        return new BigDecimal(value.toString());
    }

    // 引用证据序列化：将 citations 统一保存为 JSON 字符串，便于数据库落库和前端展示。
    private String citationsJson(Object value) {
        if (value == null) {
            return "[]";
        }
        try {
            if (value instanceof String text) {
                return text;
            }
            if (value instanceof List<?> || value instanceof Map<?, ?>) {
                return objectMapper.writeValueAsString(value);
            }
            return objectMapper.writeValueAsString(List.of(value));
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Invalid citations payload", exception);
        }
    }
}
