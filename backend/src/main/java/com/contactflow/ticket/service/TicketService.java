package com.contactflow.ticket.service;

// 展示说明：工单业务服务聚合 V0.1 工单闭环与 V0.2 RabbitMQ、Redis、AI Assist 幂等落库和审计事件能力。

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
// 领域应用服务：统一承载创建、列表、抢单、状态流转、AI Assist 回写和缓存刷新。
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
    // 创建工单：保存主表和 CREATED 审计事件，刷新热工单/队列计数缓存，并发布 ticket.created 事件。
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
    // 工单列表：按租户读取队列，并把各状态数量写入 Redis 业务缓存，供坐席台快速展示。
    public List<SupportTicket> listTickets(String tenantId) {
        List<SupportTicket> tickets = ticketRepository.findByTenantIdOrderByCreatedAtDesc(tenantId);
        cacheQueueCounts(tenantId, tickets);
        return tickets;
    }

    @Transactional(readOnly = true)
    // 工单详情：强制租户校验，避免跨租户读取，并刷新热工单缓存。
    public SupportTicket getTicket(String tenantId, UUID ticketId) {
        SupportTicket ticket = ticketRepository.findById(ticketId).orElseThrow(() -> new TicketNotFoundException(ticketId));
        if (!ticket.getTenantId().equals(tenantId)) {
            throw new TicketNotFoundException(ticketId);
        }
        cacheTicket(ticket);
        return ticket;
    }

    @Transactional
    // 并发抢单：Redis 短锁削峰，MySQL 条件更新作为最终事实来源，失败时返回明确冲突。
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
    // 状态流转：调用领域状态机校验合法迁移，记录审计事件，刷新队列缓存并发布状态变更事件。
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
    // AI Assist 幂等落库：按 sourceEventId 去重，保存建议结果并写入 AI_ASSIST_ATTACHED 审计事件。
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
    // 审计事件查询：按时间顺序返回工单生命周期事件，便于演示完整闭环。
    public List<TicketEvent> listEvents(UUID ticketId) {
        return eventRepository.findByTicketIdOrderByCreatedAtAsc(ticketId);
    }

    @Transactional(readOnly = true)
    // AI Assist 查询：返回工单下历史建议，并缓存摘要计数，支撑坐席台右侧面板。
    public List<TicketAiAssist> listAiAssists(UUID ticketId) {
        List<TicketAiAssist> assists = aiAssistRepository.findByTicketIdOrderByCreatedAtDesc(ticketId);
        cacheService.put(TicketCacheKeys.aiAssistSummary(ticketId), "{\"count\":" + assists.size() + "}", AI_ASSIST_CACHE_TTL);
        return assists;
    }

    private void cacheQueueCounts(String tenantId, List<SupportTicket> tickets) {
        // 队列计数缓存：按状态聚合当前租户工单数量，降低高频队列刷新压力。
        for (TicketStatus status : TicketStatus.values()) {
            long count = tickets.stream().filter(ticket -> ticket.getStatus() == status).count();
            cacheService.put(TicketCacheKeys.queueCount(tenantId, status), Long.toString(count), QUEUE_COUNT_TTL);
        }
    }

    private void cacheTicket(SupportTicket ticket) {
        // 热工单缓存：保存坐席台常用字段，缓存失败不影响 MySQL 主流程。
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
        // AI Assist 摘要缓存：保存最近一次建议 ID，方便前端快速判断是否有新结果。
        cacheService.put(
                TicketCacheKeys.aiAssistSummary(assist.getTicketId()),
                "{\"latestAssistId\":\"" + assist.getId() + "\"}",
                AI_ASSIST_CACHE_TTL
        );
    }
}
