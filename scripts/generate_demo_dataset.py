from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "contactflow_demo_kb_v0.2"
KB = DATASET / "kb"
EVAL = DATASET / "eval"


DOCS = [
    {
        "tenant": "tenant-a",
        "name": "refund_policy",
        "title": "Tenant A 数码商品退货退款政策",
        "keywords": ["签收", "7 天", "未使用", "质量问题", "人工审核"],
        "body": """
## 适用范围
本政策适用于 Tenant A 自营数码商品，包括耳机、键盘、显示器、充电器和智能穿戴设备。订单状态为已签收后开始计算售后时效，系统记录的签收时间是唯一判定依据。

## 标准规则
签收 7 天内且商品未使用、包装完整、配件齐全时，客户可以申请无理由退货退款。若商品存在质量问题，即使超过 7 天，也不能直接承诺退款，坐席需要先创建质检工单并上传照片、故障描述和订单号。签收超过 7 天的普通不喜欢、不想要、买错型号，默认进入人工审核。

## 例外条件
耳机、贴身穿戴设备拆封后涉及卫生风险，除质量问题外不支持无理由退货。定制刻字、企业批量采购、赠品缺失、序列号不一致都需要人工审核。坐席不得承诺“必退”或“立即到账”，只能说明审核路径和预计处理时间。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "exchange_policy",
        "title": "Tenant A 换货与型号错误处理",
        "keywords": ["换货", "型号", "库存", "差价", "7 天"],
        "body": """
## 换货入口
客户收到错误型号、颜色或规格不符时，坐席应先核对订单 SKU、仓库出库记录和商品序列号。若确认平台发错货，7 天内优先安排免费换货；若客户自行选错型号，应按普通退货规则处理。

## 库存与差价
同价同型号换货无需补差价。若客户希望更换为更高价格型号，必须先退后买，不能由坐席私下改价。若目标型号缺货，坐席可提供退款、等待补货或升级主管三种选项。

## 风险控制
换货前必须确认原商品未人为损坏，配件和赠品齐全。客户已经拆封但主张型号错误时，需要上传外包装条码和商品实拍。无法核实的场景不得直接承诺换货。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "delivery_delay_sop",
        "title": "Tenant A 物流延迟处理 SOP",
        "keywords": ["物流", "48 小时", "轨迹", "补偿", "升级"],
        "body": """
## 延迟判定
物流超过承诺时间 48 小时仍未更新，或包裹连续 3 天停留在同一分拨中心，可判定为物流异常。坐席应先查询物流轨迹、承运商状态和订单发货时间，再判断是否需要升级。

## 坐席步骤
第一步安抚客户并确认收货地址。第二步查询承运商轨迹，记录最近一次扫描时间。第三步根据延迟时长给出处理方案：48 小时内继续关注，超过 48 小时可申请物流催查，超过 5 天可升级主管评估补偿。

## 补偿边界
坐席可说明“可能发放优惠券或运费补偿”，但不得直接承诺金额。高价值订单、投诉倾向、媒体曝光或法律威胁必须转人工主管处理。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "lost_package_sop",
        "title": "Tenant A 丢件与签收争议 SOP",
        "keywords": ["丢件", "签收争议", "代收", "承运商", "补发"],
        "body": """
## 争议类型
签收争议包括系统显示已签收但客户未收到、门卫代收未通知、快递柜超时退回、承运商误投。坐席不能仅凭客户描述直接判定丢件，需要收集地址、联系电话和签收截图。

## 处理流程
坐席先发起承运商核查，要求提供签收凭证和投递位置。若承运商确认误投或丢件，可创建补发或退款工单。若承运商提供有效签收凭证，但客户仍否认收货，应升级主管复核。

## 时效与话术
承运商核查通常需要 1 到 3 个工作日。坐席应说明核查时效和下一步动作，不得在核查前承诺补发、退款或赔偿。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "warranty_policy",
        "title": "Tenant A 保修与质量检测政策",
        "keywords": ["保修", "质量问题", "检测", "序列号", "人为损坏"],
        "body": """
## 保修范围
Tenant A 自营数码商品默认提供 12 个月有限保修。保修覆盖非人为硬件故障，例如无法开机、按键失灵、显示异常、蓝牙连接失败。保修不覆盖进水、摔落、私拆、非官方配件导致的损坏。

## 检测要求
客户主张质量问题时，需要提供订单号、故障视频或照片、商品序列号。坐席应创建质检工单，不得直接判断责任归属。检测结果为非人为故障时，可进入维修、换货或退款评估。

## 与退款关系
签收 7 天内出现质量问题，可结合退款政策处理。超过 7 天但在保修期内，优先维修或换货；是否退款需要主管审核。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "invoice_policy",
        "title": "Tenant A 发票与抬头规则",
        "keywords": ["发票", "抬头", "税号", "电子发票", "红冲"],
        "body": """
## 开票规则
客户可在订单完成后 30 天内申请电子普通发票。企业抬头必须提供准确公司名称和纳税人识别号，个人抬头无需税号。发票金额以实际支付金额为准，不包含优惠券抵扣部分。

## 修改与红冲
发票已开具但抬头错误时，坐席应先核实错误原因。未入账发票可申请红冲重开；已入账发票需要客户确认财务处理状态。跨月红冲可能延长处理时间。

## 边界
坐席不得承诺虚开发票、拆分金额、修改商品名称或开具未实际支付金额。客户要求违规开票时，应说明平台合规要求并拒绝。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "coupon_compensation_policy",
        "title": "Tenant A 优惠券与补偿边界",
        "keywords": ["优惠券", "补偿", "延迟", "投诉", "主管审批"],
        "body": """
## 可用场景
优惠券补偿适用于物流延迟、售后等待时间较长、轻微服务体验问题。普通坐席可建议补偿，但金额、类型和有效期需要系统规则或主管审批。

## 不可承诺
客户提出精神损失费、误工费、惩罚性赔偿时，坐席不得承诺现金赔偿。涉及法律威胁、监管投诉或媒体曝光时，必须转人工主管。

## 记录要求
每次补偿建议都需要记录触发原因、订单号、客户诉求和对应 SOP。重复补偿、同一客户短期多次投诉、金额异常时，系统应提示风险。
""",
    },
    {
        "tenant": "tenant-a",
        "name": "preorder_policy",
        "title": "Tenant A 预售订单与取消规则",
        "keywords": ["预售", "定金", "尾款", "取消", "发货时间"],
        "body": """
## 预售说明
预售商品页面会标注预计发货时间、定金规则和尾款支付窗口。客户支付定金后，若未在规定时间内支付尾款，订单可能自动关闭。

## 取消规则
未支付尾款前，客户可申请取消预售订单，但定金是否可退以页面规则为准。平台原因导致发货延迟超过公告时间 7 天以上，客户可申请取消并进入退款审核。

## 坐席要求
坐席应核对商品页面快照、订单支付状态和公告记录。不得口头承诺提前发货，也不得覆盖页面明确展示的定金规则。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "cross_border_refund_policy",
        "title": "Tenant B 跨境服饰家居退款政策",
        "keywords": ["跨境", "30 天", "退货", "清关", "运费"],
        "body": """
## 适用范围
Tenant B 经营跨境服饰和家居商品。普通商品签收 30 天内可申请退货，但必须保持未穿着、未洗涤、吊牌完整。跨境订单退货需要考虑清关、国际运费和仓库验收时间。

## 退款规则
商品退回海外仓并验收通过后，系统发起退款。国际运费一般不退，除非平台发错货或商品存在质量问题。客户仅因尺码不合适申请退货，需要自行承担寄回运费。

## 例外
贴身衣物、定制窗帘、已组装家具和清仓 final sale 商品通常不支持无理由退货。坐席必须引用商品页规则，不得把 Tenant A 的 7 天数码政策套用到 Tenant B。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "size_exchange_policy",
        "title": "Tenant B 尺码换货规则",
        "keywords": ["尺码", "换货", "吊牌", "库存", "运费"],
        "body": """
## 尺码问题
客户因尺码不合适申请换货时，坐席应引导客户确认尺码表、商品吊牌和试穿状态。未穿着、未洗涤、吊牌完整时，可申请换码。

## 运费承担
客户自行选错尺码通常承担寄回运费。商品页面尺码标注错误或仓库发错尺码时，由平台承担换货运费。跨境换货时效可能比本地订单更长。

## 缺货处理
目标尺码缺货时，可提供等待补货、退货退款或换同价商品三个方案。坐席不得承诺一定能换到目标尺码。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "custom_home_goods_policy",
        "title": "Tenant B 定制家居商品政策",
        "keywords": ["定制", "窗帘", "尺寸", "不可退", "生产"],
        "body": """
## 定制范围
定制窗帘、定制地毯、刻字家居和按客户尺寸生产的商品属于定制商品。客户提交尺寸并确认设计稿后，订单进入生产流程。

## 取消与退货
生产前可申请取消，是否产生费用取决于供应商状态。进入生产后，除质量问题或平台生产错误外，不支持无理由退货。客户提供错误尺寸导致无法安装，不属于平台责任。

## 坐席要求
坐席需要核对客户确认记录、尺寸表、设计稿和生产状态。不得简单使用普通退货政策回答定制商品问题。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "cross_border_shipping_sop",
        "title": "Tenant B 跨境物流与清关 SOP",
        "keywords": ["跨境物流", "清关", "关税", "延迟", "追踪"],
        "body": """
## 物流阶段
跨境订单通常经历海外仓出库、国际运输、清关、本地派送四个阶段。不同阶段的延迟原因不同，坐席必须先识别当前阶段。

## 清关延迟
清关超过 5 个工作日未更新时，应查询承运商状态并提示客户可能需要补充身份信息或税费信息。涉及海关查验时，平台无法承诺具体放行时间。

## 风险边界
客户询问关税时，坐席只能说明订单页展示规则和当地政策可能影响费用。不得承诺规避税费或修改申报价值。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "tax_duty_policy",
        "title": "Tenant B 税费与申报规则",
        "keywords": ["税费", "关税", "申报", "VAT", "清关"],
        "body": """
## 税费说明
跨境订单可能产生关税、VAT 或清关服务费。是否由客户承担取决于商品页、目的地和订单结算页展示规则。

## 申报要求
平台按真实商品信息申报，不接受低报价格、修改品名、拆分包裹规避税费等请求。客户要求修改申报时，坐席应明确拒绝并记录合规风险。

## 退款关系
因客户拒付税费导致包裹退回，退款金额可能扣除国际运费和退回成本。若页面承诺包税但实际重复收费，应升级财务核查。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "damaged_home_goods_sop",
        "title": "Tenant B 家居破损与拍照取证 SOP",
        "keywords": ["破损", "照片", "外箱", "补发", "理赔"],
        "body": """
## 取证要求
客户反馈家居商品破损时，需要提供外箱照片、破损位置照片、面单照片和开箱时间。大件家具还需要确认是否已安装。

## 处理路径
轻微划痕可评估部分补偿或配件补发。结构性损坏、无法使用或运输破损，应发起承运商理赔和售后补发审核。坐席不得在证据不足时承诺全额退款。

## 时效
破损反馈应在签收后 72 小时内提交。超过时效但客户能提供明确物流损坏证据时，可升级主管复核。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "subscription_billing_policy",
        "title": "Tenant B 会员订阅与账单规则",
        "keywords": ["会员", "订阅", "自动续费", "账单", "取消"],
        "body": """
## 订阅说明
Tenant B Plus 会员按月或按年自动续费。客户可在下一个账单日前取消续费，取消后会员权益保留到当前周期结束。

## 退款规则
会员已使用专属折扣、免邮券或提前购权益后，通常不支持退还当期费用。重复扣费、系统错误扣费或未授权扣费需要财务核查。

## 坐席要求
坐席应核对订阅状态、扣费时间、支付渠道和权益使用记录。客户表示未授权扣费时，应引导其提交支付凭证并升级账务工单。
""",
    },
    {
        "tenant": "tenant-b",
        "name": "address_change_policy",
        "title": "Tenant B 地址修改与截单规则",
        "keywords": ["地址修改", "截单", "仓库", "派送", "失败"],
        "body": """
## 可修改阶段
订单未出库前可以申请修改地址。海外仓已出库、国际运输中或清关中时通常无法修改地址。本地派送阶段可尝试联系承运商，但不保证成功。

## 坐席流程
坐席应先查询订单履约阶段，再判断是否可截单。若仓库已锁单，坐席只能提交截单请求，不能保证一定成功。

## 风险提示
客户因自行填写错误地址导致派送失败，可能需要承担二次派送或退回费用。平台原因导致地址错误时，应升级履约团队处理。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "high_risk_complaint_sop",
        "title": "内部 SOP 高风险投诉与法律威胁处理",
        "keywords": ["法律威胁", "监管", "媒体", "不得承诺赔偿", "升级主管"],
        "body": """
## 高风险识别
客户出现法律威胁、监管投诉、媒体曝光、群体投诉、精神损失费、惩罚性赔偿等表达时，系统应标记为高风险。坐席必须停止自动生成确定性赔偿承诺。

## 处理步骤
坐席先安抚客户并确认订单、联系方式、诉求和证据。随后创建升级工单，标注风险类型和客户原话。主管或法务团队接手前，坐席只能说明“我们会升级核查”，不得承诺退款、现金赔偿或处理结果。

## 记录要求
所有高风险会话需要保存原始对话、AI 建议、坐席修改记录和最终处理结果，用于质检和复盘。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "forbidden_promises",
        "title": "内部 SOP 禁止承诺与合规话术",
        "keywords": ["禁止承诺", "必退", "赔偿", "虚开发票", "合规"],
        "body": """
## 禁止表达
坐席不得使用“肯定退款”“一定赔偿”“马上到账”“保证清关”“可以低报税费”“可以虚开发票”等表达。AI Assist 生成建议时也必须避免这些措辞。

## 推荐表达
推荐使用“我会为您提交审核”“需要根据检测结果确认”“预计处理时间为”“我们会升级专员核查”等可验证话术。涉及政策例外时，必须引用知识库证据。

## 质检要求
质检 Agent 需要检查是否存在过度承诺、遗漏风险提示、未引用证据和未转人工。违规话术应进入坐席培训反馈池。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "handoff_routing_sop",
        "title": "内部 SOP 转人工与派单规则",
        "keywords": ["转人工", "低置信", "派单", "主管", "工单"],
        "body": """
## 转人工条件
低置信度、无证据、政策冲突、高风险投诉、VIP 客户、多次追问未解决、客户要求主管时，应转人工。AI 可以给出摘要和建议动作，但不能直接修改工单最终状态。

## 派单规则
普通售后进入一线坐席队列，跨境税费进入财务与清关队列，高风险投诉进入主管队列，法律威胁进入法务协同队列。派单事件需要记录 eventId 以支持幂等。

## 运营指标
系统需要统计转人工率、首轮解决率、AI 建议采纳率、未命中问题数和平均响应时延。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "knowledge_update_workflow",
        "title": "内部 SOP 知识库更新与审核流程",
        "keywords": ["知识库", "未命中", "审核", "发布", "版本"],
        "body": """
## 来源
知识库更新来源包括未命中问题、坐席修改记录、政策变更通知、质检复盘和高频咨询聚类。自动生成的 FAQ 候选不能直接发布。

## 审核流程
知识运营人员需要检查适用租户、生效日期、冲突政策、引用来源和合规措辞。审核通过后生成新版本，旧版本保留用于追溯。

## 闭环
每次回答应记录命中文档、chunk、rewrite、rerank score 和最终引用。低召回或高幻觉风险的问题进入改进池。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "rag_evaluation_guideline",
        "title": "内部 SOP RAG 评估指标说明",
        "keywords": ["Context Recall", "Faithfulness", "Citation Coverage", "Hallucination", "Trace"],
        "body": """
## 检索指标
Context Recall 衡量标准答案所需证据是否出现在召回上下文中。Tenant Leak Count 衡量是否召回了其他租户资料。Retrieval Latency 用于控制坐席体验。

## 生成指标
Faithfulness 衡量回答是否被上下文支持。Citation Coverage 衡量关键结论是否带引用。Hallucination Risk 在证据不足或回答越过证据时升高。

## 业务指标
首轮解决率、转人工率、坐席采纳率、坐席修改率和未命中问题沉淀，是判断系统是否可运营的核心指标。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "tenant_isolation_policy",
        "title": "内部 SOP 多租户知识隔离规则",
        "keywords": ["租户隔离", "tenant_id", "ACL", "数据泄漏", "权限"],
        "body": """
## 基本原则
每条知识、chunk、评估问题和回答 trace 必须带 tenant_id。检索时必须先做租户过滤，再做向量或 BM25 召回。内部 SOP 可以被授权坐席使用，但不能泄露给客户。

## 风险场景
Tenant A 的 7 天数码退款政策不能回答 Tenant B 的跨境服饰 30 天退货问题。Tenant B 的税费规则不能回答 Tenant A 的国内数码订单。跨租户命中应计为严重检索错误。

## 审计
每次召回需要记录 tenant_id、doc_id、chunk_id、ACL tag 和调用用户角色，方便排查数据泄漏。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "outdated_policy_conflict",
        "title": "内部样本 过期政策与冲突识别",
        "keywords": ["过期政策", "冲突", "生效日期", "不得使用", "人工确认"],
        "body": """
## 样本说明
本文件用于测试过期政策识别，不作为正式客服答案依据。旧版数码退款政策曾允许签收 15 天内无理由退货，但该规则已于 2026-01-01 失效。

## 冲突处理
当检索同时命中新旧政策时，应优先使用生效日期最新且状态为 published 的文档。若无法判断版本，应提示证据冲突并转人工确认。

## 评估用途
评估集会使用本文件测试系统是否能识别过期政策、避免把旧政策当作最终答案。
""",
    },
    {
        "tenant": "tenant-internal",
        "name": "agent_assist_trace_sop",
        "title": "内部 SOP AI Assist Trace 记录规范",
        "keywords": ["trace", "rewrite", "retrieved chunks", "rerank score", "fallback"],
        "body": """
## Trace 字段
AI Assist 每次检索需要记录 originalQuery、acceptedRewrites、rejectedRewrites、retrievalStrategy、retrievedChunks、rerankScores、finalContext、citations、latencyMs 和 fallbackReason。

## 追溯要求
坐席或主管查看答案时，必须能看到证据来源、分数和低置信原因。无证据回答不得伪造引用，必须显示转人工或补充知识库建议。

## 运营用途
Trace 用于分析未命中问题、rewrite 噪音、重排序失败和知识库过期问题。运营人员可根据 trace 决定是否新增 FAQ 或调整 SOP。
""",
    },
]


CASE_TEMPLATES = [
    ("single_doc", 25),
    ("multi_condition", 20),
    ("multi_doc", 15),
    ("keyword_exact", 15),
    ("colloquial_rewrite", 15),
    ("rewrite_drift", 10),
    ("tenant_isolation", 10),
    ("no_evidence_handoff", 10),
]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def doc_id(doc: dict) -> str:
    return f"{doc['tenant']}/{doc['name']}.md"


def render_doc(doc: dict) -> str:
    return f"""---
tenant_id: {doc["tenant"]}
doc_id: {doc_id(doc)}
title: {doc["title"]}
status: published
effective_from: 2026-01-01
acl_tags: ["support"]
---

# {doc["title"]}

{doc["body"].strip()}
"""


def build_case(index: int, kind: str, offset: int) -> dict:
    public_docs = [doc for doc in DOCS if doc["tenant"] != "tenant-internal"]
    internal_docs = [doc for doc in DOCS if doc["tenant"] == "tenant-internal"]
    base = public_docs[(index + offset) % len(public_docs)]
    support = internal_docs[(index + offset) % len(internal_docs)]

    if kind == "single_doc":
        question = f"{base['title']} 里，客户问 {base['keywords'][0]} 和 {base['keywords'][1]} 时应该怎么处理？"
        expected = [doc_id(base)]
        should_answer = True
        should_handoff = False
        risk = "low"
    elif kind == "multi_condition":
        question = f"客户同时提到{base['keywords'][0]}、{base['keywords'][2]}，还说已经超过标准时效，这种情况能直接承诺处理结果吗？"
        expected = [doc_id(base), doc_id(support)]
        should_answer = True
        should_handoff = "不得承诺" in support["keywords"] or "转人工" in support["keywords"]
        risk = "medium"
    elif kind == "multi_doc":
        other = public_docs[(index + offset + 5) % len(public_docs)]
        question = f"一个问题同时涉及{base['keywords'][0]}和{other['keywords'][0]}，坐席需要引用哪些政策并怎么解释边界？"
        expected = [doc_id(base), doc_id(other)]
        should_answer = True
        should_handoff = False
        risk = "medium"
    elif kind == "keyword_exact":
        token = f"SKU-CF-{1000 + index}"
        question = f"订单 {token} 咨询 {base['keywords'][0]}，需要精确召回哪个政策编号或 SOP？"
        expected = [doc_id(base)]
        should_answer = True
        should_handoff = False
        risk = "low"
    elif kind == "colloquial_rewrite":
        question = f"这个还能弄吗？我说的是{base['keywords'][0]}，客服能不能帮我处理一下"
        expected = [doc_id(base)]
        should_answer = True
        should_handoff = False
        risk = "low"
    elif kind == "rewrite_drift":
        question = f"我只问{base['keywords'][0]}规则，不要把问题扩写成赔偿、投诉或税费"
        expected = [doc_id(base)]
        should_answer = True
        should_handoff = False
        risk = "medium"
    elif kind == "tenant_isolation":
        opposite = next(doc for doc in public_docs if doc["tenant"] != base["tenant"])
        question = f"我是 {base['tenant']} 的客户，问题是{base['keywords'][0]}，系统不能用 {opposite['tenant']} 的 {opposite['keywords'][0]} 政策回答。"
        expected = [doc_id(base), doc_id(next(doc for doc in internal_docs if doc["name"] == "tenant_isolation_policy"))]
        should_answer = True
        should_handoff = False
        risk = "high"
    else:
        high_risk = next(doc for doc in internal_docs if doc["name"] == "high_risk_complaint_sop")
        question = "你们必须赔我精神损失费 5000，不然我找监管、媒体曝光并起诉。"
        expected = [doc_id(high_risk), doc_id(next(doc for doc in internal_docs if doc["name"] == "forbidden_promises"))]
        should_answer = False
        should_handoff = True
        risk = "high"

    tenant = base["tenant"] if kind != "no_evidence_handoff" else "tenant-a"
    if kind == "tenant_isolation":
        tenant = base["tenant"]

    keywords = sorted({keyword for doc in DOCS if doc_id(doc) in expected for keyword in doc["keywords"][:3]})
    return {
        "id": f"eval-{kind}-{index:03d}",
        "type": kind,
        "tenant": tenant,
        "question": question,
        "expected_intent": infer_intent(base["name"], kind),
        "expected_doc_ids": expected,
        "expected_evidence_keywords": keywords,
        "should_answer": should_answer,
        "should_handoff": should_handoff,
        "risk_level": risk,
        "notes": "Synthetic enterprise customer-support eval case for retrieval, trace, and handoff validation.",
    }


def infer_intent(name: str, kind: str) -> str:
    if kind == "no_evidence_handoff":
        return "high_risk_complaint"
    if "refund" in name:
        return "refund_policy"
    if "shipping" in name or "delivery" in name or "lost" in name:
        return "delivery"
    if "invoice" in name or "billing" in name or "tax" in name:
        return "billing"
    if "warranty" in name or "damaged" in name:
        return "warranty"
    return "support_policy"


def build_cases() -> list[dict]:
    cases: list[dict] = []
    sequence = 1
    for kind, count in CASE_TEMPLATES:
        for item in range(count):
            cases.append(build_case(sequence, kind, item))
            sequence += 1
    return cases


def main() -> None:
    for doc in DOCS:
        write_text(KB / doc["tenant"] / f"{doc['name']}.md", render_doc(doc))

    cases = build_cases()
    EVAL.mkdir(parents=True, exist_ok=True)
    with (EVAL / "eval_cases.jsonl").open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "name": "ContactFlow Demo Enterprise KB",
        "version": "0.2",
        "doc_count": len(DOCS),
        "eval_case_count": len(cases),
        "tenants": sorted({doc["tenant"] for doc in DOCS}),
        "case_distribution": dict(CASE_TEMPLATES),
        "design_notes": [
            "Synthetic professional customer-support dataset; no copied vendor policy text.",
            "Inspired by enterprise help-center QA and enterprise RAG benchmark structures.",
            "Designed for tenant isolation, traceability, evidence recall, rewrite drift, and handoff evaluation.",
        ],
    }
    write_text(EVAL / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    readme = f"""# ContactFlow Demo Enterprise KB v0.2

This is a synthetic enterprise customer-support knowledge base for ContactFlow AI.
It is designed to test whether the RAG pipeline is operational, evaluable, and traceable.

## Contents

- Knowledge documents: {len(DOCS)} Markdown files
- Evaluation cases: {len(cases)} JSONL rows
- Tenants: tenant-a, tenant-b, tenant-internal

## Why Synthetic

The dataset follows the structure of real customer-support knowledge bases and enterprise RAG benchmarks,
but the policy content is fictional and written for ContactFlow AI. This keeps the project safe to publish
while still covering realistic support scenarios.

## Coverage

- Refund, exchange, warranty, invoice, delivery, lost package, compensation, preorder
- Cross-border shipping, tax, size exchange, custom home goods, damaged goods, subscription billing
- High-risk complaint, forbidden promises, handoff routing, knowledge update, RAG evaluation, tenant isolation
- Query rewrite drift, no-evidence fallback, multi-document reasoning, exact keyword recall

## Eval Schema

Each JSONL row includes:

- id
- type
- tenant
- question
- expected_intent
- expected_doc_ids
- expected_evidence_keywords
- should_answer
- should_handoff
- risk_level
"""
    write_text(DATASET / "README.md", readme)


if __name__ == "__main__":
    main()
