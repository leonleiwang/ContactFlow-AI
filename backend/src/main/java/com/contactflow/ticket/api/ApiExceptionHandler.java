package com.contactflow.ticket.api;

// 展示说明：统一 REST 异常响应格式，把找不到工单、状态冲突和参数校验失败转换成稳定错误码。
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
    // API 错误响应：统一 code、message、timestamp，便于前端提示和日志检索。
    public record ApiError(String code, String message, Instant timestamp) {
    }

    // 404：租户内找不到目标工单时返回明确错误码。
    @ExceptionHandler(TicketNotFoundException.class)
    ResponseEntity<ApiError> handleNotFound(TicketNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ApiError("TICKET_NOT_FOUND", ex.getMessage(), Instant.now()));
    }

    // 409：抢单冲突或非法状态流转时返回业务冲突，而不是泛化成 500。
    @ExceptionHandler(TicketStateConflictException.class)
    ResponseEntity<ApiError> handleConflict(TicketStateConflictException ex) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ApiError("TICKET_STATE_CONFLICT", ex.getMessage(), Instant.now()));
    }

    // 400：请求体字段缺失、枚举非法、长度越界等入参问题统一归类为校验失败。
    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiError> handleValidation(MethodArgumentNotValidException ex) {
        return ResponseEntity.badRequest().body(new ApiError("VALIDATION_FAILED", "Request body validation failed", Instant.now()));
    }
}
