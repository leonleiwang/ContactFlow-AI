package com.contactflow.ticket.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class TicketWorkflowTest {
    @Test
    void openTicketCanMoveToInProgress() {
        SupportTicket ticket = new SupportTicket("tenant-a", "Refund request", "Mia", "Need refund", TicketPriority.NORMAL, Instant.now());

        ticket.transitionTo(TicketStatus.IN_PROGRESS, null);

        assertThat(ticket.getStatus()).isEqualTo(TicketStatus.IN_PROGRESS);
    }

    @Test
    void escalationRequiresReason() {
        SupportTicket ticket = new SupportTicket("tenant-a", "Complaint", "Mia", "Bad service", TicketPriority.HIGH, Instant.now());
        ticket.transitionTo(TicketStatus.IN_PROGRESS, null);

        assertThatThrownBy(() -> ticket.transitionTo(TicketStatus.ESCALATED, " "))
                .isInstanceOf(TicketStateConflictException.class);
    }

    @Test
    void closedTicketCannotBeChanged() {
        SupportTicket ticket = new SupportTicket("tenant-a", "Done", "Mia", "Thanks", TicketPriority.LOW, Instant.now());
        ticket.transitionTo(TicketStatus.IN_PROGRESS, null);
        ticket.transitionTo(TicketStatus.RESOLVED, null);
        ticket.transitionTo(TicketStatus.CLOSED, null);

        assertThatThrownBy(() -> ticket.transitionTo(TicketStatus.IN_PROGRESS, null))
                .isInstanceOf(TicketStateConflictException.class);
    }
}
