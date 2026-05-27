package com.contactflow.ticket.integration;

import java.util.Map;
import org.springframework.amqp.core.Queue;

final class QueueBuilderFactory {
    private QueueBuilderFactory() {
    }

    static Queue durableWithDlq(String queueName, String deadLetterQueueName) {
        return new Queue(queueName, true, false, false, Map.of(
                "x-dead-letter-exchange", "",
                "x-dead-letter-routing-key", deadLetterQueueName
        ));
    }
}
