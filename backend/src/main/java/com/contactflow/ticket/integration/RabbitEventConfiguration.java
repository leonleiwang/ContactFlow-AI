package com.contactflow.ticket.integration;

// 展示说明：RabbitMQ 基础设施配置，声明 ticket event exchange、AI Assist 队列、完成队列、死信队列和 JSON 消息转换。

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(RabbitEventProperties.class)
@ConditionalOnProperty(prefix = "contactflow.events.rabbit", name = "enabled", havingValue = "true")
// 条件化 MQ 配置：只有开启 contactflow.events.rabbit.enabled 时才创建真实 RabbitMQ bean。
public class RabbitEventConfiguration {
    @Bean
    // 工单事件交换机：所有 ticket.created/status_changed/ai.assist.completed 事件的主题路由入口。
    TopicExchange ticketEventsExchange(RabbitEventProperties properties) {
        return new TopicExchange(properties.getExchange(), true, false);
    }

    @Bean
    // AI Assist 请求队列：接收后端发布的工单创建事件，供 AI Service 消费生成建议。
    Queue aiAssistQueue(RabbitEventProperties properties) {
        return QueueBuilderFactory.durableWithDlq(properties.getAiAssistQueue(), properties.getAiAssistDlq());
    }

    @Bean
    // AI Assist 请求死信队列：保留消费失败消息，支持失败排查和重放。
    Queue aiAssistDeadLetterQueue(RabbitEventProperties properties) {
        return new Queue(properties.getAiAssistDlq(), true);
    }

    @Bean
    // AI Assist 完成队列：接收 AI Service 回写的建议结果，触发后端幂等落库。
    Queue aiAssistCompletedQueue(RabbitEventProperties properties) {
        return QueueBuilderFactory.durableWithDlq(properties.getAiAssistCompletedQueue(), properties.getAiAssistCompletedDlq());
    }

    @Bean
    // AI Assist 完成死信队列：隔离回写失败消息，避免阻塞正常消费。
    Queue aiAssistCompletedDeadLetterQueue(RabbitEventProperties properties) {
        return new Queue(properties.getAiAssistCompletedDlq(), true);
    }

    @Bean
    // 绑定 AI Assist 请求路由键：把创建/变更事件路由到 AI 请求队列。
    Binding aiAssistBinding(Queue aiAssistQueue, TopicExchange ticketEventsExchange, RabbitEventProperties properties) {
        return BindingBuilder.bind(aiAssistQueue).to(ticketEventsExchange).with(properties.getAiAssistRoutingKey());
    }

    @Bean
    // 绑定 AI Assist 完成路由键：把 ai.assist.completed 路由到完成队列。
    Binding aiAssistCompletedBinding(Queue aiAssistCompletedQueue, TopicExchange ticketEventsExchange, RabbitEventProperties properties) {
        return BindingBuilder.bind(aiAssistCompletedQueue).to(ticketEventsExchange).with(properties.getAiAssistCompletedRoutingKey());
    }

    @Bean
    // JSON 消息转换器：确保 Java Map envelope 与 RabbitMQ 消息体之间自动序列化。
    MessageConverter rabbitJsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }
}
