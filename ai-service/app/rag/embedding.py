# 展示说明：V0.2 本地可测 embedding 模块，用确定性 hashing 向量模拟语义召回，避免测试依赖外部模型服务。
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable


ASCII_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]+")

DOMAIN_TERMS = [
    "退款",
    "退货",
    "质量问题",
    "签收",
    "保修",
    "质检",
    "物流",
    "快递",
    "没收到",
    "丢件",
    "赔偿",
    "起诉",
    "法律",
    "律师",
    "监管",
    "投诉",
    "媒体",
    "曝光",
    "发票",
    "抬头",
    "税号",
    "会员",
    "终身免费",
    "免费会员",
    "跨境",
    "清关",
    "关税",
    "税费",
    "换货",
    "型号",
    "库存",
    "预售",
    "定金",
    "尾款",
    "优惠券",
    "补偿",
    "转人工",
]


def tokenize(text: str) -> list[str]:
    # 领域分词：同时保留英文/数字、客服业务词和中文 n-gram，为向量召回与 BM25 共用。
    lowered = text.lower()
    tokens = [token.lower() for token in ASCII_TOKEN_PATTERN.findall(lowered)]
    for term in DOMAIN_TERMS:
        if term.lower() in lowered:
            tokens.append(term.lower())
    for segment in CJK_PATTERN.findall(lowered):
        tokens.extend(segment[index : index + 2] for index in range(max(len(segment) - 1, 0)))
        tokens.extend(segment[index : index + 3] for index in range(max(len(segment) - 2, 0)))
    return tokens


class HashingEmbeddingModel:
    """Small deterministic embedding adapter for local tests.

    Production can replace this with an API-backed embedding model while keeping
    the same `embed` contract.
    """

    def __init__(self, dimensions: int = 128) -> None:
        # 维度固定保证本地测试稳定，也方便未来替换成真实 embedding 服务。
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        # 文本向量化：把 token 哈希到固定维度并归一化，支持离线可复现的相似度检索。
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return normalize(vector)


def normalize(vector: Iterable[float]) -> list[float]:
    # 向量归一化：让余弦相似度可比较，避免长文本天然占优。
    values = list(vector)
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    # 余弦相似度：向量召回和 rewrite 语义校验共用的基础评分函数。
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
