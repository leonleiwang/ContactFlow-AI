package com.contactflow.ticket.api;

// 展示说明：工单 REST API 层，对外展示创建、列表、详情、抢单、流转、AI Assist 回写和审计查询能力。

import com.contactflow.ticket.api.TicketDtos.AiAssistRequest;
import com.contactflow.ticket.api.TicketDtos.AiAssistResponse;
import com.contactflow.ticket.api.TicketDtos.ClaimTicketRequest;
import com.contactflow.ticket.api.TicketDtos.CreateTicketRequest;
import com.contactflow.ticket.api.TicketDtos.TicketResponse;
import com.contactflow.ticket.api.TicketDtos.TransitionRequest;
import com.contactflow.ticket.service.TicketService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
// 工单控制器：保持接口薄封装，业务一致性和缓存/事件处理都委托给 TicketService。
public class TicketController {
    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @PostMapping("/tickets")
    // 创建工单接口：触发工单落库、审计事件和异步 AI Assist 事件发布。
    public TicketResponse createTicket(@Valid @RequestBody CreateTicketRequest request) {
        return TicketResponse.from(ticketService.createTicket(request.tenantId(), request.title(), request.customerName(), request.customerMessage(), request.priority()));
    }

    @GetMapping("/tickets")
    // 工单列表接口：按租户返回队列，用于三栏坐席台左侧列表。
    public List<TicketResponse> listTickets(@RequestParam String tenantId) {
        return ticketService.listTickets(tenantId).stream().map(TicketResponse::from).toList();
    }

    @GetMapping("/tickets/{ticketId}")
    // 工单详情接口：按租户读取单个工单，服务层负责租户隔离校验。
    public TicketResponse getTicket(@PathVariable UUID ticketId, @RequestParam String tenantId) {
        return TicketResponse.from(ticketService.getTicket(tenantId, ticketId));
    }

    @PostMapping("/tickets/{ticketId}/claim")
    // 抢单接口：演示并发领取时的 Redis 削峰锁与 MySQL 条件更新。
    public TicketResponse claimTicket(@PathVariable UUID ticketId, @Valid @RequestBody ClaimTicketRequest request) {
        return TicketResponse.from(ticketService.claimTicket(request.tenantId(), ticketId, request.agentId()));
    }

    @PostMapping("/tickets/{ticketId}/transitions")
    // 状态流转接口：驱动工单状态机、审计事件和状态变更消息。
    public TicketResponse transition(@PathVariable UUID ticketId, @Valid @RequestBody TransitionRequest request) {
        return TicketResponse.from(ticketService.transition(request.tenantId(), ticketId, request.actorId(), request.targetStatus(), request.reason()));
    }

    @PostMapping("/ai-assists")
    // AI Assist 回写接口：用于本地或测试直接模拟 ai.assist.completed 幂等落库。
    public AiAssistResponse attachAiAssist(@Valid @RequestBody AiAssistRequest request) {
        return AiAssistResponse.from(ticketService.attachAiAssist(
                request.ticketId(),
                request.sourceEventId(),
                request.intent(),
                request.summary(),
                request.suggestedReply(),
                request.handoffRecommended(),
                request.handoffReason(),
                request.slaRisk(),
                request.confidence(),
                request.citationsJson(),
                request.latencyMs(),
                request.estimatedCostUsd()
        ));
    }

    @GetMapping("/tickets/{ticketId}/events")
    // 审计事件接口：展示工单创建、抢单、流转、AI Assist 挂载等生命周期记录。
    public List<Map<String, Object>> listEvents(@PathVariable UUID ticketId) {
        return ticketService.listEvents(ticketId).stream()
                .map(event -> Map.<String, Object>of(
                        "id", event.getId(),
                        "ticketId", event.getTicketId(),
                        "eventType", event.getEventType(),
                        "fromStatus", event.getFromStatus() == null ? "" : event.getFromStatus(),
                        "toStatus", event.getToStatus() == null ? "" : event.getToStatus(),
                        "reason", event.getReason() == null ? "" : event.getReason(),
                        "createdAt", event.getCreatedAt()
                ))
                .toList();
    }

    @GetMapping("/tickets/{ticketId}/ai-assists")
    // AI Assist 列表接口：返回工单关联的历史建议结果，支撑坐席台 Copilot 面板。
    public List<AiAssistResponse> listAiAssists(@PathVariable UUID ticketId) {
        return ticketService.listAiAssists(ticketId).stream().map(AiAssistResponse::from).toList();
    }
}
