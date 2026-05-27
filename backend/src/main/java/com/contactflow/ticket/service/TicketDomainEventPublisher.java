package com.contactflow.ticket.service;

import java.util.Map;

public interface TicketDomainEventPublisher {
    void publish(String eventType, Map<String, Object> payload);
}
