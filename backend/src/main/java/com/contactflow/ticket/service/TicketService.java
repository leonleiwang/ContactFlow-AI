package com.contactflow.ticket.service;

import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketAiAssist;
import com.contactflow.ticket.domain.TicketEvent;
import com.contactflow.ticket.domain.TicketEventType;
import com.contactflow.ticket.domain.TicketNotFoundException;
import com.contactflow.ticket.domain.TicketPriority;
import com.contactflow.ticket.domain.TicketStateConflictException;
import com.contactflow.ticket.domain.TicketStatus;
import com.contactflow.ticket.integration.TicketCacheKeys;
import com.contactflow.ticket.integration.TicketCacheService;
import com.contactflow.ticket.repository.SupportTicketRepository;
import com.contactflow.ticket.repository.TicketAiAssistRepository;
import com.contactflow.ticket.repository.TicketEventRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TicketService {
    private static final Duration TICKET_CACHE_TTL = Duration.ofMinutes(5);
    private static final Duration QUEUE_COUNT_TTL = Duration.ofMinutes(2);
    private static final Duration AI_ASSIST_CACHE_TTL = Duration.ofMinutes(10);
    private static final Duration CLAIM_LOCK_TTL = Duration.ofSeconds(8);

    private final SupportTicketRepository ticketRepository;
    private final TicketEventRepository eventRepository;
    private final TicketAiAssistRepository aiAssistRepository;
    private final TicketDomainEventPublisher eventPublisher;
    private final TicketCacheService cacheService;
    private final ObjectMapper objectMapper;

    public TicketService(
            SupportTicketRepository ticketRepository,
            TicketEventRepository eventRepository,
            TicketAiAssistRepository aiAssistRepository,
            TicketDomainEventPublisher eventPublisher,
            TicketCacheService cacheService,
            ObjectMapper objectMapper
    ) {
        this.ticketRepository = ticketRepository;
        this.eventRepository = eventRepository;
        this.aiAssistRepository = aiAssistRepository;
        this.eventPublisher = eventPublisher;
        this.cacheService = cacheService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public SupportTicket createTicket(String tenantId, String title, String customerName, String customerMessage, TicketPriority priority) {
        SupportTicket ticket = new SupportTicket(tenantId, title, customerName, customerMessage, priority, Instant.now().plusSeconds(3600));
        SupportTicket saved = ticketRepository.save(ticket);
        eventRepository.save(new TicketEvent(saved.getId(), tenantId, TicketEventType.CREATED, "system", null, TicketStatus.OPEN, "ticket created"));
        cacheTicket(saved);
        cacheService.increment(TicketCacheKeys.queueCount(tenantId, TicketStatus.OPEN), 1, QUEUE_COUNT_TTL);

        eventPublisher.publish("ticket.created", Map.of(
                "eventId", UUID.randomUUID().toString(),
                "ticketId", saved.getId().toString(),
                "tenantId", tenantId,
                "message", customerMessage
        ));
        return saved;
    }

    @Transactional(readOnly = true)
    public List<SupportTicket> listTickets(String tenantId) {
        List<SupportTicket> tickets = ticketRepository.findByTenantIdOrderByCreatedAtDesc(tenantId);
        cacheQueueCounts(tenantId, tickets);
        return tickets;
    }

    @Transactional(readOnly = true)
    public SupportTicket getTicket(String tenantId, UUID ticketId) {
        SupportTicket ticket = ticketRepository.findById(ticketId).orElseThrow(() -> new TicketNotFoundException(ticketId));
        if (!ticket.getTenantId().equals(tenantId)) {
            throw new TicketNotFoundException(ticketId);
        }
        cacheTicket(ticket);
        return ticket;
    }

    @Transactional
    public SupportTicket claimTicket(String tenantId, UUID ticketId, String agentId) {
        // The short Redis lock reduces hot-ticket contention; the conditional
        // MySQL update remains the final source of truth.
        String lockKey = TicketCacheKeys.claimLock(ticketId);
        if (!cacheService.setIfAbsent(lockKey, agentId, CLAIM_LOCK_TTL)) {
            throw new TicketStateConflictException("Ticket is currently being claimed by another agent");
        }
        try {
            int updatedRows = ticketRepository.claimOpenTicket(
                    ticketId,
                    tenantId,
                    agentId,
                    Instant.now(),
                    TicketStatus.OPEN,
                    TicketStatus.IN_PROGRESS
            );

            if (updatedRows == 0) {
                SupportTicket current = ticketRepository.findById(ticketId).orElseThrow(() -> new TicketNotFoundException(ticketId));
                if (!current.getTenantId().equals(tenantId)) {
                    throw new TicketNotFoundException(ticketId);
                }
                throw new TicketStateConflictException("Ticket is not claimable. currentStatus=" + current.getStatus() + ", assignedAgentId=" + current.getAssignedAgentId());
            }

            eventRepository.save(new TicketEvent(ticketId, tenantId, TicketEventType.CLAIMED, agentId, TicketStatus.OPEN, TicketStatus.IN_PROGRESS, "ticket claimed"));
            eventPublisher.publish("ticket.status_changed", Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "ticketId", ticketId.toString(),
                    "tenantId", tenantId,
                    "fromStatus", TicketStatus.OPEN.name(),
                    "toStatus", TicketStatus.IN_PROGRESS.name()
            ));
            cacheService.increment(TicketCacheKeys.queueCount(tenantId, TicketStatus.OPEN), -1, QUEUE_COUNT_TTL);
            cacheService.increment(TicketCacheKeys.queueCount(tenantId, TicketStatus.IN_PROGRESS), 1, QUEUE_COUNT_TTL);
            return getTicket(tenantId, ticketId);
        } finally {
            cacheService.evict(lockKey);
        }
    }

    @Transactional
    public SupportTicket transition(String tenantId, UUID ticketId, String actorId, TicketStatus targetStatus, String reason) {
        SupportTicket ticket = getTicket(tenantId, ticketId);
        TicketStatus before = ticket.getStatus();
        ticket.transitionTo(targetStatus, reason);
        SupportTicket saved = ticketRepository.save(ticket);
        eventRepository.save(new TicketEvent(ticketId, tenantId, TicketEventType.STATUS_CHANGED, actorId, before, targetStatus, reason));
        cacheTicket(saved);
        cacheService.increment(TicketCacheKeys.queueCount(tenantId, before), -1, QUEUE_COUNT_TTL);
        cacheService.increment(TicketCacheKeys.queueCount(tenantId, targetStatus), 1, QUEUE_COUNT_TTL);
        eventPublisher.publish("ticket.status_changed", Map.of(
                "eventId", UUID.randomUUID().toString(),
                "ticketId", ticketId.toString(),
                "tenantId", tenantId,
                "fromStatus", before.name(),
                "toStatus", targetStatus.name()
        ));
        return saved;
    }

    @Transactional
    public TicketAiAssist attachAiAssist(UUID ticketId, String sourceEventId, String intent, String summary, String suggestedReply, boolean handoffRecommended, String handoffReason, SlaRisk slaRisk, double confidence, String citationsJson, int latencyMs, BigDecimal estimatedCostUsd) {
        // MQ retries may deliver the same AI event more than once; sourceEventId
        // keeps the callback idempotent.
        return aiAssistRepository.findByTicketIdAndSourceEventId(ticketId, sourceEventId)
                .orElseGet(() -> {
                    TicketAiAssist assist = new TicketAiAssist(ticketId, sourceEventId, intent, summary, suggestedReply, handoffRecommended, handoffReason, slaRisk, BigDecimal.valueOf(confidence), citationsJson, latencyMs, estimatedCostUsd);
                    TicketAiAssist saved = aiAssistRepository.save(assist);
                    SupportTicket ticket = ticketRepository.findById(ticketId).orElseThrow(() -> new TicketNotFoundException(ticketId));
                    eventRepository.save(new TicketEvent(ticketId, ticket.getTenantId(), TicketEventType.AI_ASSIST_ATTACHED, "ai-service", ticket.getStatus(), ticket.getStatus(), "ai assist attached"));
                    cacheAiAssistSummary(saved);
                    return saved;
                });
    }

    @Transactional(readOnly = true)
    public List<TicketEvent> listEvents(UUID ticketId) {
        return eventRepository.findByTicketIdOrderByCreatedAtAsc(ticketId);
    }

    @Transactional(readOnly = true)
    public List<TicketAiAssist> listAiAssists(UUID ticketId) {
        List<TicketAiAssist> assists = aiAssistRepository.findByTicketIdOrderByCreatedAtDesc(ticketId);
        cacheService.put(TicketCacheKeys.aiAssistSummary(ticketId), "{\"count\":" + assists.size() + "}", AI_ASSIST_CACHE_TTL);
        return assists;
    }

    private void cacheQueueCounts(String tenantId, List<SupportTicket> tickets) {
        for (TicketStatus status : TicketStatus.values()) {
            long count = tickets.stream().filter(ticket -> ticket.getStatus() == status).count();
            cacheService.put(TicketCacheKeys.queueCount(tenantId, status), Long.toString(count), QUEUE_COUNT_TTL);
        }
    }

    private void cacheTicket(SupportTicket ticket) {
        try {
            cacheService.put(
                    TicketCacheKeys.ticket(ticket.getTenantId(), ticket.getId()),
                    objectMapper.writeValueAsString(Map.of(
                            "id", ticket.getId().toString(),
                            "tenantId", ticket.getTenantId(),
                            "status", ticket.getStatus().name(),
                            "priority", ticket.getPriority().name(),
                            "title", ticket.getTitle(),
                            "version", ticket.getVersion()
                    )),
                    TICKET_CACHE_TTL
            );
        } catch (JsonProcessingException ignored) {
            // Cache writes are best-effort; MySQL remains the source of truth.
        }
    }

    private void cacheAiAssistSummary(TicketAiAssist assist) {
        cacheService.put(
                TicketCacheKeys.aiAssistSummary(assist.getTicketId()),
                "{\"latestAssistId\":\"" + assist.getId() + "\"}",
                AI_ASSIST_CACHE_TTL
        );
    }
}
