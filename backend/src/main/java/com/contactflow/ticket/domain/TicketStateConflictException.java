package com.contactflow.ticket.domain;

public class TicketStateConflictException extends RuntimeException {
    public TicketStateConflictException(String message) {
        super(message);
    }
}
