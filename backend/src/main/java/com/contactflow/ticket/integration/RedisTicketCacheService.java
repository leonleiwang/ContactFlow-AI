package com.contactflow.ticket.integration;

import java.time.Duration;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
@Primary
@ConditionalOnProperty(prefix = "contactflow.redis", name = "enabled", havingValue = "true")
public class RedisTicketCacheService implements TicketCacheService {
    private final StringRedisTemplate redisTemplate;

    public RedisTicketCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public Optional<String> get(String key) {
        return Optional.ofNullable(redisTemplate.opsForValue().get(key));
    }

    @Override
    public void put(String key, String value, Duration ttl) {
        redisTemplate.opsForValue().set(key, value, ttl);
    }

    @Override
    public long increment(String key, long delta, Duration ttl) {
        Long value = redisTemplate.opsForValue().increment(key, delta);
        redisTemplate.expire(key, ttl);
        return value == null ? 0L : value;
    }

    @Override
    public boolean setIfAbsent(String key, String value, Duration ttl) {
        Boolean stored = redisTemplate.opsForValue().setIfAbsent(key, value, ttl);
        return Boolean.TRUE.equals(stored);
    }

    @Override
    public void evict(String key) {
        redisTemplate.delete(key);
    }
}
