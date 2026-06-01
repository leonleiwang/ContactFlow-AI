package com.contactflow.ticket.integration;

// 展示说明：RabbitMQ 队列构造工具，统一为业务队列挂载死信路由，便于失败重试和问题定位。

import java.util.Map;
import org.springframework.amqp.core.Queue;

final class QueueBuilderFactory {
    private QueueBuilderFactory() {
    }

    // 构建持久化队列并配置 DLQ：消费失败消息会进入指定死信队列而不是丢失。
    static Queue durableWithDlq(String queueName, String deadLetterQueueName) {
        return new Queue(queueName, true, false, false, Map.of(
                "x-dead-letter-exchange", "",
                "x-dead-letter-routing-key", deadLetterQueueName
        ));
    }
}
