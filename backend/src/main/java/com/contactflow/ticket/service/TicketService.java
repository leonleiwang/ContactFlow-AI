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
import com.contactflow.ticket.repository.SupportTicketRepository;
import com.contactflow.ticket.repository.TicketAiAssistRepository;
import com.contactflow.ticket.repository.TicketEventRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TicketService {
    private final SupportTicketRepository ticketRepository;
    private final TicketEventRepository eventRepository;
    private final TicketAiAssistRepository aiAssistRepository;
    private final TicketDomainEventPublisher eventPublisher;

    public TicketService(
            SupportTicketRepository ticketRepository,
            TicketEventRepository eventRepository,
            TicketAiAssistRepository aiAssistRepository,
            TicketDomainEventPublisher eventPublisher
    ) {
        this.ticketRepository = ticketRepository;
        this.eventRepository = eventRepository;
        this.aiAssistRepository = aiAssistRepository;
        this.eventPublisher = eventPublisher;
    }

    @Transactional
    public SupportTicket createTicket(String tenantId, String title, String customerName, String customerMessage, TicketPriority priority) {
        SupportTicket ticket = new SupportTicket(tenantId, title, customerName, customerMessage, priority, Instant.now().plusSeconds(3600));
        SupportTicket saved = ticketRepository.save(ticket);
        eventRepository.save(new TicketEvent(saved.getId(), tenantId, TicketEventType.CREATED, "system", null, TicketStatus.OPEN, "ticket created"));

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
        return ticketRepository.findByTenantIdOrderByCreatedAtDesc(tenantId);
    }

    @Transactional(readOnly = true)
    public SupportTicket getTicket(String tenantId, UUID ticketId) {
        SupportTicket ticket = ticketRepository.findById(ticketId).orElseThrow(() -> new TicketNotFoundException(ticketId));
        if (!ticket.getTenantId().equals(tenantId)) {
            throw new TicketNotFoundException(ticketId);
        }
        return ticket;
    }

    @Transactional
    public SupportTicket claimTicket(String tenantId, UUID ticketId, String agentId) {
        // 抢单使用“条件更新”而不是先查再改，避免两个客服同时读到 OPEN 后都以为自己能成功。
        // Redis 锁可以减少热点冲突，但数据库更新行数才是最终事实来源。
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
        return getTicket(tenantId, ticketId);
    }

    @Transactional
    public SupportTicket transition(String tenantId, UUID ticketId, String actorId, TicketStatus targetStatus, String reason) {
        SupportTicket ticket = getTicket(tenantId, ticketId);
        TicketStatus before = ticket.getStatus();
        ticket.transitionTo(targetStatus, reason);
        SupportTicket saved = ticketRepository.save(ticket);
        eventRepository.save(new TicketEvent(ticketId, tenantId, TicketEventType.STATUS_CHANGED, actorId, before, targetStatus, reason));
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
        // AI 事件可能因为 MQ retry 被重复投递；以 sourceEventId 做幂等键，保证同一个事件只落一条结果。
        return aiAssistRepository.findByTicketIdAndSourceEventId(ticketId, sourceEventId)
                .orElseGet(() -> {
                    TicketAiAssist assist = new TicketAiAssist(ticketId, sourceEventId, intent, summary, suggestedReply, handoffRecommended, handoffReason, slaRisk, BigDecimal.valueOf(confidence), citationsJson, latencyMs, estimatedCostUsd);
                    TicketAiAssist saved = aiAssistRepository.save(assist);
                    SupportTicket ticket = ticketRepository.findById(ticketId).orElseThrow(() -> new TicketNotFoundException(ticketId));
                    eventRepository.save(new TicketEvent(ticketId, ticket.getTenantId(), TicketEventType.AI_ASSIST_ATTACHED, "ai-service", ticket.getStatus(), ticket.getStatus(), "ai assist attached"));
                    return saved;
                });
    }

    @Transactional(readOnly = true)
    public List<TicketEvent> listEvents(UUID ticketId) {
        return eventRepository.findByTicketIdOrderByCreatedAtAsc(ticketId);
    }

    @Transactional(readOnly = true)
    public List<TicketAiAssist> listAiAssists(UUID ticketId) {
        return aiAssistRepository.findByTicketIdOrderByCreatedAtDesc(ticketId);
    }
}
