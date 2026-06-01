package com.contactflow.ticket.integration;

// 展示说明：Redis 关闭时的 fallback 缓存实现，保证本地开发和测试不依赖外部基础设施。

import java.time.Duration;
import java.util.Optional;
import org.springframework.stereotype.Component;

@Component
// 空缓存实现：维持 TicketCacheService 契约，让业务代码无需关心 Redis 是否启用。
public class NoopTicketCacheService implements TicketCacheService {
    @Override
    // 读取 fallback：未启用 Redis 时永远 miss，业务继续走 MySQL。
    public Optional<String> get(String key) {
        return Optional.empty();
    }

    @Override
    // 写入 fallback：缓存是可选增强，关闭时不影响主流程。
    public void put(String key, String value, Duration ttl) {
        // Cache is optional; MySQL remains the source of truth.
    }

    @Override
    // 删除 fallback：Redis 关闭时无需实际清理。
    public void evict(String key) {
        // Cache is optional; evict can be a no-op when Redis is disabled.
    }
}
