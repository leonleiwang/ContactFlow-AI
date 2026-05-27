package com.contactflow.ticket.service;

import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class LoggingTicketDomainEventPublisher implements TicketDomainEventPublisher {
    private static final Logger log = LoggerFactory.getLogger(LoggingTicketDomainEventPublisher.class);

    @Override
    public void publish(String eventType, Map<String, Object> payload) {
        log.info("domain_event type={} payload={}", eventType, payload);
    }
}
