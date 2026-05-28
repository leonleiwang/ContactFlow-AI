package com.contactflow.ticket.service;

import java.util.Map;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

@TestConfiguration
public class NoopPublisherConfig {
    @Bean
    @Primary
    TicketDomainEventPublisher noopPublisher() {
        return new TicketDomainEventPublisher() {
            @Override
            public void publish(String eventType, Map<String, Object> payload) {
                // Business tests do not depend on a real message broker.
            }
        };
    }
}
