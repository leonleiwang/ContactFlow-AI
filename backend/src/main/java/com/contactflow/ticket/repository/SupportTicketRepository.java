package com.contactflow.ticket.repository;

import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketStatus;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SupportTicketRepository extends JpaRepository<SupportTicket, UUID> {
    List<SupportTicket> findByTenantIdOrderByCreatedAtDesc(String tenantId);

    @Modifying(clearAutomatically = true, flushAutomatically = true)
    @Query("""
            update SupportTicket t
               set t.status = :targetStatus,
                   t.assignedAgentId = :agentId,
                   t.claimedAt = :claimedAt,
                   t.version = t.version + 1
             where t.id = :ticketId
               and t.tenantId = :tenantId
               and t.status = :requiredStatus
            """)
    int claimOpenTicket(
            @Param("ticketId") UUID ticketId,
            @Param("tenantId") String tenantId,
            @Param("agentId") String agentId,
            @Param("claimedAt") Instant claimedAt,
            @Param("requiredStatus") TicketStatus requiredStatus,
            @Param("targetStatus") TicketStatus targetStatus
    );
}
