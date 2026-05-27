package com.contactflow.ticket.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "ticket_events")
public class TicketEvent {
    @Id
    @JdbcTypeCode(SqlTypes.BINARY)
    @Column(columnDefinition = "binary(16)")
    private UUID id;

    @JdbcTypeCode(SqlTypes.BINARY)
    @Column(nullable = false, columnDefinition = "binary(16)")
    private UUID ticketId;

    @Column(nullable = false, length = 64)
    private String tenantId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 64)
    private TicketEventType eventType;

    @Column(nullable = false, length = 64)
    private String actorId;

    @Enumerated(EnumType.STRING)
    @Column(length = 32)
    private TicketStatus fromStatus;

    @Enumerated(EnumType.STRING)
    @Column(length = 32)
    private TicketStatus toStatus;

    @Column(length = 255)
    private String reason;

    @Column(nullable = false)
    private Instant createdAt;

    protected TicketEvent() {
    }

    public TicketEvent(UUID ticketId, String tenantId, TicketEventType eventType, String actorId, TicketStatus fromStatus, TicketStatus toStatus, String reason) {
        this.id = UUID.randomUUID();
        this.ticketId = ticketId;
        this.tenantId = tenantId;
        this.eventType = eventType;
        this.actorId = actorId;
        this.fromStatus = fromStatus;
        this.toStatus = toStatus;
        this.reason = reason;
        this.createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public UUID getTicketId() {
        return ticketId;
    }

    public TicketEventType getEventType() {
        return eventType;
    }

    public TicketStatus getFromStatus() {
        return fromStatus;
    }

    public TicketStatus getToStatus() {
        return toStatus;
    }

    public String getReason() {
        return reason;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
