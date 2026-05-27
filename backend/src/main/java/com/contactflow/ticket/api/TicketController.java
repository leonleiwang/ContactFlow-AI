package com.contactflow.ticket.api;

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
public class TicketController {
    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @PostMapping("/tickets")
    public TicketResponse createTicket(@Valid @RequestBody CreateTicketRequest request) {
        return TicketResponse.from(ticketService.createTicket(request.tenantId(), request.title(), request.customerName(), request.customerMessage(), request.priority()));
    }

    @GetMapping("/tickets")
    public List<TicketResponse> listTickets(@RequestParam String tenantId) {
        return ticketService.listTickets(tenantId).stream().map(TicketResponse::from).toList();
    }

    @GetMapping("/tickets/{ticketId}")
    public TicketResponse getTicket(@PathVariable UUID ticketId, @RequestParam String tenantId) {
        return TicketResponse.from(ticketService.getTicket(tenantId, ticketId));
    }

    @PostMapping("/tickets/{ticketId}/claim")
    public TicketResponse claimTicket(@PathVariable UUID ticketId, @Valid @RequestBody ClaimTicketRequest request) {
        return TicketResponse.from(ticketService.claimTicket(request.tenantId(), ticketId, request.agentId()));
    }

    @PostMapping("/tickets/{ticketId}/transitions")
    public TicketResponse transition(@PathVariable UUID ticketId, @Valid @RequestBody TransitionRequest request) {
        return TicketResponse.from(ticketService.transition(request.tenantId(), ticketId, request.actorId(), request.targetStatus(), request.reason()));
    }

    @PostMapping("/ai-assists")
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
    public List<AiAssistResponse> listAiAssists(@PathVariable UUID ticketId) {
        return ticketService.listAiAssists(ticketId).stream().map(AiAssistResponse::from).toList();
    }
}
