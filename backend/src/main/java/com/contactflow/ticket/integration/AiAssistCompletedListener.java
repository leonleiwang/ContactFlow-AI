package com.contactflow.ticket.integration;

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
    private Map<String, Object> payload(Map<String, Object> envelope) {
        Object nested = envelope.get("payload");
        if (nested instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return envelope;
    }

    private static String required(Map<String, Object> payload, String field) {
        Object value = payload.get(field);
        if (value == null || value.toString().isBlank()) {
            throw new IllegalArgumentException("Missing required AI assist field: " + field);
        }
        return value.toString();
    }

    private static String optionalString(Object value) {
        return value == null ? null : value.toString();
    }

    private static boolean bool(Object value) {
        return Boolean.parseBoolean(String.valueOf(value));
    }

    private static BigDecimal decimal(Object value) {
        if (value == null) {
            return BigDecimal.ZERO;
        }
        if (value instanceof Number number) {
            return BigDecimal.valueOf(number.doubleValue());
        }
        return new BigDecimal(value.toString());
    }

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
