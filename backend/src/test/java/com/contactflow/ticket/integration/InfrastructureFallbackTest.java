package com.contactflow.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;

import com.contactflow.ticket.service.TicketDomainEventPublisher;
import com.contactflow.ticket.service.LoggingTicketDomainEventPublisher;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class InfrastructureFallbackTest {
    @Autowired
    private TicketDomainEventPublisher publisher;

    @Autowired
    private TicketCacheService cacheService;

    @Test
    void usesFallbackInfrastructureWhenBrokerAndRedisAreDisabled() {
        assertThat(publisher).isInstanceOf(LoggingTicketDomainEventPublisher.class);
        assertThat(cacheService).isInstanceOf(NoopTicketCacheService.class);
    }
}
