package com.contactflow.ticket.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "ticket_ai_assists", uniqueConstraints = @UniqueConstraint(name = "uk_ai_assist_event", columnNames = {"ticket_id", "source_event_id"}))
public class TicketAiAssist {
    @Id
    @JdbcTypeCode(SqlTypes.BINARY)
    @Column(columnDefinition = "binary(16)")
    private UUID id;

    @JdbcTypeCode(SqlTypes.BINARY)
    @Column(name = "ticket_id", nullable = false, columnDefinition = "binary(16)")
    private UUID ticketId;

    @Column(name = "source_event_id", nullable = false, length = 80)
    private String sourceEventId;

    @Column(nullable = false, length = 80)
    private String intent;

    @Column(nullable = false, length = 500)
    private String summary;

    @Column(nullable = false, columnDefinition = "text")
    private String suggestedReply;

    @Column(nullable = false)
    private boolean handoffRecommended;

    @Column(length = 255)
    private String handoffReason;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private SlaRisk slaRisk;

    @Column(nullable = false, precision = 5, scale = 4)
    private BigDecimal confidence;

    @Column(columnDefinition = "text")
    private String citationsJson;

    @Column(nullable = false)
    private int latencyMs;

    @Column(nullable = false, precision = 10, scale = 6)
    private BigDecimal estimatedCostUsd;

    @Column(nullable = false)
    private Instant createdAt;

    protected TicketAiAssist() {
    }

    public TicketAiAssist(UUID ticketId, String sourceEventId, String intent, String summary, String suggestedReply, boolean handoffRecommended, String handoffReason, SlaRisk slaRisk, BigDecimal confidence, String citationsJson, int latencyMs, BigDecimal estimatedCostUsd) {
        this.id = UUID.randomUUID();
        this.ticketId = ticketId;
        this.sourceEventId = sourceEventId;
        this.intent = intent;
        this.summary = summary;
        this.suggestedReply = suggestedReply;
        this.handoffRecommended = handoffRecommended;
        this.handoffReason = handoffReason;
        this.slaRisk = slaRisk;
        this.confidence = confidence;
        this.citationsJson = citationsJson;
        this.latencyMs = latencyMs;
        this.estimatedCostUsd = estimatedCostUsd;
        this.createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public UUID getTicketId() {
        return ticketId;
    }

    public String getSourceEventId() {
        return sourceEventId;
    }
}
