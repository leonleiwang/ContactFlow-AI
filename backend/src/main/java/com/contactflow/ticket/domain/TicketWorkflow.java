package com.contactflow.ticket.domain;

// 展示说明：工单状态机集中声明合法流转路径，保证 V0.1 工单闭环在服务层和测试中都有同一套规则。

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

public final class TicketWorkflow {
    private static final Map<TicketStatus, Set<TicketStatus>> ALLOWED = new EnumMap<>(TicketStatus.class);

    static {
        ALLOWED.put(TicketStatus.OPEN, EnumSet.of(TicketStatus.IN_PROGRESS, TicketStatus.CANCELLED));
        ALLOWED.put(TicketStatus.IN_PROGRESS, EnumSet.of(TicketStatus.WAITING_CUSTOMER, TicketStatus.RESOLVED, TicketStatus.ESCALATED));
        ALLOWED.put(TicketStatus.WAITING_CUSTOMER, EnumSet.of(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.ESCALATED));
        ALLOWED.put(TicketStatus.RESOLVED, EnumSet.of(TicketStatus.CLOSED, TicketStatus.IN_PROGRESS));
        ALLOWED.put(TicketStatus.ESCALATED, EnumSet.of(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED));
        ALLOWED.put(TicketStatus.CLOSED, EnumSet.noneOf(TicketStatus.class));
        ALLOWED.put(TicketStatus.CANCELLED, EnumSet.noneOf(TicketStatus.class));
    }

    private TicketWorkflow() {
    }

    // 状态迁移校验：只有 ALLOWED 表中的迁移可以通过，非法流转会在领域对象中被拒绝。
    public static boolean canTransit(TicketStatus from, TicketStatus to) {
        return ALLOWED.getOrDefault(from, Set.of()).contains(to);
    }
}
