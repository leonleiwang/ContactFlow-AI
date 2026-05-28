import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  GitBranch,
  Layers3,
  Lock,
  MessageSquareText,
  Search,
  ShieldCheck,
  UserCheck
} from "lucide-react";
import "./styles.css";

type TicketStatus = "OPEN" | "IN_PROGRESS" | "WAITING_CUSTOMER" | "RESOLVED" | "CLOSED" | "ESCALATED";
type AiState = "pending" | "completed" | "failed";

type Ticket = {
  id: string;
  title: string;
  customerName: string;
  message: string;
  status: TicketStatus;
  priority: "LOW" | "NORMAL" | "HIGH" | "URGENT";
  assignedAgentId?: string;
  sla: string;
  aiState: AiState;
  conflict?: string;
};

type TraceScenario = {
  id: string;
  label: string;
  question: string;
  intent: string;
  strategy: string;
  shouldHandoff: boolean;
  fallbackReason: string | null;
  answer: string;
  citations: Array<{
    docId: string;
    title: string;
    score: number;
    tenant: string;
  }>;
  metrics: {
    contextRecall: number;
    citationCoverage: number;
    faithfulness: number;
    hallucinationRisk: number;
    tenantLeakCount: number;
    handoffAccuracy: number;
    retrievalLatencyMs: number;
  };
  traceSteps: string[];
};

const traceScenarios: TraceScenario[] = [
  {
    id: "refund-quality",
    label: "退款质检",
    question: "我签收 8 天了，耳机有质量问题还能退吗？",
    intent: "refund",
    strategy: "deep hybrid",
    shouldHandoff: false,
    fallbackReason: null,
    answer: "命中保修与退款政策，回答保留主管审核边界，不直接承诺退款。",
    citations: [
      { docId: "tenant-a/warranty_policy.md", title: "与退款关系", score: 1.1162, tenant: "tenant-a" },
      { docId: "tenant-a/refund_policy.md", title: "标准规则", score: 1.0772, tenant: "tenant-a" }
    ],
    metrics: {
      contextRecall: 0.58,
      citationCoverage: 1,
      faithfulness: 0.67,
      hallucinationRisk: 0.33,
      tenantLeakCount: 0,
      handoffAccuracy: 0.88,
      retrievalLatencyMs: 3
    },
    traceSteps: ["UTF-8 query accepted", "intent=refund", "BM25 + vector recall", "rerank top evidence", "answer with citations"]
  },
  {
    id: "high-risk",
    label: "高风险",
    question: "你们必须赔我 5000，不然我起诉。",
    intent: "complaint",
    strategy: "risk-first deep",
    shouldHandoff: true,
    fallbackReason: "high_risk_handoff",
    answer: "识别法律与赔偿风险，只给坐席处理建议，不自动承诺赔偿或处理结果。",
    citations: [
      { docId: "tenant-internal/high_risk_complaint_sop.md", title: "高风险识别", score: 0.4753, tenant: "tenant-internal" },
      { docId: "tenant-internal/forbidden_promises.md", title: "禁止表达", score: 0.4229, tenant: "tenant-internal" }
    ],
    metrics: {
      contextRecall: 0.58,
      citationCoverage: 1,
      faithfulness: 0.67,
      hallucinationRisk: 0.33,
      tenantLeakCount: 0,
      handoffAccuracy: 0.88,
      retrievalLatencyMs: 3
    },
    traceSteps: ["risk keywords matched", "intent=complaint", "internal SOP recall", "handoff required", "no compensation promise"]
  },
  {
    id: "no-evidence",
    label: "无证据",
    question: "你们能不能给我终身免费会员？",
    intent: "billing",
    strategy: "fallback guarded",
    shouldHandoff: true,
    fallbackReason: "no_sufficient_evidence",
    answer: "知识库没有足够证据支持确定回答，进入人工核查和知识库补充池。",
    citations: [
      { docId: "tenant-internal/handoff_routing_sop.md", title: "转人工条件", score: 0.4259, tenant: "tenant-internal" },
      { docId: "tenant-internal/agent_assist_trace_sop.md", title: "追溯要求", score: 0.3761, tenant: "tenant-internal" }
    ],
    metrics: {
      contextRecall: 0.58,
      citationCoverage: 1,
      faithfulness: 0.67,
      hallucinationRisk: 0.33,
      tenantLeakCount: 0,
      handoffAccuracy: 0.88,
      retrievalLatencyMs: 3
    },
    traceSteps: ["unsupported entitlement detected", "weak business evidence removed", "fallback SOP retained", "handoff suggested", "knowledge gap logged"]
  }
];

const initialTickets: Ticket[] = [
  {
    id: "T-1042",
    title: "物流超过承诺时间仍未更新",
    customerName: "林女士",
    message: "我的订单已经超过 7 天没到，物流 48 小时没有任何更新。如果今天不能解决，我要投诉。",
    status: "OPEN",
    priority: "HIGH",
    sla: "38m",
    aiState: "completed"
  },
  {
    id: "T-1041",
    title: "退款政策咨询",
    customerName: "周先生",
    message: "商品签收后试用了一次，还能不能申请退款？",
    status: "IN_PROGRESS",
    priority: "NORMAL",
    assignedAgentId: "agent-07",
    sla: "2h 12m",
    aiState: "pending"
  },
  {
    id: "T-1040",
    title: "发票信息开错",
    customerName: "陈女士",
    message: "企业发票抬头写错了，需要重新开。",
    status: "WAITING_CUSTOMER",
    priority: "LOW",
    assignedAgentId: "agent-02",
    sla: "5h 03m",
    aiState: "failed"
  }
];

function App() {
  const [tickets, setTickets] = useState<Ticket[]>(initialTickets);
  const [selectedId, setSelectedId] = useState("T-1042");
  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0];

  const queueStats = useMemo(() => {
    return {
      open: tickets.filter((ticket) => ticket.status === "OPEN").length,
      active: tickets.filter((ticket) => ticket.status === "IN_PROGRESS").length,
      risk: tickets.filter((ticket) => ticket.priority === "HIGH" || ticket.priority === "URGENT").length
    };
  }, [tickets]);

  function claimTicket() {
    setTickets((current) =>
      current.map((ticket) => {
        if (ticket.id !== selected.id) return ticket;
        if (ticket.status !== "OPEN") {
          return {
            ...ticket,
            conflict: `工单当前为 ${ticket.status}，已不能领取。数据库条件更新会返回 0 行，前端展示冲突而不是覆盖状态。`
          };
        }
        return {
          ...ticket,
          status: "IN_PROGRESS",
          assignedAgentId: "agent-me",
          conflict: undefined
        };
      })
    );
  }

  function simulateClaimConflict() {
    setTickets((current) =>
      current.map((ticket) =>
        ticket.id === selected.id
          ? {
              ...ticket,
              status: "IN_PROGRESS",
              assignedAgentId: "agent-11",
              conflict: "领取失败：该工单已被 agent-11 领取。服务端以 MySQL 条件更新结果为准。"
            }
          : ticket
      )
    );
  }

  function transition(target: TicketStatus) {
    setTickets((current) =>
      current.map((ticket) =>
        ticket.id === selected.id
          ? {
              ...ticket,
              status: target,
              conflict: undefined
            }
          : ticket
      )
    );
  }

  return (
    <main className="app-shell">
      <aside className="queue-rail">
        <div className="brand-block">
          <div className="brand-mark">CF</div>
          <div>
            <div className="brand-title">ContactFlow AI</div>
            <div className="brand-subtitle">客服工单坐席台</div>
          </div>
        </div>

        <div className="search-box">
          <Search size={16} />
          <input aria-label="搜索工单" placeholder="搜索工单、客户、意图" />
        </div>

        <section className="metric-grid" aria-label="队列统计">
          <Metric label="待领取" value={queueStats.open} tone="blue" />
          <Metric label="处理中" value={queueStats.active} tone="green" />
          <Metric label="高风险" value={queueStats.risk} tone="amber" />
        </section>

        <nav className="ticket-list" aria-label="工单队列">
          {tickets.map((ticket) => (
            <button
              className={`ticket-row ${ticket.id === selected.id ? "is-selected" : ""}`}
              key={ticket.id}
              onClick={() => setSelectedId(ticket.id)}
            >
              <div className="row-topline">
                <span className="ticket-id">{ticket.id}</span>
                <StatusBadge status={ticket.status} />
              </div>
              <div className="ticket-title">{ticket.title}</div>
              <div className="row-footer">
                <span>{ticket.customerName}</span>
                <span className={ticket.priority === "HIGH" || ticket.priority === "URGENT" ? "sla-hot" : ""}>SLA {ticket.sla}</span>
              </div>
            </button>
          ))}
        </nav>
      </aside>

      <section className="ticket-pane">
        <header className="workspace-topbar">
          <div>
            <div className="eyebrow">当前工单</div>
            <h1>{selected.title}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" title="查看审计日志">
              <FileText size={18} />
            </button>
            <button className="primary-action" onClick={claimTicket} disabled={selected.status !== "OPEN"}>
              <UserCheck size={17} />
              领取
            </button>
            <button className="ghost-action" onClick={simulateClaimConflict}>
              模拟抢单冲突
            </button>
          </div>
        </header>

        {selected.conflict ? (
          <div className="conflict-banner" role="alert">
            <Lock size={17} />
            <span>{selected.conflict}</span>
          </div>
        ) : null}

        <div className="detail-grid">
          <section className="conversation-panel">
            <div className="section-heading">
              <MessageSquareText size={18} />
              <span>客户诉求</span>
            </div>
            <div className="message-card">
              <div className="message-meta">
                <strong>{selected.customerName}</strong>
                <span>{selected.priority}</span>
              </div>
              <p>{selected.message}</p>
            </div>
          </section>

          <section className="workflow-panel">
            <div className="section-heading">
              <Clock3 size={18} />
              <span>状态流转</span>
            </div>
            <div className="status-strip">
              {["OPEN", "IN_PROGRESS", "WAITING_CUSTOMER", "RESOLVED", "CLOSED"].map((status) => (
                <div className={`step ${selected.status === status ? "is-current" : ""}`} key={status}>
                  {status}
                </div>
              ))}
            </div>
            <div className="workflow-actions">
              <button onClick={() => transition("WAITING_CUSTOMER")} disabled={selected.status !== "IN_PROGRESS"}>
                等待客户
              </button>
              <button onClick={() => transition("RESOLVED")} disabled={selected.status !== "IN_PROGRESS" && selected.status !== "WAITING_CUSTOMER"}>
                标记解决
              </button>
              <button onClick={() => transition("ESCALATED")} disabled={selected.status === "CLOSED"}>
                升级
              </button>
              <button onClick={() => transition("CLOSED")} disabled={selected.status !== "RESOLVED"}>
                关闭
              </button>
            </div>
          </section>
        </div>
      </section>

      <aside className="assist-pane">
        <div className="section-heading">
          <Bot size={18} />
          <span>AI Assist</span>
        </div>
        <AiAssist ticket={selected} />
        <EvidenceTracePanel />
      </aside>
    </main>
  );
}

function EvidenceTracePanel() {
  const [activeId, setActiveId] = useState(traceScenarios[0].id);
  const active = traceScenarios.find((scenario) => scenario.id === activeId) ?? traceScenarios[0];

  return (
    <section className="trace-panel" aria-label="RAG Evidence Trace">
      <div className="trace-heading">
        <div>
          <div className="eyebrow">RAG Evidence Trace</div>
          <h2>证据链路</h2>
        </div>
        <ShieldCheck size={18} />
      </div>

      <div className="trace-tabs" role="tablist" aria-label="手工验证场景">
        {traceScenarios.map((scenario) => (
          <button
            key={scenario.id}
            className={scenario.id === active.id ? "is-active" : ""}
            onClick={() => setActiveId(scenario.id)}
            type="button"
          >
            {scenario.label}
          </button>
        ))}
      </div>

      <div className="trace-question">
        <span>Query</span>
        <p>{active.question}</p>
      </div>

      <dl className="trace-kv">
        <dt>Intent</dt>
        <dd>{active.intent}</dd>
        <dt>Strategy</dt>
        <dd>{active.strategy}</dd>
        <dt>Handoff</dt>
        <dd className={active.shouldHandoff ? "risk-text" : ""}>{active.shouldHandoff ? "required" : "not required"}</dd>
        <dt>Fallback</dt>
        <dd>{active.fallbackReason ?? "none"}</dd>
      </dl>

      <div className="trace-answer">{active.answer}</div>

      <div className="metric-row" aria-label="RAG 批量评估指标">
        <MiniMetric label="Recall" value={active.metrics.contextRecall.toFixed(2)} />
        <MiniMetric label="Cite" value={active.metrics.citationCoverage.toFixed(2)} />
        <MiniMetric label="Faith" value={active.metrics.faithfulness.toFixed(2)} />
        <MiniMetric label="Leak" value={String(active.metrics.tenantLeakCount)} />
      </div>

      <div className="trace-subsection">
        <div className="trace-subtitle">
          <Layers3 size={15} />
          <span>Citations</span>
        </div>
        <div className="citation-list">
          {active.citations.map((citation) => (
            <div className="citation-row" key={`${active.id}-${citation.docId}-${citation.title}`}>
              <div>
                <strong>{citation.title}</strong>
                <span>{citation.docId}</span>
              </div>
              <code>{citation.score.toFixed(4)}</code>
            </div>
          ))}
        </div>
      </div>

      <div className="trace-subsection">
        <div className="trace-subtitle">
          <GitBranch size={15} />
          <span>Trace</span>
        </div>
        <ol className="trace-steps">
          {active.traceSteps.map((step) => (
            <li key={`${active.id}-${step}`}>{step}</li>
          ))}
        </ol>
      </div>

      <div className="trace-footnote">
        <Activity size={14} />
        <span>120 cases · latency {active.metrics.retrievalLatencyMs}ms · handoff accuracy {active.metrics.handoffAccuracy.toFixed(2)}</span>
      </div>
    </section>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="mini-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: "blue" | "green" | "amber" }) {
  return (
    <div className={`metric-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status}</span>;
}

function AiAssist({ ticket }: { ticket: Ticket }) {
  if (ticket.aiState === "pending") {
    return (
      <div className="assist-state">
        <Clock3 size={20} />
        <strong>AI 分析中</strong>
        <p>工单创建已经完成，摘要和建议回复通过异步事件生成，不阻塞坐席处理。</p>
      </div>
    );
  }

  if (ticket.aiState === "failed") {
    return (
      <div className="assist-state error">
        <AlertTriangle size={20} />
        <strong>AI Assist 生成失败</strong>
        <p>主工单流程保持可用。坐席可以继续处理，后台事件稍后重试。</p>
        <button>重试分析</button>
      </div>
    );
  }

  return (
    <div className="assist-stack">
      <div className="assist-card">
        <div className="assist-card-title">
          <CheckCircle2 size={17} />
          <span>摘要</span>
        </div>
        <p>客户反馈物流超过承诺时间且存在投诉风险，需要优先核对物流轨迹并给出明确下一步。</p>
      </div>

      <div className="assist-card">
        <div className="assist-card-title">
          <AlertTriangle size={17} />
          <span>风险与转人工</span>
        </div>
        <dl className="assist-kv">
          <dt>意图</dt>
          <dd>delivery / complaint</dd>
          <dt>SLA</dt>
          <dd className="risk-text">MEDIUM</dd>
          <dt>建议</dt>
          <dd>先安抚客户，再查询物流轨迹；若 48 小时无更新，升级主管。</dd>
        </dl>
      </div>

      <div className="assist-card">
        <div className="assist-card-title">
          <FileText size={17} />
          <span>建议回复</span>
        </div>
        <p>您好，我们已收到您的反馈。我会先核对物流轨迹，如果超过承诺时间仍无更新，将为您提交升级处理。</p>
        <div className="citation-box">引用：物流延迟处理 / score 0.78</div>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
