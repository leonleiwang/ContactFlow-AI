package com.contactflow.ticket.integration;

// 展示说明：Redis 业务缓存 key 规范集中定义，避免热工单、队列计数、AI 摘要和抢单锁命名分散。

import com.contactflow.ticket.domain.TicketStatus;
import java.util.UUID;

public final class TicketCacheKeys {
    private TicketCacheKeys() {
    }

    // 热工单缓存 key：按租户和工单 ID 隔离，避免跨租户读取。
    public static String ticket(String tenantId, UUID ticketId) {
        return "ticket:%s:%s".formatted(tenantId, ticketId);
    }

    // 队列计数缓存 key：按租户和工单状态聚合坐席台队列数量。
    public static String queueCount(String tenantId, TicketStatus status) {
        return "ticket_count:%s:%s".formatted(tenantId, status.name());
    }

    // AI Assist 摘要缓存 key：保存最近建议或计数，用于右侧面板快速展示。
    public static String aiAssistSummary(UUID ticketId) {
        return "ai_assists:%s".formatted(ticketId);
    }

    // 抢单削峰锁 key：为热点工单提供短 TTL Redis 锁。
    public static String claimLock(UUID ticketId) {
        return "claim_lock:%s".formatted(ticketId);
    }
}
