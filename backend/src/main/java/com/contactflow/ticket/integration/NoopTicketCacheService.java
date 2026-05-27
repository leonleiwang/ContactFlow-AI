package com.contactflow.ticket.integration;

import java.time.Duration;
import java.util.Optional;
import org.springframework.stereotype.Component;

@Component
public class NoopTicketCacheService implements TicketCacheService {
    @Override
    public Optional<String> get(String key) {
        return Optional.empty();
    }

    @Override
    public void put(String key, String value, Duration ttl) {
        // Cache is optional; MySQL remains the source of truth.
    }

    @Override
    public void evict(String key) {
        // Cache is optional; evict can be a no-op when Redis is disabled.
    }
}
