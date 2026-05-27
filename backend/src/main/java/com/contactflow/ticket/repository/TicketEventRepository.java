package com.contactflow.ticket.repository;

import com.contactflow.ticket.domain.TicketEvent;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TicketEventRepository extends JpaRepository<TicketEvent, UUID> {
    List<TicketEvent> findByTicketIdOrderByCreatedAtAsc(UUID ticketId);
}
