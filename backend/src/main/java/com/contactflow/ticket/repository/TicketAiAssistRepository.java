package com.contactflow.ticket.repository;

import com.contactflow.ticket.domain.TicketAiAssist;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TicketAiAssistRepository extends JpaRepository<TicketAiAssist, UUID> {
    Optional<TicketAiAssist> findByTicketIdAndSourceEventId(UUID ticketId, String sourceEventId);

    List<TicketAiAssist> findByTicketIdOrderByCreatedAtDesc(UUID ticketId);
}
