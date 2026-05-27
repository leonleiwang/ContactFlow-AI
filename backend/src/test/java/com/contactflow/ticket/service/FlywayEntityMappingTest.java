package com.contactflow.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.contactflow.ticket.repository.SupportTicketRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("flyway-test")
@Import(NoopPublisherConfig.class)
class FlywayEntityMappingTest {
    @Autowired
    private SupportTicketRepository ticketRepository;

    @Test
    void flywaySchemaMatchesJpaEntities() {
        // 如果 Flyway DDL 和 Entity 字段类型不一致，Spring 上下文会在 ddl-auto=validate 阶段失败。
        assertThat(ticketRepository.count()).isZero();
    }
}
