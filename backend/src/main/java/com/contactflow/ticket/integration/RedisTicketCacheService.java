package com.contactflow.ticket.integration;

// 展示说明：Redis 缓存实现，承载热工单、队列计数、AI Assist 摘要和抢单削峰锁等 V0.2 业务缓存。

import java.time.Duration;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
@Primary
@ConditionalOnProperty(prefix = "contactflow.redis", name = "enabled", havingValue = "true")
// 条件化 Redis 实现：开启 Redis 时替换 Noop 缓存，关闭时业务仍以 MySQL 为事实来源。
public class RedisTicketCacheService implements TicketCacheService {
    private final StringRedisTemplate redisTemplate;

    public RedisTicketCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    // 读取缓存值：用于热工单、幂等标记和摘要查询。
    public Optional<String> get(String key) {
        return Optional.ofNullable(redisTemplate.opsForValue().get(key));
    }

    @Override
    // 写入带 TTL 的缓存：避免业务缓存长期堆积，也便于演示过期策略。
    public void put(String key, String value, Duration ttl) {
        redisTemplate.opsForValue().set(key, value, ttl);
    }

    @Override
    // 原子增减计数：维护租户队列状态数量，降低频繁聚合查询压力。
    public long increment(String key, long delta, Duration ttl) {
        Long value = redisTemplate.opsForValue().increment(key, delta);
        redisTemplate.expire(key, ttl);
        return value == null ? 0L : value;
    }

    @Override
    // SETNX 抢占锁：用于并发抢单削峰，最终一致性仍由 MySQL 条件更新保证。
    public boolean setIfAbsent(String key, String value, Duration ttl) {
        Boolean stored = redisTemplate.opsForValue().setIfAbsent(key, value, ttl);
        return Boolean.TRUE.equals(stored);
    }

    @Override
    // 删除缓存键：抢单结束后释放短锁，状态变更后可清理旧缓存。
    public void evict(String key) {
        redisTemplate.delete(key);
    }
}
