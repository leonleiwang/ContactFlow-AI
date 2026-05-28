package com.contactflow.ticket.integration;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.service.TicketService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class AiAssistCompletedListenerTest {
    private final TicketService ticketService = org.mockito.Mockito.mock(TicketService.class);
    private final TicketCacheService cacheService = org.mockito.Mockito.mock(TicketCacheService.class);
    private final AiAssistCompletedListener listener = new AiAssistCompletedListener(ticketService, cacheService, new ObjectMapper());

    @Test
    void attachesAiAssistAndMarksEventAsProcessed() {
        UUID ticketId = UUID.randomUUID();
        when(cacheService.get("ai_event:event-1")).thenReturn(Optional.empty());

        listener.handle(Map.of("eventType", "ai.assist.completed", "payload", completedPayload(ticketId)));

        verify(ticketService).attachAiAssist(
                eq(ticketId),
                eq("event-1"),
                eq("refund"),
                eq("Customer asks refund"),
                eq("Ask for order id"),
                eq(false),
                eq(null),
                eq(SlaRisk.LOW),
                eq(0.91),
                anyString(),
                eq(32),
                eq(new BigDecimal("0.0002"))
        );
        verify(cacheService).put(eq("ai_event:event-1"), eq("processed"), any(Duration.class));
    }

    @Test
    void skipsEventAlreadyMarkedAsProcessedInRedis() {
        when(cacheService.get("ai_event:event-1")).thenReturn(Optional.of("processed"));

        listener.handle(Map.of("payload", completedPayload(UUID.randomUUID())));

        verify(ticketService, never()).attachAiAssist(
                any(UUID.class),
                anyString(),
                anyString(),
                anyString(),
                anyString(),
                anyBoolean(),
                any(),
                any(SlaRisk.class),
                anyDouble(),
                anyString(),
                anyInt(),
                any(BigDecimal.class)
        );
    }

    private Map<String, Object> completedPayload(UUID ticketId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ticketId", ticketId.toString());
        payload.put("sourceEventId", "event-1");
        payload.put("intent", "refund");
        payload.put("summary", "Customer asks refund");
        payload.put("suggestedReply", "Ask for order id");
        payload.put("handoffRecommended", false);
        payload.put("slaRisk", "LOW");
        payload.put("confidence", 0.91);
        payload.put("citations", List.of(Map.of("docId", "tenant-a/refund_policy.md")));
        payload.put("latencyMs", 32);
        payload.put("estimatedCostUsd", "0.0002");
        return payload;
    }
}
