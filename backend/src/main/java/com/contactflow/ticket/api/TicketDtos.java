package com.contactflow.ticket.api;

import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketAiAssist;
import com.contactflow.ticket.domain.TicketPriority;
import com.contactflow.ticket.domain.TicketStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public final class TicketDtos {
    private TicketDtos() {
    }

    public record CreateTicketRequest(
            @NotBlank String tenantId,
            @NotBlank String title,
            @NotBlank String customerName,
            @NotBlank String customerMessage,
            @NotNull TicketPriority priority
    ) {
    }

    public record ClaimTicketRequest(@NotBlank String tenantId, @NotBlank String agentId) {
    }

    public record TransitionRequest(@NotBlank String tenantId, @NotBlank String actorId, @NotNull TicketStatus targetStatus, String reason) {
    }

    public record AiAssistRequest(
            @NotNull UUID ticketId,
            @NotBlank String sourceEventId,
            @NotBlank String intent,
            @NotBlank String summary,
            @NotBlank String suggestedReply,
            boolean handoffRecommended,
            String handoffReason,
            @NotNull SlaRisk slaRisk,
            double confidence,
            String citationsJson,
            int latencyMs,
            @NotNull BigDecimal estimatedCostUsd
    ) {
    }

    public record TicketResponse(
            UUID id,
            String tenantId,
            String title,
            String customerName,
            String customerMessage,
            TicketStatus status,
            TicketPriority priority,
            String assignedAgentId,
            Instant slaDueAt,
            Instant claimedAt,
            long version
    ) {
        public static TicketResponse from(SupportTicket ticket) {
            return new TicketResponse(
                    ticket.getId(),
                    ticket.getTenantId(),
                    ticket.getTitle(),
                    ticket.getCustomerName(),
                    ticket.getCustomerMessage(),
                    ticket.getStatus(),
                    ticket.getPriority(),
                    ticket.getAssignedAgentId(),
                    ticket.getSlaDueAt(),
                    ticket.getClaimedAt(),
                    ticket.getVersion()
            );
        }
    }

    public record AiAssistResponse(UUID id, UUID ticketId, String sourceEventId) {
        public static AiAssistResponse from(TicketAiAssist assist) {
            return new AiAssistResponse(assist.getId(), assist.getTicketId(), assist.getSourceEventId());
        }
    }
}
