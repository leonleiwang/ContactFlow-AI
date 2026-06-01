package com.contactflow.ticket.domain;

// 展示说明：工单审计事件实体，记录创建、抢单、状态流转和 AI Assist 挂载等关键生命周期动作。

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
// 审计事件表：以 append-only 方式保留工单状态变化和操作原因，便于追踪与质检。
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
        // 创建审计事件：记录操作者、前后状态、原因和发生时间。
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
