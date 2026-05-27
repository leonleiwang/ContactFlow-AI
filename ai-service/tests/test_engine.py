from app.engine import AssistEngine
from app.models import Intent, Route, TicketEvent


def test_high_risk_complaint_goes_to_handoff() -> None:
    engine = AssistEngine()
    result = engine.analyze(
        TicketEvent(
            event_id="event-1",
            ticket_id="ticket-1",
            tenant_id="tenant-a",
            title="我要投诉",
            customer_message="我要找监管投诉你们，物流一直没到",
            priority="HIGH",
        )
    )

    assert result.intent == Intent.COMPLAINT
    assert result.handoff_recommended is True
    assert result.route == Route.HANDOFF
    assert result.confidence < 0.5


def test_rag_answer_requires_tenant_scoped_evidence() -> None:
    engine = AssistEngine()
    result = engine.analyze(
        TicketEvent(
            event_id="event-2",
            ticket_id="ticket-2",
            tenant_id="tenant-a",
            title="退款问题",
            customer_message="我想申请退款 refund policy",
            priority="NORMAL",
        )
    )

    assert result.intent == Intent.REFUND
    assert result.route == Route.RAG
    assert result.citations
    assert result.confidence >= 0.7


def test_no_evidence_does_not_fabricate_policy_answer() -> None:
    engine = AssistEngine()
    result = engine.analyze(
        TicketEvent(
            event_id="event-3",
            ticket_id="ticket-3",
            tenant_id="tenant-b",
            title="退款问题",
            customer_message="我想申请退款 refund policy",
            priority="NORMAL",
        )
    )

    assert result.route == Route.RAG
    assert result.citations == []
    assert result.confidence < 0.5
    assert "没有找到足够依据" in result.suggested_reply


def test_general_question_uses_rule_only_route() -> None:
    engine = AssistEngine()
    result = engine.analyze(
        TicketEvent(
            event_id="event-4",
            ticket_id="ticket-4",
            tenant_id="tenant-a",
            title="咨询",
            customer_message="你好，请问怎么联系人工客服",
            priority="LOW",
        )
    )

    assert result.route == Route.RULE_ONLY
    assert result.estimated_cost_usd == 0.0
