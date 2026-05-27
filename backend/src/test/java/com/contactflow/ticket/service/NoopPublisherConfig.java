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
                // 测试聚焦业务状态，不依赖真实 MQ。
            }
        };
    }
}
