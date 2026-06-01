// 展示说明：V0.2 React 三栏坐席台原型，集中展示工单队列、并发抢单状态、AI Assist 和 RAG Evidence Trace 面板。
import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  GitBranch,
  Inbox,
  Layers3,
  Lock,
  MessageSquareText,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  UserCheck
} from "lucide-react";
import "./styles.css";

type TicketStatus = "OPEN" | "IN_PROGRESS" | "WAITING_CUSTOMER" | "RESOLVED" | "CLOSED" | "ESCALATED";
type AiState = "pending" | "completed" | "failed";
type RightPanelTab = "assist" | "trace" | "evals";

type Ticket = {
  id: string;
  title: string;
  customerName: string;
  channel: string;
  message: string;
  status: TicketStatus;
  priority: "LOW" | "NORMAL" | "HIGH" | "URGENT";
  assignedAgentId?: string;
  sla: string;
  aiState: AiState;
  intent: string;
  risk: "low" | "medium" | "high";
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

const initialTickets: Ticket[] = [
  // 演示工单数据：覆盖物流投诉、退款咨询和发票问题，用于展示不同风险与 AI 状态。
  {
    id: "T-1042",
    title: "物流超过承诺时间仍未更新",
    customerName: "林女士",
    channel: "Web Chat",
    message: "我的订单已经超过 7 天没到，物流 48 小时没有任何更新。如果今天不能解决，我要投诉。",
    status: "OPEN",
    priority: "HIGH",
    sla: "38m",
    aiState: "completed",
    intent: "delivery / complaint",
    risk: "high"
  },
  {
    id: "T-1041",
    title: "退款政策咨询",
    customerName: "周先生",
    channel: "Email",
    message: "商品签收后试用了一次，还能不能申请退款？",
    status: "IN_PROGRESS",
    priority: "NORMAL",
    assignedAgentId: "agent-07",
    sla: "2h 12m",
    aiState: "pending",
    intent: "refund",
    risk: "medium"
  },
  {
    id: "T-1040",
    title: "发票信息开错",
    customerName: "陈女士",
    channel: "Enterprise WeChat",
    message: "企业发票抬头写错了，需要重新开。",
    status: "WAITING_CUSTOMER",
    priority: "LOW",
    assignedAgentId: "agent-02",
    sla: "5h 03m",
    aiState: "failed",
    intent: "billing",
    risk: "low"
  }
];

const traceScenarios: TraceScenario[] = [
  // RAG Evidence Trace 手工场景：覆盖有证据、高风险转人工和无充分证据 fallback 三类演示。
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

function App() {
  // 坐席台主组件：组织左侧队列、中间会话工作区和右侧 Copilot / Trace / Evals 面板。
  const [tickets, setTickets] = useState<Ticket[]>(initialTickets);
  const [selectedId, setSelectedId] = useState("T-1042");
  const [rightTab, setRightTab] = useState<RightPanelTab>("assist");
  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0];

  const queueStats = useMemo(() => {
    // 队列统计：模拟 Redis 队列计数缓存提供的 open/active/risk 概览。
    return {
      open: tickets.filter((ticket) => ticket.status === "OPEN").length,
      active: tickets.filter((ticket) => ticket.status === "IN_PROGRESS").length,
      risk: tickets.filter((ticket) => ticket.risk === "high").length
    };
  }, [tickets]);

  function claimTicket() {
    // 抢单交互：演示 OPEN 工单领取成功，以及非 OPEN 工单由服务端条件更新返回冲突。
    setTickets((current) =>
      current.map((ticket) => {
        if (ticket.id !== selected.id) return ticket;
        if (ticket.status !== "OPEN") {
          return {
            ...ticket,
            conflict: `工单当前为 ${ticket.status}，已经不能领取。数据库条件更新返回 0 行，前端展示冲突而不是覆盖状态。`
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
    // 冲突模拟：把当前工单标记为已被其他坐席领取，展示并发抢单失败提示。
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
    // 状态流转交互：模拟后端状态机把工单推进到等待客户、已解决、升级或关闭。
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
      <aside className="nav-rail">
        <div className="brand-block">
          <div className="brand-mark">CF</div>
          <div>
            <div className="brand-title">ContactFlow AI</div>
            <div className="brand-subtitle">Agent Workspace</div>
          </div>
        </div>

        <nav className="rail-menu" aria-label="Workspace navigation">
          <button className="is-active"><Inbox size={17} />Inbox</button>
          <button><Bot size={17} />Copilot</button>
          <button><Activity size={17} />Evaluations</button>
          <button><ShieldCheck size={17} />Governance</button>
        </nav>

        <section className="queue-summary" aria-label="队列概览">
          <Metric label="Open" value={queueStats.open} />
          <Metric label="Active" value={queueStats.active} />
          <Metric label="Risk" value={queueStats.risk} />
        </section>
      </aside>

      <section className="inbox-pane">
        <div className="search-box">
          <Search size={16} />
          <input aria-label="搜索工单" placeholder="搜索工单、客户、意图或证据" />
        </div>

        <div className="queue-filter">
          <button className="is-active">All</button>
          <button>Mine</button>
          <button>Escalated</button>
        </div>

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
              <div className="ticket-preview">{ticket.message}</div>
              <div className="row-footer">
                <span>{ticket.customerName} · {ticket.channel}</span>
                <span className={ticket.risk === "high" ? "risk-text" : ""}>SLA {ticket.sla}</span>
              </div>
            </button>
          ))}
        </nav>
      </section>

      <section className="workspace-pane">
        <header className="workspace-topbar">
          <div>
            <div className="eyebrow">当前工单 · {selected.id}</div>
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

        <div className="workspace-grid">
          <section className="conversation-panel">
            <div className="section-heading">
              <MessageSquareText size={18} />
              <span>客户诉求</span>
            </div>
            <div className="message-card">
              <div className="message-meta">
                <strong>{selected.customerName}</strong>
                <span>{selected.priority} · {selected.channel}</span>
              </div>
              <p>{selected.message}</p>
            </div>

            <div className="reply-composer">
              <input aria-label="回复客户" placeholder="输入给客户的回复，或采纳 Copilot 建议" />
              <button title="发送回复"><Send size={17} /></button>
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

      <aside className="copilot-pane">
        <div className="copilot-tabs" role="tablist" aria-label="AI Copilot panels">
          <button className={rightTab === "assist" ? "is-active" : ""} onClick={() => setRightTab("assist")}>Assist</button>
          <button className={rightTab === "trace" ? "is-active" : ""} onClick={() => setRightTab("trace")}>Trace</button>
          <button className={rightTab === "evals" ? "is-active" : ""} onClick={() => setRightTab("evals")}>Evals</button>
        </div>

        {rightTab === "assist" ? <AiAssist ticket={selected} /> : null}
        {rightTab === "trace" ? <EvidenceTracePanel /> : null}
        {rightTab === "evals" ? <EvalPanel /> : null}
      </aside>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  // 队列指标卡：展示 Open、Active、Risk 三个关键运营数字。
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ status }: { status: TicketStatus }) {
  // 状态徽标：让不同工单状态在列表中可快速扫读。
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status}</span>;
}

function AiAssist({ ticket }: { ticket: Ticket }) {
  // AI Assist 面板：按 pending/failed/completed 展示异步分析状态、摘要、风险和建议回复。
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
      <section className="assist-hero">
        <div>
          <div className="eyebrow">Agent Copilot</div>
          <h2>建议先安抚客户，再核对物流轨迹</h2>
        </div>
        <Sparkles size={20} />
      </section>

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
          <dd>{ticket.intent}</dd>
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
        <div className="citation-box">引用：物流延迟处理 SOP / score 0.78</div>
      </div>
    </div>
  );
}

function EvidenceTracePanel() {
  // RAG Evidence Trace 面板：展示 intent、fallback、metrics、citations 和 trace steps。
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

function EvalPanel() {
  // 评估面板：展示批量评估报告中的核心指标，呼应后端 latest_report.json。
  const rows = [
    ["Context Recall", "0.58", "retrieval gap"],
    ["Citation Coverage", "1.00", "stable"],
    ["Faithfulness", "0.67", "needs rerank"],
    ["Tenant Leak Count", "0", "isolated"],
    ["Handoff Accuracy", "0.88", "good"]
  ];

  return (
    <section className="eval-panel">
      <div className="trace-heading">
        <div>
          <div className="eyebrow">LangSmith-style review</div>
          <h2>Evaluation runs</h2>
        </div>
        <ArrowUpRight size={18} />
      </div>
      <div className="eval-table">
        {rows.map(([metric, value, note]) => (
          <div className="eval-row" key={metric}>
            <span>{metric}</span>
            <strong>{value}</strong>
            <em>{note}</em>
          </div>
        ))}
      </div>
    </section>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  // Trace 小指标：压缩展示召回、引用、忠实度和租户泄漏计数。
  return (
    <div className="mini-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
