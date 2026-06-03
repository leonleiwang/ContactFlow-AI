// 展示说明：V0.3 演示版坐席台，保留 20 条本地 mock 工单作为 LLM/RAG 不可用时的前端降级展示层。
import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Clock3,
  CopyCheck,
  FileText,
  GitBranch,
  Inbox,
  Layers3,
  Lock,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  UserCheck
} from "lucide-react";
import "./styles.css";

type TicketStatus = "OPEN" | "IN_PROGRESS" | "WAITING_CUSTOMER" | "RESOLVED" | "CLOSED" | "ESCALATED" | "CANCELLED";
type TicketPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";
type AiState = "pending" | "completed" | "degraded" | "failed";
type RightPanelTab = "assist" | "trace" | "evals";
type QueueFilter = "all" | "mine" | "escalated";

type AssistData = {
  state: AiState;
  headline: string;
  summary: string;
  intent: string;
  slaRisk: "LOW" | "MEDIUM" | "HIGH";
  recommendation: string;
  suggestedReply: string;
  confidence: number;
  generationMode: "llm" | "template_fallback" | "mock_fallback" | "pending" | "failed";
  modelName?: string;
  degradedReason?: string;
  citations: Array<{
    docId: string;
    title: string;
    score: number;
  }>;
};

type ConversationReply = {
  id: string;
  text: string;
  createdBy: string;
};

type Ticket = {
  id: string;
  title: string;
  customerName: string;
  channel: string;
  message: string;
  status: TicketStatus;
  priority: TicketPriority;
  assignedAgentId?: string;
  sla: string;
  intent: string;
  risk: "low" | "medium" | "high";
  tenant: "tenant-a" | "tenant-b" | "tenant-internal";
  category: string;
  assist: AssistData;
  conflict?: string;
  replies?: ConversationReply[];
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

const fallbackCitation = { docId: "tenant-internal/agent_assist_trace_sop.md", title: "AI Assist 降级与追溯要求", score: 0.81 };

const initialTickets: Ticket[] = [
  ticket("T-1042", "物流超过承诺时间仍未更新", "林女士", "Web Chat", "我的订单已经超过 7 天没到，物流 48 小时没有任何更新。如果今天不能解决，我要投诉。", "OPEN", "HIGH", "38m", "delivery / complaint", "high", "tenant-a", "物流投诉", "completed", "建议先安抚客户，再核对物流轨迹", "客户反馈物流超过承诺时间且存在投诉风险，需要优先核对物流轨迹并给出明确下一步。", "先安抚客户并确认订单号；如 48 小时无更新，升级主管并引用物流延迟 SOP。", "您好，我们已经收到您的反馈。我会先为您核对物流轨迹；如果确认超过承诺时间且仍无更新，将为您提交升级处理。", "qwen3-max", undefined, [{ docId: "tenant-a/delivery_delay_sop.md", title: "物流延迟处理 SOP", score: 0.92 }]),
  ticket("T-1041", "退款政策咨询", "周先生", "Email", "商品签收后试用了一次，还能不能申请退款？", "IN_PROGRESS", "NORMAL", "2h 12m", "refund", "medium", "tenant-a", "退款售后", "pending", "AI 正在分析退款条件", "工单已创建，等待异步 AI Assist 生成摘要和建议回复。", "处理中，不阻塞坐席继续处理工单。", "", undefined, undefined, []),
  ticket("T-1040", "发票信息开错", "陈女士", "Enterprise WeChat", "企业发票抬头写错了，需要重新开。", "WAITING_CUSTOMER", "LOW", "5h 03m", "billing", "low", "tenant-a", "发票账单", "failed", "AI Assist 生成失败", "主工单流程仍可用，坐席可继续处理；后台事件稍后重试。", "请先收集正确抬头、税号和原发票信息。", "您好，请您补充正确的发票抬头、税号和原发票信息，我会帮您核对是否可以重新开具。", undefined, "llm_timeout", [fallbackCitation]),
  ticket("T-1039", "跨境包裹清关税费疑问", "王先生", "WhatsApp", "为什么这次跨境包裹还要补交税费？之前没有收过。", "OPEN", "NORMAL", "1h 44m", "billing / tax", "medium", "tenant-b", "跨境税费", "degraded", "使用知识库模板降级回复", "LLM 未接通，已基于跨境税费政策生成坐席兜底建议。", "解释税费由清关政策和申报规则决定，不承诺减免。", "您好，跨境订单可能因目的地清关政策、商品类别和申报金额产生税费。建议您提供订单号，我会帮您核对税费来源。", undefined, "missing_api_key", [{ docId: "tenant-b/tax_duty_policy.md", title: "跨境税费政策", score: 0.86 }]),
  ticket("T-1038", "会员订阅重复扣费", "赵女士", "App", "我这个月会员被扣了两次，麻烦查一下。", "OPEN", "HIGH", "26m", "billing", "medium", "tenant-b", "订阅账单", "completed", "建议核对扣费流水和订阅周期", "客户疑似重复扣费，需要核对支付流水、订阅周期和退款规则。", "收集支付时间、金额、支付渠道和订单号，确认是否为续费周期重叠。", "您好，我先为您核对订阅扣费记录。请您提供两笔扣费的时间、金额和支付渠道，确认重复后会按订阅账单规则处理。", "qwen3-max", undefined, [{ docId: "tenant-b/subscription_billing_policy.md", title: "订阅账单处理规则", score: 0.89 }]),
  ticket("T-1037", "VIP 投诉要求赔偿", "孙先生", "Phone", "你们必须赔我 5000，不然我找媒体曝光。", "ESCALATED", "URGENT", "12m", "complaint", "high", "tenant-internal", "高风险投诉", "completed", "高风险投诉必须转人工", "识别到赔偿、媒体曝光和高风险投诉，不应自动承诺处理结果。", "立即升级主管或法务协同；只做安抚、事实收集和升级说明。", "非常抱歉给您带来不好的体验。我会立即记录您的诉求和相关证据，并提交主管专人跟进。当前我不能直接承诺赔偿结果。", "qwen3-max", undefined, [{ docId: "tenant-internal/high_risk_complaint_sop.md", title: "高风险投诉 SOP", score: 0.95 }]),
  ticket("T-1036", "预售尾款支付失败", "何女士", "Mini Program", "预售尾款一直支付失败，页面提示库存异常。", "OPEN", "NORMAL", "3h 02m", "preorder", "medium", "tenant-a", "预售订单", "degraded", "使用规则模板处理预售异常", "模型不可用时仍可依据预售政策给坐席建议。", "先确认预售订单状态、尾款时间窗和库存锁定状态。", "您好，请您提供预售订单号。我会先核对尾款支付时间窗和库存锁定状态，再为您确认下一步处理方式。", undefined, "llm_disabled", [{ docId: "tenant-a/preorder_policy.md", title: "预售订单政策", score: 0.78 }]),
  ticket("T-1035", "签收后商品破损", "刘女士", "Web Chat", "刚签收的杯子碎了，包装也有破损。", "IN_PROGRESS", "HIGH", "49m", "warranty", "medium", "tenant-b", "破损售后", "completed", "建议收集照片并按破损 SOP 处理", "签收后发现破损，需要收集外包装和商品照片，判断补发、退款或人工审核。", "要求客户上传外包装、面单和破损照片，并保留商品。", "您好，很抱歉出现破损。请您上传外包装、面单和商品破损照片，并暂时保留商品，我们会按破损处理规则为您核实。", "qwen3-max", undefined, [{ docId: "tenant-b/damaged_home_goods_sop.md", title: "家居商品破损 SOP", score: 0.88 }]),
  ticket("T-1034", "地址修改请求", "吴先生", "Email", "订单还没发货，能不能改到公司地址？", "OPEN", "LOW", "6h 20m", "delivery", "low", "tenant-b", "地址变更", "completed", "未发货订单可尝试修改地址", "客户请求改地址，需要确认发货状态，未出库前可按地址变更流程处理。", "先核对发货状态，未出库则收集新地址；已出库则提示无法保证拦截。", "您好，我先帮您核对订单是否已出库。如果尚未出库，可以为您提交地址修改；如果已出库，则需要以物流拦截结果为准。", "qwen3-max", undefined, [{ docId: "tenant-b/address_change_policy.md", title: "地址变更政策", score: 0.84 }]),
  ticket("T-1033", "优惠券补偿咨询", "郑女士", "App", "上次延迟发货说补偿优惠券，怎么还没到账？", "WAITING_CUSTOMER", "NORMAL", "4h 40m", "compensation", "medium", "tenant-a", "优惠补偿", "degraded", "降级到补偿政策模板", "可先核对补偿资格和发放批次，不承诺额外补偿。", "核对订单、活动规则和优惠券发放批次。", "您好，我会先核对您的订单是否符合补偿规则以及优惠券发放批次。确认后会给您同步处理结果。", undefined, "rerank_http_error", [{ docId: "tenant-a/coupon_compensation_policy.md", title: "优惠券补偿政策", score: 0.79 }]),
  ticket("T-1032", "换货尺码问题", "罗先生", "Web Chat", "鞋子尺码小了，想换大一码。", "OPEN", "NORMAL", "2h 58m", "exchange", "low", "tenant-a", "换货", "completed", "建议确认库存和换货条件", "客户请求尺码换货，需要确认商品状态、库存和换货时效。", "确认未影响二次销售后检查库存，符合条件可提交换货。", "您好，请确认商品未使用且包装配件完整。我会帮您查询大一码库存，符合条件后可为您提交换货申请。", "qwen3-max", undefined, [{ docId: "tenant-a/exchange_policy.md", title: "换货政策", score: 0.83 }]),
  ticket("T-1031", "终身免费会员诉求", "马女士", "Email", "你们能不能给我终身免费会员作为补偿？", "OPEN", "NORMAL", "5h 12m", "billing", "medium", "tenant-b", "无证据权益", "degraded", "无充分证据，建议转人工", "知识库没有支持终身免费会员的政策，系统不应自动承诺。", "使用无证据 fallback，转人工核查并沉淀知识缺口。", "当前知识库没有支持该权益的政策依据。建议我先为您登记诉求，并转人工核查是否存在特殊处理方案。", undefined, "no_sufficient_evidence", [{ docId: "tenant-internal/handoff_routing_sop.md", title: "转人工路由 SOP", score: 0.82 }]),
  ticket("T-1030", "海外订单退款周期", "黄先生", "WhatsApp", "跨境订单取消后多久到账？已经等了五天。", "IN_PROGRESS", "NORMAL", "1h 18m", "refund", "medium", "tenant-b", "跨境退款", "completed", "建议说明跨境退款周期和银行处理时间", "客户询问跨境退款到账时间，需要区分平台处理和银行入账。", "说明退款已发起后仍受支付渠道和银行处理周期影响。", "您好，跨境退款在平台处理完成后，还会受到支付渠道和银行入账周期影响。我会帮您核对退款状态和预计到账时间。", "qwen3-max", undefined, [{ docId: "tenant-b/cross_border_refund_policy.md", title: "跨境退款政策", score: 0.87 }]),
  ticket("T-1029", "登录报错无法提交工单", "唐女士", "Web", "登录后台一直报错 500，我没法提交资料。", "OPEN", "HIGH", "33m", "technical", "medium", "tenant-internal", "技术故障", "completed", "建议收集错误信息并升级技术支持", "客户遇到 500 错误，需要收集账号、时间、截图和浏览器信息。", "引导客户提供截图和发生时间，并升级技术支持排查。", "您好，请您提供报错截图、发生时间、账号和浏览器信息。我会同步技术支持排查，同时记录您的业务诉求。", "qwen3-max", undefined, [{ docId: "tenant-internal/handoff_routing_sop.md", title: "技术问题升级路径", score: 0.76 }]),
  ticket("T-1028", "定制商品取消订单", "孟先生", "Phone", "定制柜子还没发货，我想取消订单。", "OPEN", "NORMAL", "7h 09m", "custom_order", "medium", "tenant-b", "定制商品", "degraded", "定制商品需人工审核", "定制商品取消通常存在限制，需要核对生产状态和合同条款。", "收集订单号并确认是否已进入生产，不自动承诺取消。", "您好，定制商品取消需要先核对生产状态和订单条款。请您提供订单号，我会帮您提交人工审核。", undefined, "llm_disabled", [{ docId: "tenant-b/custom_home_goods_policy.md", title: "定制家居政策", score: 0.8 }]),
  ticket("T-1027", "丢件赔付咨询", "高先生", "Web Chat", "物流显示签收了，但我没有收到。", "ESCALATED", "HIGH", "18m", "delivery", "high", "tenant-a", "疑似丢件", "completed", "建议核对签收凭证并升级物流核查", "客户称未收到但物流签收，需要核对签收凭证、地址和物流责任。", "先核对签收凭证和收件地址，必要时升级物流专员。", "您好，我会先为您核对签收凭证、收件地址和物流轨迹。如果确认异常，会升级物流专员进一步处理。", "qwen3-max", undefined, [{ docId: "tenant-a/lost_package_sop.md", title: "丢件处理 SOP", score: 0.91 }]),
  ticket("T-1026", "开发票税号缺失", "梁女士", "Enterprise WeChat", "公司财务说税号没填，发票还能补开吗？", "RESOLVED", "LOW", "closed", "billing", "low", "tenant-a", "发票", "completed", "建议确认发票状态和补开条件", "客户需要补开发票税号，应确认原发票状态和企业开票信息。", "收集抬头、税号和订单号，已开票则按重开规则处理。", "您好，请您提供企业抬头、税号和订单号。我会核对原发票状态，并按发票规则确认是否可以补开或重开。", "qwen3-max", undefined, [{ docId: "tenant-a/invoice_policy.md", title: "发票政策", score: 0.85 }]),
  ticket("T-1025", "质检报告索要", "谢先生", "Email", "耳机维修后能不能给我质检报告？", "WAITING_CUSTOMER", "NORMAL", "3h 36m", "warranty", "low", "tenant-a", "保修质检", "completed", "建议说明质检报告获取路径", "客户索要维修后的质检报告，需要确认维修单和报告生成状态。", "收集维修单号并说明报告可用时点。", "您好，请您提供维修单号。我会帮您查询质检报告是否已生成，若已完成会同步获取方式。", "qwen3-max", undefined, [{ docId: "tenant-a/warranty_policy.md", title: "保修与质检政策", score: 0.82 }]),
  ticket("T-1024", "客户要求主管回电", "许女士", "Phone", "我不想再和普通客服沟通了，请主管今天回电。", "OPEN", "HIGH", "21m", "handoff", "high", "tenant-internal", "主管升级", "degraded", "触发人工升级兜底", "客户明确要求主管介入，应进入人工路由，不由模型继续自动处理。", "创建升级任务，记录回电时间和诉求摘要。", "我理解您的诉求。我会为您创建主管升级记录，并备注希望今天回电，请您确认方便接听的时间段。", undefined, "high_risk_handoff", [{ docId: "tenant-internal/handoff_routing_sop.md", title: "转人工路由 SOP", score: 0.88 }]),
  ticket("T-1023", "订单关闭后要求恢复", "彭先生", "App", "订单被我误操作取消了，能恢复吗？", "CANCELLED", "NORMAL", "closed", "general", "medium", "tenant-a", "订单恢复", "degraded", "取消订单需人工核查", "取消后恢复能力依赖库存、支付和订单状态，模板降级不自动承诺。", "引导客户提供订单号，按人工核查处理。", "您好，请您提供订单号。我会帮您核对订单是否仍可恢复；如果库存或支付状态已变化，可能需要重新下单或人工处理。", undefined, "template_only", [fallbackCitation])
];

const traceScenarios: TraceScenario[] = [
  {
    id: "refund-quality",
    label: "有证据退款",
    question: "我签收 8 天了，耳机有质量问题还能退吗？",
    intent: "refund",
    strategy: "deep hybrid + qwen3-rerank fallback",
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
    traceSteps: ["Query Rewrite accepted", "Hybrid recall", "qwen3-rerank unavailable -> lightweight rerank", "Answer with citations"]
  },
  {
    id: "high-risk",
    label: "高风险投诉",
    question: "你们必须赔我 5000，不然我起诉并找媒体曝光。",
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
    traceSteps: ["Risk terms matched", "Internal SOP recall", "Handoff required", "No compensation promise"]
  },
  {
    id: "no-evidence",
    label: "无证据兜底",
    question: "你们能不能给我终身免费会员？",
    intent: "billing",
    strategy: "fallback guarded",
    shouldHandoff: true,
    fallbackReason: "no_sufficient_evidence",
    answer: "知识库没有充分证据支持确定回答，进入人工核查和知识库补充池。",
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
    traceSteps: ["Unsupported entitlement detected", "Weak evidence removed", "Fallback SOP retained", "Knowledge gap logged"]
  }
];

// 工单工厂：把 20 条演示工单的公共字段、AI 状态和引用证据收敛到统一结构，降低 mock 数据维护成本。
function ticket(
  id: string,
  title: string,
  customerName: string,
  channel: string,
  message: string,
  status: TicketStatus,
  priority: TicketPriority,
  sla: string,
  intent: string,
  risk: "low" | "medium" | "high",
  tenant: Ticket["tenant"],
  category: string,
  aiState: AiState,
  headline: string,
  summary: string,
  recommendation: string,
  suggestedReply: string,
  modelName: string | undefined,
  degradedReason: string | undefined,
  citations: AssistData["citations"]
): Ticket {
  return {
    id,
    title,
    customerName,
    channel,
    message,
    status,
    priority,
    sla,
    intent,
    risk,
    tenant,
    category,
    assist: {
      state: aiState,
      headline,
      summary,
      intent,
      slaRisk: risk === "high" ? "HIGH" : risk === "medium" ? "MEDIUM" : "LOW",
      recommendation,
      suggestedReply,
      confidence: aiState === "completed" ? 0.82 : aiState === "degraded" ? 0.58 : aiState === "pending" ? 0 : 0.28,
      generationMode: aiState === "completed" ? "llm" : aiState === "pending" ? "pending" : aiState === "failed" ? "failed" : "template_fallback",
      modelName,
      degradedReason,
      citations
    },
    assignedAgentId: status === "IN_PROGRESS" || status === "WAITING_CUSTOMER" || status === "RESOLVED" ? "agent-07" : undefined,
    replies: []
  };
}

// 主工作台：承载三栏布局、工单筛选、抢单、状态流转、采纳建议和本地回复闭环。
function App() {
  const [tickets, setTickets] = useState<Ticket[]>(initialTickets);
  const [selectedId, setSelectedId] = useState("T-1042");
  const [rightTab, setRightTab] = useState<RightPanelTab>("assist");
  const [queueFilter, setQueueFilter] = useState<QueueFilter>("all");
  const [search, setSearch] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const selected = tickets.find((item) => item.id === selectedId) ?? tickets[0];
  const draft = drafts[selected.id] ?? "";

  const queueStats = useMemo(() => {
    return {
      open: tickets.filter((item) => item.status === "OPEN").length,
      active: tickets.filter((item) => item.status === "IN_PROGRESS").length,
      risk: tickets.filter((item) => item.risk === "high").length
    };
  }, [tickets]);

  const visibleTickets = useMemo(() => {
    return tickets.filter((item) => {
      const matchesFilter =
        queueFilter === "all" ||
        (queueFilter === "mine" && item.assignedAgentId === "agent-07") ||
        (queueFilter === "escalated" && item.status === "ESCALATED");
      const text = `${item.id} ${item.title} ${item.customerName} ${item.category} ${item.message}`.toLowerCase();
      return matchesFilter && text.includes(search.toLowerCase().trim());
    });
  }, [queueFilter, search, tickets]);

  // 局部更新工单：所有前端演示交互都通过该入口修改当前 ticket，避免分散 setState。
  function updateTicket(ticketId: string, updater: (ticket: Ticket) => Ticket) {
    setTickets((current) => current.map((item) => (item.id === ticketId ? updater(item) : item)));
  }

  // 领取工单：模拟坐席抢单成功路径，真实接后端后对应条件更新和审计事件。
  function claimTicket() {
    updateTicket(selected.id, (item) => {
      if (item.status !== "OPEN") {
        return {
          ...item,
          conflict: `工单当前为 ${item.status}，不能领取。服务端会以 MySQL 条件更新返回 0 行作为冲突事实。`
        };
      }
      return { ...item, status: "IN_PROGRESS", assignedAgentId: "agent-me", conflict: undefined };
    });
  }

  // 抢单冲突模拟：展示并发领取失败时的产品反馈，不依赖真实后端也能讲清并发设计。
  function simulateClaimConflict() {
    updateTicket(selected.id, (item) => ({
      ...item,
      status: "IN_PROGRESS",
      assignedAgentId: "agent-11",
      conflict: "领取失败：该工单已被 agent-11 领取。服务端以 MySQL 条件更新结果为准。"
    }));
  }

  // 状态流转：本地演示 OPEN、处理中、待客户、已解决等状态机按钮效果。
  function transition(target: TicketStatus) {
    updateTicket(selected.id, (item) => ({ ...item, status: target, conflict: undefined }));
  }

  // 采纳 Copilot 建议：把右侧 Assist 推荐回复写入中间回复框，展示坐席工作流闭环。
  function adoptSuggestion() {
    setDrafts((current) => ({ ...current, [selected.id]: selected.assist.suggestedReply }));
  }

  // 发送回复：本地追加到会话记录，演示坐席采纳、编辑、发送后的可见反馈。
  function sendReply() {
    const text = draft.trim();
    if (!text) return;
    updateTicket(selected.id, (item) => ({
      ...item,
      replies: [
        ...(item.replies ?? []),
        {
          id: `${item.id}-reply-${(item.replies?.length ?? 0) + 1}`,
          text,
          createdBy: "agent-me"
        }
      ],
      status: item.status === "OPEN" ? "IN_PROGRESS" : item.status
    }));
    setDrafts((current) => ({ ...current, [selected.id]: "" }));
  }

  // AI 重试降级：模拟真实 LLM 失败后转入 mock_fallback，保证面试现场仍可完整展示。
  function retryAssist() {
    updateTicket(selected.id, (item) => ({
      ...item,
      assist: {
        ...item.assist,
        state: "degraded",
        headline: "已使用前端兜底建议",
        summary: "真实 LLM 或异步任务暂不可用，前端保留 mock 建议作为演示降级层。",
        generationMode: "mock_fallback",
        degradedReason: "demo_mock_fallback",
        confidence: 0.54,
        citations: item.assist.citations.length ? item.assist.citations : [fallbackCitation]
      }
    }));
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
          <input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="搜索工单" placeholder="搜索工单、客户、场景或证据" />
        </div>

        <div className="queue-filter">
          <button className={queueFilter === "all" ? "is-active" : ""} onClick={() => setQueueFilter("all")}>All</button>
          <button className={queueFilter === "mine" ? "is-active" : ""} onClick={() => setQueueFilter("mine")}>Mine</button>
          <button className={queueFilter === "escalated" ? "is-active" : ""} onClick={() => setQueueFilter("escalated")}>Escalated</button>
        </div>

        <nav className="ticket-list" aria-label="工单队列">
          {visibleTickets.map((item) => (
            <button
              className={`ticket-row ${item.id === selected.id ? "is-selected" : ""}`}
              key={item.id}
              onClick={() => setSelectedId(item.id)}
            >
              <div className="row-topline">
                <span className="ticket-id">{item.id} · {item.category}</span>
                <StatusBadge status={item.status} />
              </div>
              <div className="ticket-title">{item.title}</div>
              <div className="ticket-preview">{item.message}</div>
              <div className="row-footer">
                <span>{item.customerName} · {item.channel}</span>
                <span className={item.risk === "high" ? "risk-text" : ""}>SLA {item.sla}</span>
              </div>
            </button>
          ))}
        </nav>
      </section>

      <section className="workspace-pane">
        <header className="workspace-topbar">
          <div>
            <div className="eyebrow">当前工单 · {selected.id} · {selected.tenant}</div>
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

            {(selected.replies ?? []).length ? (
              <div className="sent-replies">
                {(selected.replies ?? []).map((reply) => (
                  <div className="sent-reply" key={reply.id}>
                    <span>{reply.createdBy}</span>
                    <p>{reply.text}</p>
                  </div>
                ))}
              </div>
            ) : null}

            <div className="reply-tools">
              <button className="adopt-action" onClick={adoptSuggestion} disabled={!selected.assist.suggestedReply}>
                <CopyCheck size={16} />
                <span>采纳建议</span>
              </button>
              <div className="reply-meta" aria-label="AI generation status">
                <span className="reply-meta-label">Copilot</span>
                <span className={`model-chip ${selected.assist.generationMode === "llm" ? "is-live" : "is-fallback"}`}>
                  {selected.assist.generationMode === "llm" ? selected.assist.modelName : "fallback"}
                </span>
              </div>
            </div>
            <div className="reply-composer">
              <input value={draft} onChange={(event) => setDrafts((current) => ({ ...current, [selected.id]: event.target.value }))} aria-label="回复客户" placeholder="输入给客户的回复，或采纳 Copilot 建议" />
              <button title="发送回复" onClick={sendReply}><Send size={17} /></button>
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
              <button onClick={() => transition("WAITING_CUSTOMER")} disabled={selected.status !== "IN_PROGRESS"}>等待客户</button>
              <button onClick={() => transition("RESOLVED")} disabled={selected.status !== "IN_PROGRESS" && selected.status !== "WAITING_CUSTOMER"}>标记解决</button>
              <button onClick={() => transition("ESCALATED")} disabled={selected.status === "CLOSED"}>升级</button>
              <button onClick={() => transition("CLOSED")} disabled={selected.status !== "RESOLVED"}>关闭</button>
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

        {rightTab === "assist" ? <AiAssist ticket={selected} onRetry={retryAssist} /> : null}
        {rightTab === "trace" ? <EvidenceTracePanel /> : null}
        {rightTab === "evals" ? <EvalPanel /> : null}
      </aside>
    </main>
  );
}

// 左侧队列指标：展示 Open、Active、Risk 等坐席工作量概览。
function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

// 工单状态徽标：把状态机结果压缩成列表可扫描的视觉标签。
function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status}</span>;
}

// 右侧 Assist 面板：统一展示成功、分析中、降级和失败重试四类 AI 状态。
function AiAssist({ ticket, onRetry }: { ticket: Ticket; onRetry: () => void }) {
  const assist = ticket.assist;
  if (assist.state === "pending") {
    return (
      <div className="assist-state">
        <Clock3 size={20} />
        <strong>AI 分析中</strong>
        <p>工单已创建，AI Assist 通过异步事件生成，不阻塞坐席处理。当前页面仍保留 mock 工单和客户诉求。</p>
      </div>
    );
  }

  if (assist.state === "failed") {
    return (
      <div className="assist-state error">
        <AlertTriangle size={20} />
        <strong>AI Assist 生成失败</strong>
        <p>主工单流程保持可用。可以点击重试，或使用前端兜底 mock 建议继续演示。</p>
        <button onClick={onRetry}><RefreshCw size={16} />重试并使用兜底</button>
      </div>
    );
  }

  return (
    <div className="assist-stack">
      <section className={`assist-hero ${assist.state === "degraded" ? "is-degraded" : ""}`}>
        <div>
          <div className="eyebrow">Agent Copilot · {assist.generationMode}</div>
          <h2>{assist.headline}</h2>
        </div>
        <Sparkles size={20} />
      </section>

      {assist.state === "degraded" ? (
        <div className="degrade-banner">
          <AlertTriangle size={15} />
          <span>LLM/Rerank 不可用时已降级：{assist.degradedReason ?? "template_fallback"}</span>
        </div>
      ) : null}

      <AssistCard icon={<CheckCircle2 size={17} />} title="摘要">
        <p>{assist.summary}</p>
      </AssistCard>

      <AssistCard icon={<AlertTriangle size={17} />} title="风险与转人工">
        <dl className="assist-kv">
          <dt>意图</dt>
          <dd>{assist.intent}</dd>
          <dt>SLA</dt>
          <dd className={assist.slaRisk === "HIGH" ? "risk-text" : ""}>{assist.slaRisk}</dd>
          <dt>建议</dt>
          <dd>{assist.recommendation}</dd>
          <dt>置信度</dt>
          <dd>{assist.confidence.toFixed(2)}</dd>
        </dl>
      </AssistCard>

      <AssistCard icon={<FileText size={17} />} title="建议回复">
        <p>{assist.suggestedReply}</p>
        <div className="citation-box">
          引用：{assist.citations.map((item) => `${item.title} / ${item.score.toFixed(2)}`).join("；") || "无直接引用，使用前端演示兜底"}
        </div>
      </AssistCard>
    </div>
  );
}

// Assist 信息卡：承载摘要、风险、建议回复等重复结构，保持右侧面板一致性。
function AssistCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="assist-card">
      <div className="assist-card-title">
        {icon}
        <span>{title}</span>
      </div>
      {children}
    </div>
  );
}

// Evidence Trace 面板：展示 RAG rewrite、召回、rerank、引用和评估指标的可追溯链路。
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

// 评估面板：展示 RAG 批量评估的核心指标，方便面试时说明可运营、可评估能力。
function EvalPanel() {
  const rows = [
    ["Context Recall", "0.58", "retrieval gap"],
    ["Citation Coverage", "1.00", "stable"],
    ["Faithfulness", "0.67", "needs rerank"],
    ["Tenant Leak Count", "0", "isolated"],
    ["Handoff Accuracy", "0.88", "good"],
    ["LLM Fallback", "ready", "safe demo"],
    ["Rerank Fallback", "ready", "qwen3-rerank"]
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

// 小型评估指标：用于右侧 Evals 面板的紧凑数据展示。
function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="mini-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
