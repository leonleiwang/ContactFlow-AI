package com.contactflow.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketAiAssist;
import com.contactflow.ticket.domain.TicketPriority;
import com.contactflow.ticket.repository.TicketAiAssistRepository;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@Import(NoopPublisherConfig.class)
class TicketAiAssistIdempotencyTest {
    @Autowired
    private TicketService ticketService;

    @Autowired
    private TicketAiAssistRepository aiAssistRepository;

    @Test
    void duplicateAiEventReturnsExistingAssist() {
        SupportTicket ticket = ticketService.createTicket("tenant-a", "Refund", "Nora", "Need refund", TicketPriority.NORMAL);

        TicketAiAssist first = ticketService.attachAiAssist(ticket.getId(), "event-1", "refund", "Customer asks refund", "Please confirm order id.", false, null, SlaRisk.LOW, 0.85, "[]", 120, new BigDecimal("0.0002"));
        TicketAiAssist second = ticketService.attachAiAssist(ticket.getId(), "event-1", "refund", "Customer asks refund", "Please confirm order id.", false, null, SlaRisk.LOW, 0.85, "[]", 120, new BigDecimal("0.0002"));

        assertThat(second.getId()).isEqualTo(first.getId());
        assertThat(aiAssistRepository.findByTicketIdOrderByCreatedAtDesc(ticket.getId())).hasSize(1);
    }
}
