package com.contactflow.ticket.integration;

import java.time.Duration;
import java.util.Optional;

public interface TicketCacheService {
    Optional<String> get(String key);

    void put(String key, String value, Duration ttl);

    default long increment(String key, long delta, Duration ttl) {
        return 0L;
    }

    default boolean setIfAbsent(String key, String value, Duration ttl) {
        return true;
    }

    void evict(String key);
}
