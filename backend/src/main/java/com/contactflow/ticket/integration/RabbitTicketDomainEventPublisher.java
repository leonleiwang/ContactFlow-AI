package com.contactflow.ticket.integration;

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
public class RabbitTicketDomainEventPublisher implements TicketDomainEventPublisher {
    private final RabbitTemplate rabbitTemplate;
    private final RabbitEventProperties properties;

    public RabbitTicketDomainEventPublisher(RabbitTemplate rabbitTemplate, RabbitEventProperties properties) {
        this.rabbitTemplate = rabbitTemplate;
        this.properties = properties;
    }

    @Override
    public void publish(String eventType, Map<String, Object> payload) {
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("eventType", eventType);
        envelope.put("schemaVersion", "v1");
        envelope.put("occurredAt", Instant.now().toString());
        envelope.put("payload", payload);
        rabbitTemplate.convertAndSend(properties.getExchange(), eventType, envelope);
    }
}
