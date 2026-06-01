package com.contactflow.ticket.domain;

// 展示说明：工单聚合根实体，承载租户隔离、状态、优先级、SLA、抢单归属和状态机流转规则。

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "support_tickets")
// 支持工单实体：对应 Flyway support_tickets 表，是抢单、流转和审计链路的核心业务对象。
public class SupportTicket {
    @Id
    @JdbcTypeCode(SqlTypes.BINARY)
    @Column(columnDefinition = "binary(16)")
    private UUID id;

    @Column(nullable = false, length = 64)
    private String tenantId;

    @Column(nullable = false, length = 180)
    private String title;

    @Column(nullable = false, length = 120)
    private String customerName;

    @Column(nullable = false, columnDefinition = "text")
    private String customerMessage;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private TicketStatus status;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private TicketPriority priority;

    @Column(length = 64)
    private String assignedAgentId;

    @Column(length = 255)
    private String handoffReason;

    private Instant slaDueAt;
    private Instant claimedAt;

    @Column(nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    @Version
    @Column(nullable = false)
    private long version;

    protected SupportTicket() {
    }

    public SupportTicket(String tenantId, String title, String customerName, String customerMessage, TicketPriority priority, Instant slaDueAt) {
        // 新建工单默认进入 OPEN 状态，等待坐席领取或后续 AI Assist 异步分析。
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.title = title;
        this.customerName = customerName;
        this.customerMessage = customerMessage;
        this.status = TicketStatus.OPEN;
        this.priority = priority;
        this.slaDueAt = slaDueAt;
    }

    @PrePersist
    // 创建时间钩子：首次落库时自动填充 createdAt 和 updatedAt。
    void onCreate() {
        Instant now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    @PreUpdate
    // 更新时间钩子：每次更新工单状态或归属时刷新 updatedAt。
    void onUpdate() {
        updatedAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public String getTenantId() {
        return tenantId;
    }

    public String getTitle() {
        return title;
    }

    public String getCustomerName() {
        return customerName;
    }

    public String getCustomerMessage() {
        return customerMessage;
    }

    public TicketStatus getStatus() {
        return status;
    }

    public TicketPriority getPriority() {
        return priority;
    }

    public String getAssignedAgentId() {
        return assignedAgentId;
    }

    public String getHandoffReason() {
        return handoffReason;
    }

    public Instant getSlaDueAt() {
        return slaDueAt;
    }

    public Instant getClaimedAt() {
        return claimedAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public long getVersion() {
        return version;
    }

    public void transitionTo(TicketStatus target, String reason) {
        // 领域状态流转：阻止关闭后修改、无原因升级和非法状态迁移。
        if (status == TicketStatus.CLOSED) {
            throw new TicketStateConflictException("Closed ticket cannot be changed");
        }
        if (target == TicketStatus.ESCALATED && (reason == null || reason.isBlank())) {
            throw new TicketStateConflictException("Escalation requires a reason");
        }
        if (!TicketWorkflow.canTransit(status, target)) {
            throw new TicketStateConflictException("Illegal ticket transition from " + status + " to " + target);
        }
        status = target;
        if (target == TicketStatus.ESCALATED) {
            handoffReason = reason;
        }
    }
}
