package com.contactflow.ticket.domain;

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

    public static boolean canTransit(TicketStatus from, TicketStatus to) {
        return ALLOWED.getOrDefault(from, Set.of()).contains(to);
    }
}
