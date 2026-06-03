package com.contactflow.ticket.api;

// 展示说明：工单 API DTO 契约集中定义请求与响应字段，并通过 Bean Validation 约束接口边界。
import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketAiAssist;
import com.contactflow.ticket.domain.TicketPriority;
import com.contactflow.ticket.domain.TicketStatus;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public final class TicketDtos {
    private TicketDtos() {
    }

    // 创建工单请求：限制租户格式、文本长度和优先级，避免低质量入参进入状态机主链路。
    public record CreateTicketRequest(
            @NotBlank @Size(max = 80) @Pattern(regexp = "^tenant-[a-z0-9-]+$") String tenantId,
            @NotBlank @Size(max = 120) String title,
            @NotBlank @Size(max = 80) String customerName,
            @NotBlank @Size(max = 2000) String customerMessage,
            @NotNull TicketPriority priority
    ) {
    }

    // 领取工单请求：租户和坐席 ID 必须明确，后续由服务层做并发领取条件更新。
    public record ClaimTicketRequest(
            @NotBlank @Size(max = 80) @Pattern(regexp = "^tenant-[a-z0-9-]+$") String tenantId,
            @NotBlank @Size(max = 80) String agentId
    ) {
    }

    // 状态流转请求：目标状态必须来自枚举，原因字段限长，避免审计事件写入异常大文本。
    public record TransitionRequest(
            @NotBlank @Size(max = 80) @Pattern(regexp = "^tenant-[a-z0-9-]+$") String tenantId,
            @NotBlank @Size(max = 80) String actorId,
            @NotNull TicketStatus targetStatus,
            @Size(max = 500) String reason
    ) {
    }

    // AI Assist 回写请求：用于 ai.assist.completed 幂等落库，约束置信度、耗时、成本和文本长度。
    public record AiAssistRequest(
            @NotNull UUID ticketId,
            @NotBlank @Size(max = 120) String sourceEventId,
            @NotBlank @Size(max = 80) String intent,
            @NotBlank @Size(max = 1000) String summary,
            @NotBlank @Size(max = 2000) String suggestedReply,
            boolean handoffRecommended,
            @Size(max = 500) String handoffReason,
            @NotNull SlaRisk slaRisk,
            @DecimalMin("0.0") @DecimalMax("1.0") double confidence,
            @Size(max = 8000) String citationsJson,
            @Min(0) @Max(300000) int latencyMs,
            @NotNull @DecimalMin("0.0") BigDecimal estimatedCostUsd
    ) {
    }

    // 工单响应：返回坐席台展示所需的事实字段，避免把内部实体直接暴露给外部调用方。
    public record TicketResponse(
            UUID id,
            String tenantId,
            String title,
            String customerName,
            String customerMessage,
            TicketStatus status,
            TicketPriority priority,
            String assignedAgentId,
            Instant slaDueAt,
            Instant claimedAt,
            long version
    ) {
        // 响应映射：从 JPA 实体投影为稳定 API 结构，减少实体字段变更对前端的影响。
        public static TicketResponse from(SupportTicket ticket) {
            return new TicketResponse(
                    ticket.getId(),
                    ticket.getTenantId(),
                    ticket.getTitle(),
                    ticket.getCustomerName(),
                    ticket.getCustomerMessage(),
                    ticket.getStatus(),
                    ticket.getPriority(),
                    ticket.getAssignedAgentId(),
                    ticket.getSlaDueAt(),
                    ticket.getClaimedAt(),
                    ticket.getVersion()
            );
        }
    }

    // AI Assist 响应：回写成功后只返回幂等结果标识，详细内容可通过工单关联查询。
    public record AiAssistResponse(UUID id, UUID ticketId, String sourceEventId) {
        // 响应映射：从 AI Assist 落库实体提取外部需要的最小字段。
        public static AiAssistResponse from(TicketAiAssist assist) {
            return new AiAssistResponse(assist.getId(), assist.getTicketId(), assist.getSourceEventId());
        }
    }
}
