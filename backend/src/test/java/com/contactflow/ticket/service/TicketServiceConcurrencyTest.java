package com.contactflow.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.contactflow.ticket.domain.SupportTicket;
import com.contactflow.ticket.domain.TicketPriority;
import com.contactflow.ticket.domain.TicketStateConflictException;
import com.contactflow.ticket.domain.TicketStatus;
import com.contactflow.ticket.repository.SupportTicketRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@Import(NoopPublisherConfig.class)
class TicketServiceConcurrencyTest {
    @Autowired
    private TicketService ticketService;

    @Autowired
    private SupportTicketRepository ticketRepository;

    @Test
    void onlyOneAgentCanClaimSameOpenTicket() throws Exception {
        SupportTicket ticket = ticketService.createTicket("tenant-a", "Late delivery", "Nora", "Order has not arrived", TicketPriority.HIGH);
        UUID ticketId = ticket.getId();
        int workerCount = 4;
        CountDownLatch ready = new CountDownLatch(workerCount);
        CountDownLatch start = new CountDownLatch(1);
        ExecutorService executor = Executors.newFixedThreadPool(workerCount);
        List<Callable<Boolean>> tasks = new ArrayList<>();

        for (int i = 0; i < workerCount; i++) {
            String agentId = "agent-" + i;
            tasks.add(() -> {
                ready.countDown();
                start.await();
                try {
                    ticketService.claimTicket("tenant-a", ticketId, agentId);
                    return true;
                } catch (TicketStateConflictException ex) {
                    return false;
                }
            });
        }

        try {
            List<Future<Boolean>> futures = tasks.stream()
                    .map(executor::submit)
                    .collect(Collectors.toList());
            assertThat(ready.await(5, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            for (Future<Boolean> future : futures) {
                future.get(10, TimeUnit.SECONDS);
            }
            assertThat(futures).allMatch(Future::isDone);
            long successCount = futures.stream().filter(future -> {
                try {
                    return future.get(1, TimeUnit.SECONDS);
                } catch (Exception ex) {
                    throw new IllegalStateException(ex);
                }
            }).count();

            SupportTicket claimed = ticketRepository.findById(ticketId).orElseThrow();
            assertThat(successCount).isEqualTo(1);
            assertThat(claimed.getStatus()).isEqualTo(TicketStatus.IN_PROGRESS);
            assertThat(claimed.getAssignedAgentId()).startsWith("agent-");
        } finally {
            executor.shutdownNow();
        }
    }
}
