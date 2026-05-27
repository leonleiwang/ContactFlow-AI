package com.contactflow.ticket.api;

import com.contactflow.ticket.domain.TicketNotFoundException;
import com.contactflow.ticket.domain.TicketStateConflictException;
import java.time.Instant;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    public record ApiError(String code, String message, Instant timestamp) {
    }

    @ExceptionHandler(TicketNotFoundException.class)
    ResponseEntity<ApiError> handleNotFound(TicketNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ApiError("TICKET_NOT_FOUND", ex.getMessage(), Instant.now()));
    }

    @ExceptionHandler(TicketStateConflictException.class)
    ResponseEntity<ApiError> handleConflict(TicketStateConflictException ex) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ApiError("TICKET_STATE_CONFLICT", ex.getMessage(), Instant.now()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiError> handleValidation(MethodArgumentNotValidException ex) {
        return ResponseEntity.badRequest().body(new ApiError("VALIDATION_FAILED", "Request body validation failed", Instant.now()));
    }
}
