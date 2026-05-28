package com.contactflow.ticket.integration;

import com.contactflow.ticket.domain.TicketStatus;
import java.util.UUID;

public final class TicketCacheKeys {
    private TicketCacheKeys() {
    }

    public static String ticket(String tenantId, UUID ticketId) {
        return "ticket:%s:%s".formatted(tenantId, ticketId);
    }

    public static String queueCount(String tenantId, TicketStatus status) {
        return "ticket_count:%s:%s".formatted(tenantId, status.name());
    }

    public static String aiAssistSummary(UUID ticketId) {
        return "ai_assists:%s".formatted(ticketId);
    }

    public static String claimLock(UUID ticketId) {
        return "claim_lock:%s".formatted(ticketId);
    }
}
