package com.contactflow.ticket.integration;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "contactflow.events.rabbit")
public class RabbitEventProperties {
    private boolean enabled;
    private String exchange = "contactflow.ticket.events";
    private String aiAssistRoutingKey = "ticket.created";
    private String aiAssistQueue = "ai.assist.request";
    private String aiAssistDlq = "ai.assist.dlq";

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getExchange() {
        return exchange;
    }

    public void setExchange(String exchange) {
        this.exchange = exchange;
    }

    public String getAiAssistRoutingKey() {
        return aiAssistRoutingKey;
    }

    public void setAiAssistRoutingKey(String aiAssistRoutingKey) {
        this.aiAssistRoutingKey = aiAssistRoutingKey;
    }

    public String getAiAssistQueue() {
        return aiAssistQueue;
    }

    public void setAiAssistQueue(String aiAssistQueue) {
        this.aiAssistQueue = aiAssistQueue;
    }

    public String getAiAssistDlq() {
        return aiAssistDlq;
    }

    public void setAiAssistDlq(String aiAssistDlq) {
        this.aiAssistDlq = aiAssistDlq;
    }
}
