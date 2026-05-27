import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { AlertTriangle, Bot, CheckCircle2, Clock3, FileText, Lock, MessageSquareText, Search, UserCheck } from "lucide-react";
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
      </aside>
    </main>
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
