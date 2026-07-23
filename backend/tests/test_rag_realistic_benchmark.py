from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def realistic_runtime_config() -> dict:
    return {
        "providerName": "mock",
        "baseURL": "http://127.0.0.1:8765/mock",
        "model": "mock-embedding-realistic",
        "dimensions": 64,
        "batchSize": 4,
        "timeoutMs": 3000,
        "enabled": True,
        "apiKey": "mock-local-key",
    }


REALISTIC_DOCUMENTS = [
    {
        "title": "青柚会员计划",
        "sourceType": "markdown",
        "content": """
# 青柚会员计划

## 项目档案
编号：QY-MEMBER-2026
上线窗口：2026-08-18 19:30
预算金额：21.6 万元
负责人：沈知夏
说明：老会员续费提醒先确认续费意愿，再发放 7 天体验优惠券。

## 风险边界
规则：不得导入未授权手机号、身份证号或完整支付凭证。
""".strip(),
    },
    {
        "title": "青柚硬件巡检",
        "sourceType": "markdown",
        "content": """
# 青柚硬件巡检

## 项目档案
编号：QY-HARDWARE-2026
上线窗口：2026-09-05 10:00
预算金额：4.2 万元
负责人：韩序
说明：巡检只覆盖会议室投屏、备用路由器和直播麦克风。
""".strip(),
    },
    {
        "title": "蓝鲸发票规则",
        "sourceType": "markdown",
        "content": """
# 蓝鲸发票规则

## 开票字段
编号：BJ-INVOICE-2026
发票类型：电子普通发票
开票时限：付款后 3 个工作日内
负责人：陆芷
说明：用户需要提供抬头、税号和接收邮箱，不需要提供银行卡号。
""".strip(),
    },
    {
        "title": "蓝鲸退款流程",
        "sourceType": "markdown",
        "content": """
# 蓝鲸退款流程

## 处理规则
触发条件：用户明确提出退款、退钱或取消订单。
升级码：BJ-REFUND-42
处理动作：先安抚情绪，再核对订单号，然后提交人工复核。
证据来源：只使用用户主动提供的订单截图或订单号。

## 不该做
- 不要要求用户在公开聊天里发送银行卡号。
- 不要把退款凭证写入长期记忆。
""".strip(),
    },
    {
        "title": "雪松设备清单",
        "sourceType": "markdown",
        "content": """
# 雪松设备清单

## 借用规则
编号：XS-EQUIP-2026
保管人：乔澜
借用窗口：工作日 10:00-18:00
位置：B2 储物柜

## 设备表
| 设备 | 数量 | 位置 |
| --- | --- | --- |
| 直播麦克风 | 3 | B2-03 |
| 备用路由器 | 2 | B2-06 |
| 采集卡 | 1 | B2-08 |
""".strip(),
    },
    {
        "title": "星河内容排期",
        "sourceType": "markdown",
        "content": """
# 星河内容排期

## 发布字段
编号：XH-CONTENT-2026
发布时间：2026-08-22 12:00
负责人：任屿
审核人：白珩
说明：首发内容是“本地优先与隐私可控”，需要在发布前复核截图是否含 Key。
""".strip(),
    },
    {
        "title": "云朵课程报名",
        "sourceType": "markdown",
        "content": """
# 云朵课程报名

## 报名字段
编号：YD-COURSE-2026
优惠码：YUNDOU-CLASS-66
优惠口令：YUNDOU-CLASS-66
截止日期：2026-08-28
名额：60 人
负责人：许棠
说明：优惠码只用于云朵课程报名，不可用于其他活动。
""".strip(),
    },
    {
        "title": "云朵课程讲师安排",
        "sourceType": "markdown",
        "content": """
# 云朵课程讲师安排

## 讲师字段
编号：YD-TEACHER-2026
主讲人：程砚
助教：米洛
上课时间：2026-09-03 20:00
说明：主讲主题是“AI 伴侣的本地记忆与知识库边界”。
""".strip(),
    },
    {
        "title": "资料安全红线",
        "sourceType": "markdown",
        "content": """
# 资料安全红线

## 禁止导入
规则：不要导入身份证号、银行卡号、完整 API Key、密钥、Cookie、扫码凭证或未授权聊天记录。
处理动作：发现敏感资料时先停止导入，提示用户删除或脱敏后再试。

## 可导入
规则：可以导入用户自己整理且无隐私的产品说明、学习笔记、公开资料摘要。
""".strip(),
    },
    {
        "title": "知识库导入规范",
        "sourceType": "markdown",
        "content": """
# 知识库导入规范

## 支持格式
编号：KB-IMPORT-2026
支持格式：纯文本、Markdown
切片原则：尽量让同一事实组的编号、负责人、金额和日期留在同一切片里。
删除规则：资料被删除或删掉后，对应切片不再进入检索结果，也不再注入 prompt，不给模型继续参考。
""".strip(),
    },
    {
        "title": "情绪陪伴话术",
        "sourceType": "markdown",
        "content": """
# 情绪陪伴话术

## 回复原则
编号：CARE-TONE-2026
语气原则：先接住情绪，再给出选择，不要一上来讲大道理。
节奏：短句、慢一点、允许用户暂停。
边界：不要承诺替用户做现实世界决定。
""".strip(),
    },
    {
        "title": "桌面数据迁移说明",
        "sourceType": "markdown",
        "content": """
# 桌面数据迁移说明

## 数据位置
编号：DESKTOP-MIGRATION-2026
数据库位置：Electron userData/backend/suoyi.sqlite
回滚入口：保留旧 localStorage fallback；迁移失败时继续读取旧数据。
说明：API Key 不进入 SQLite，需要用户在桌面版重新填写。
""".strip(),
    },
]


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    query: str
    expected_source: str | None
    required_text: tuple[str, ...] = ()
    forbidden_text: tuple[str, ...] = ()
    should_inject: bool = True
    needs_clarification: bool | None = None
    retrieval_mode: str = "auto"


LEXICAL_CASES = [
    BenchmarkCase("member launch", "青柚会员计划什么时候上线？", "青柚会员计划", ("2026-08-18 19:30",), ("2026-09-05",)),
    BenchmarkCase("member budget", "青柚会员计划要花多少钱？", "青柚会员计划", ("21.6 万元",), ("4.2 万元",)),
    BenchmarkCase("member owner", "青柚会员计划谁负责？", "青柚会员计划", ("沈知夏",), ("韩序",)),
    BenchmarkCase("member id", "QY-MEMBER-2026 是哪份资料？", "青柚会员计划", ("QY-MEMBER-2026",), ("QY-HARDWARE-2026",)),
    BenchmarkCase("hardware launch", "青柚硬件巡检上线时间是什么？", "青柚硬件巡检", ("2026-09-05 10:00",), ("2026-08-18",)),
    BenchmarkCase("hardware budget", "青柚硬件巡检预算是多少？", "青柚硬件巡检", ("4.2 万元",), ("21.6 万元",)),
    BenchmarkCase("hardware owner", "青柚硬件巡检负责人是谁？", "青柚硬件巡检", ("韩序",), ("沈知夏",)),
    BenchmarkCase("invoice type", "蓝鲸发票规则支持什么发票？", "蓝鲸发票规则", ("电子普通发票",), ("BJ-REFUND-42",)),
    BenchmarkCase("invoice window", "蓝鲸发票多久能开？", "蓝鲸发票规则", ("3 个工作日",), ("退款",)),
    BenchmarkCase("invoice owner", "蓝鲸发票规则负责人是谁？", "蓝鲸发票规则", ("陆芷",), ("银行卡号",)),
    BenchmarkCase("refund trigger", "蓝鲸退款流程什么时候触发？", "蓝鲸退款流程", ("取消订单",), ("电子普通发票",)),
    BenchmarkCase("refund code", "蓝鲸退款流程的升级码是什么？", "蓝鲸退款流程", ("BJ-REFUND-42",), ("银行卡号",)),
    BenchmarkCase("refund action", "蓝鲸退款流程第一步怎么处理？", "蓝鲸退款流程", ("先安抚情绪", "核对订单号"), ("付款后 3 个工作日",)),
    BenchmarkCase("equipment keeper", "雪松设备清单谁保管？", "雪松设备清单", ("乔澜",), ("任屿",)),
    BenchmarkCase("router location", "备用路由器放在哪里？", "雪松设备清单", ("B2-06",), ("B2-08",)),
    BenchmarkCase("mic count", "直播麦克风有几支？", "雪松设备清单", ("直播麦克风", "3"), ("采集卡",)),
    BenchmarkCase("content publish", "星河内容排期什么时候发布？", "星河内容排期", ("2026-08-22 12:00",), ("2026-08-28",)),
    BenchmarkCase("content reviewer", "星河内容排期审核人是谁？", "星河内容排期", ("白珩",), ("许棠",)),
    BenchmarkCase("content key safety", "星河内容排期发布前要复核什么？", "星河内容排期", ("截图是否含 Key",), ("优惠码",)),
    BenchmarkCase("course coupon", "云朵课程报名优惠码是什么？", "云朵课程报名", ("YUNDOU-CLASS-66",), ("YD-TEACHER-2026",)),
    BenchmarkCase("course deadline", "云朵课程报名截止日期是哪天？", "云朵课程报名", ("2026-08-28",), ("2026-09-03",)),
    BenchmarkCase("course quota", "云朵课程报名有多少名额？", "云朵课程报名", ("60 人",), ("程砚",)),
    BenchmarkCase("teacher", "云朵课程讲师安排主讲人是谁？", "云朵课程讲师安排", ("程砚",), ("许棠",)),
    BenchmarkCase("assistant", "云朵课程讲师安排助教是谁？", "云朵课程讲师安排", ("米洛",), ("YUNDOU-CLASS-66",)),
    BenchmarkCase("security forbidden", "资料安全红线禁止导入什么？", "资料安全红线", ("身份证号", "完整 API Key"), ("YUNDOU-CLASS-66",)),
    BenchmarkCase("security action", "发现敏感资料时该怎么做？", "资料安全红线", ("停止导入", "脱敏"), ("7 天体验优惠券",)),
    BenchmarkCase("import formats", "知识库导入规范支持哪些格式？", "知识库导入规范", ("纯文本", "Markdown"), ("电子普通发票",)),
    BenchmarkCase("chunking principle", "知识库导入规范的切片原则是什么？", "知识库导入规范", ("同一事实组", "同一切片"), ("银行卡号",)),
    BenchmarkCase("delete rule", "资料删除后还会进入 prompt 吗？", "知识库导入规范", ("不再进入检索结果", "不再注入 prompt"), ("继续读取旧数据",)),
    BenchmarkCase("tone principle", "情绪陪伴话术怎么回复低落用户？", "情绪陪伴话术", ("先接住情绪", "不要一上来讲大道理"), ("退款",)),
    BenchmarkCase("tone pace", "情绪陪伴话术的节奏是什么？", "情绪陪伴话术", ("短句", "慢一点"), ("60 人",)),
    BenchmarkCase("desktop db", "桌面版 SQLite 数据库在哪里？", "桌面数据迁移说明", ("Electron userData/backend/suoyi.sqlite",), ("backend/data",)),
    BenchmarkCase("migration fallback", "桌面数据迁移失败后怎么回退？", "桌面数据迁移说明", ("localStorage fallback", "继续读取旧数据"), ("不再注入 prompt",)),
    BenchmarkCase("api key migration", "桌面迁移会把 API Key 放进 SQLite 吗？", "桌面数据迁移说明", ("API Key 不进入 SQLite",), ("完整 API Key",)),
    BenchmarkCase("generic owner", "负责人是谁？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic launch", "上线窗口是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic coupon", "优惠码是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("unrelated dinner", "今晚适合吃什么？", None, should_inject=False),
    BenchmarkCase("unrelated weather", "明天会下雨吗？", None, should_inject=False),
    BenchmarkCase("unrelated finance", "帮我预测一下股票走势", None, should_inject=False),
]


HYBRID_CASES = [
    BenchmarkCase("renewal paraphrase", "老用户续费提醒一开始要先做什么？", "青柚会员计划", ("先确认续费意愿",), ("韩序",), retrieval_mode="hybrid"),
    BenchmarkCase("refund paraphrase", "客户要退钱时售后开头先做啥？", "蓝鲸退款流程", ("先安抚情绪", "核对订单号"), ("电子普通发票",), retrieval_mode="hybrid"),
    BenchmarkCase("privacy paraphrase", "别把银行卡和密钥塞进资料库是哪份规范？", "资料安全红线", ("银行卡号", "完整 API Key"), ("YUNDOU-CLASS-66",), retrieval_mode="hybrid"),
    BenchmarkCase("deleted prompt wording", "删掉资料以后还应该给模型参考吗？", "知识库导入规范", ("不再注入 prompt",), ("继续读取旧数据",), retrieval_mode="hybrid"),
    BenchmarkCase("emotion paraphrase", "用户难过时别急着讲道理应该按哪条话术？", "情绪陪伴话术", ("先接住情绪", "不要一上来讲大道理"), ("退款",), retrieval_mode="hybrid"),
    BenchmarkCase("migration paraphrase", "换桌面版后本地数据库文件在什么位置？", "桌面数据迁移说明", ("Electron userData/backend/suoyi.sqlite",), ("backend/data",), retrieval_mode="hybrid"),
    BenchmarkCase("coupon paraphrase", "云朵课的优惠口令是哪一个？", "云朵课程报名", ("YUNDOU-CLASS-66",), ("YD-TEACHER-2026",), retrieval_mode="hybrid"),
    BenchmarkCase("reviewer paraphrase", "星河发布内容由谁审核？", "星河内容排期", ("白珩",), ("许棠",), retrieval_mode="hybrid"),
]


def seed_realistic_documents(client: TestClient) -> None:
    for payload in REALISTIC_DOCUMENTS:
        response = client.post("/knowledge/sources", json=payload)
        assert response.status_code == 201


def evaluate_case(client: TestClient, case: BenchmarkCase, *, runtime: dict | None = None) -> str | None:
    payload: dict = {"query": case.query, "topK": 3, "retrievalMode": case.retrieval_mode}
    if runtime is not None:
        payload["embeddingRuntimeConfig"] = runtime
    response = client.post("/knowledge/search", json=payload)
    if response.status_code != 200:
        return f"{case.name}: HTTP {response.status_code}"
    data = response.json()
    prompt_context = data["promptContext"]

    if data["shouldInject"] is not case.should_inject:
        return f"{case.name}: shouldInject={data['shouldInject']} expected {case.should_inject}"
    if case.needs_clarification is not None and data["needsClarification"] is not case.needs_clarification:
        return f"{case.name}: needsClarification={data['needsClarification']} expected {case.needs_clarification}"
    if case.expected_source is None:
        if data["hits"] or prompt_context:
            return f"{case.name}: expected no hits but got {[hit['sourceTitle'] for hit in data['hits']]}"
        return None
    if not data["hits"]:
        return f"{case.name}: no hits"
    actual_source = data["hits"][0]["sourceTitle"]
    if actual_source != case.expected_source:
        return f"{case.name}: top1={actual_source!r} expected {case.expected_source!r}"
    for text in case.required_text:
        if text not in prompt_context:
            return f"{case.name}: missing required text {text!r}"
    for text in case.forbidden_text:
        if text in prompt_context:
            return f"{case.name}: leaked forbidden text {text!r}"
    return None


def test_realistic_markdown_rag_benchmark_precision_and_no_answer_cases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-realistic.sqlite"))

    assert len(REALISTIC_DOCUMENTS) == 12
    assert len(LEXICAL_CASES) == 40

    with TestClient(app) as client:
        seed_realistic_documents(client)
        failures = [failure for case in LEXICAL_CASES if (failure := evaluate_case(client, case))]

    assert not failures, "\n".join(failures)


def test_realistic_hybrid_benchmark_with_mock_embeddings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-realistic.sqlite"))
    runtime = realistic_runtime_config()

    with TestClient(app) as client:
        seed_realistic_documents(client)
        reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert reindex.status_code == 200
        assert reindex.json()["failed"] == 0
        assert reindex.json()["indexed"] >= len(REALISTIC_DOCUMENTS)

        failures = [failure for case in HYBRID_CASES if (failure := evaluate_case(client, case, runtime=runtime))]

    assert not failures, "\n".join(failures)
