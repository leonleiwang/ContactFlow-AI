package com.contactflow.ticket.integration;

// 展示说明：RabbitMQ 事件发布器，把工单领域事件封装为标准 envelope 并发布到主题交换机。

import com.contactflow.ticket.service.TicketDomainEventPublisher;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

@Component
@Primary
@ConditionalOnProperty(prefix = "contactflow.events.rabbit", name = "enabled", havingValue = "true")
// 真实 MQ 发布实现：启用 RabbitMQ 时替换日志 publisher，支撑多消费者订阅和异步 AI Assist。
public class RabbitTicketDomainEventPublisher implements TicketDomainEventPublisher {
    private final RabbitTemplate rabbitTemplate;
    private final RabbitEventProperties properties;

    public RabbitTicketDomainEventPublisher(RabbitTemplate rabbitTemplate, RabbitEventProperties properties) {
        this.rabbitTemplate = rabbitTemplate;
        this.properties = properties;
    }

    @Override
    // 发布领域事件：统一补充 eventType、schemaVersion、occurredAt 和 payload，便于统计、审计和消费端扩展。
    public void publish(String eventType, Map<String, Object> payload) {
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("eventType", eventType);
        envelope.put("schemaVersion", "v1");
        envelope.put("occurredAt", Instant.now().toString());
        envelope.put("payload", payload);
        rabbitTemplate.convertAndSend(properties.getExchange(), eventType, envelope);
    }
}
