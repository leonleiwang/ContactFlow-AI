package com.contactflow.ticket.integration;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(RabbitEventProperties.class)
@ConditionalOnProperty(prefix = "contactflow.events.rabbit", name = "enabled", havingValue = "true")
public class RabbitEventConfiguration {
    @Bean
    TopicExchange ticketEventsExchange(RabbitEventProperties properties) {
        return new TopicExchange(properties.getExchange(), true, false);
    }

    @Bean
    Queue aiAssistQueue(RabbitEventProperties properties) {
        return QueueBuilderFactory.durableWithDlq(properties.getAiAssistQueue(), properties.getAiAssistDlq());
    }

    @Bean
    Queue aiAssistDeadLetterQueue(RabbitEventProperties properties) {
        return new Queue(properties.getAiAssistDlq(), true);
    }

    @Bean
    Binding aiAssistBinding(Queue aiAssistQueue, TopicExchange ticketEventsExchange, RabbitEventProperties properties) {
        return BindingBuilder.bind(aiAssistQueue).to(ticketEventsExchange).with(properties.getAiAssistRoutingKey());
    }
}
