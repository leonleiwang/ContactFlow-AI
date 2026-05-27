package com.contactflow.ticket.integration;

import java.time.Duration;
import java.util.Optional;

public interface TicketCacheService {
    Optional<String> get(String key);

    void put(String key, String value, Duration ttl);

    void evict(String key);
}
