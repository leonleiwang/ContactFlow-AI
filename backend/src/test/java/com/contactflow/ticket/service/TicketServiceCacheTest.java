package com.contactflow.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.contactflow.ticket.domain.SlaRisk;
import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketPriority;
import com.contactflow.ticket.domain.TicketStateConflictException;
import com.contactflow.ticket.domain.TicketStatus;
import com.contactflow.ticket.integration.TicketCacheKeys;
import com.contactflow.ticket.integration.TicketCacheService;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@Import({NoopPublisherConfig.class, TicketServiceCacheTest.RecordingCacheConfig.class})
class TicketServiceCacheTest {
    @Autowired
    private TicketService ticketService;

    @Autowired
    private RecordingTicketCacheService cacheService;

    @BeforeEach
    void resetCacheRecorder() {
        cacheService.clear();
    }

    @Test
    void createAndListTicketsCacheHotTicketAndQueueCounts() {
        String tenantId = uniqueTenant();
        SupportTicket ticket = ticketService.createTicket(tenantId, "Refund", "Nora", "Need refund", TicketPriority.NORMAL);

        assertThat(cacheService.puts).anyMatch(put -> put.key().equals(TicketCacheKeys.ticket(tenantId, ticket.getId())));
        assertThat(cacheService.increments).anyMatch(increment -> increment.key().equals(TicketCacheKeys.queueCount(tenantId, TicketStatus.OPEN)) && increment.delta() == 1);

        cacheService.clear();
        ticketService.listTickets(tenantId);

        assertThat(cacheService.puts).anyMatch(put -> put.key().equals(TicketCacheKeys.queueCount(tenantId, TicketStatus.OPEN)) && put.value().equals("1"));
        assertThat(cacheService.puts).anyMatch(put -> put.key().equals(TicketCacheKeys.queueCount(tenantId, TicketStatus.IN_PROGRESS)) && put.value().equals("0"));
    }

    @Test
    void claimTicketUsesClaimLockAndUpdatesQueueCounts() {
        String tenantId = uniqueTenant();
        SupportTicket ticket = ticketService.createTicket(tenantId, "Late delivery", "Nora", "Package late", TicketPriority.HIGH);
        cacheService.clear();

        ticketService.claimTicket(tenantId, ticket.getId(), "agent-1");

        String claimLockKey = TicketCacheKeys.claimLock(ticket.getId());
        assertThat(cacheService.setIfAbsentCalls).anyMatch(call -> call.key().equals(claimLockKey) && call.value().equals("agent-1"));
        assertThat(cacheService.evicts).contains(claimLockKey);
        assertThat(cacheService.increments).anyMatch(increment -> increment.key().equals(TicketCacheKeys.queueCount(tenantId, TicketStatus.OPEN)) && increment.delta() == -1);
        assertThat(cacheService.increments).anyMatch(increment -> increment.key().equals(TicketCacheKeys.queueCount(tenantId, TicketStatus.IN_PROGRESS)) && increment.delta() == 1);
    }

    @Test
    void claimTicketFailsFastWhenClaimLockIsHeld() {
        String tenantId = uniqueTenant();
        SupportTicket ticket = ticketService.createTicket(tenantId, "Late delivery", "Nora", "Package late", TicketPriority.HIGH);
        cacheService.clear();
        cacheService.allowSetIfAbsent = false;

        assertThatThrownBy(() -> ticketService.claimTicket(tenantId, ticket.getId(), "agent-1"))
                .isInstanceOf(TicketStateConflictException.class)
                .hasMessageContaining("currently being claimed");
    }

    @Test
    void attachAndListAiAssistsCacheSummary() {
        SupportTicket ticket = ticketService.createTicket(uniqueTenant(), "Refund", "Nora", "Need refund", TicketPriority.NORMAL);
        cacheService.clear();

        ticketService.attachAiAssist(ticket.getId(), "event-1", "refund", "Customer asks refund", "Please confirm order id.", false, null, SlaRisk.LOW, 0.85, "[]", 120, new BigDecimal("0.0002"));

        assertThat(cacheService.puts).anyMatch(put -> put.key().equals(TicketCacheKeys.aiAssistSummary(ticket.getId())) && put.value().contains("latestAssistId"));

        cacheService.clear();
        ticketService.listAiAssists(ticket.getId());

        assertThat(cacheService.puts).anyMatch(put -> put.key().equals(TicketCacheKeys.aiAssistSummary(ticket.getId())) && put.value().equals("{\"count\":1}"));
    }

    private String uniqueTenant() {
        return "tenant-cache-" + UUID.randomUUID();
    }

    @TestConfiguration
    static class RecordingCacheConfig {
        @Bean
        @Primary
        RecordingTicketCacheService recordingTicketCacheService() {
            return new RecordingTicketCacheService();
        }
    }

    static class RecordingTicketCacheService implements TicketCacheService {
        private final List<PutCall> puts = new ArrayList<>();
        private final List<IncrementCall> increments = new ArrayList<>();
        private final List<SetIfAbsentCall> setIfAbsentCalls = new ArrayList<>();
        private final List<String> evicts = new ArrayList<>();
        private boolean allowSetIfAbsent = true;

        @Override
        public Optional<String> get(String key) {
            return Optional.empty();
        }

        @Override
        public void put(String key, String value, Duration ttl) {
            puts.add(new PutCall(key, value, ttl));
        }

        @Override
        public long increment(String key, long delta, Duration ttl) {
            increments.add(new IncrementCall(key, delta, ttl));
            return delta;
        }

        @Override
        public boolean setIfAbsent(String key, String value, Duration ttl) {
            setIfAbsentCalls.add(new SetIfAbsentCall(key, value, ttl));
            return allowSetIfAbsent;
        }

        @Override
        public void evict(String key) {
            evicts.add(key);
        }

        private void clear() {
            puts.clear();
            increments.clear();
            setIfAbsentCalls.clear();
            evicts.clear();
            allowSetIfAbsent = true;
        }
    }

    record PutCall(String key, String value, Duration ttl) {
    }

    record IncrementCall(String key, long delta, Duration ttl) {
    }

    record SetIfAbsentCall(String key, String value, Duration ttl) {
    }
}
