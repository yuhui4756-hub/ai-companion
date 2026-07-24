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
密钥边界：API Key 不进入 SQLite，需要用户在桌面版重新填写。
""".strip(),
    },
]


def build_distractor_documents(count: int = 24) -> list[dict[str, str]]:
    owners = ["林溪", "唐晚", "周屿", "姜宁", "叶舟", "宋澜", "顾南", "许知", "温然", "陆予", "夏禾", "秦越"]
    topics = ["运营复盘", "社群活动", "硬件借用", "课程排班", "发票答疑", "退款跟进"]
    documents: list[dict[str, str]] = []
    for index in range(1, count + 1):
        owner = owners[(index - 1) % len(owners)]
        topic = topics[(index - 1) % len(topics)]
        title = f"萤火{topic}档案 {index:02d}"
        documents.append(
            {
                "title": title,
                "sourceType": "markdown",
                "content": f"""
# {title}

## 项目档案
编号：YH-DISTRACTOR-2026-{index:02d}
上线窗口：2026-10-{(index % 20) + 1:02d} 10:30
预算金额：{3 + index / 10:.1f} 万元
负责人：{owner}
说明：这是一份用于扩大知识库规模的干扰资料，主题是{topic}，不应覆盖核心评测资料。

## 操作边界
规则：只回答本档案自己的编号、预算、负责人和上线窗口，不替代其他资料来源。
""".strip(),
            }
        )
    return documents


DISTRACTOR_DOCUMENTS = build_distractor_documents()
BENCHMARK_DOCUMENTS = [*REALISTIC_DOCUMENTS, *DISTRACTOR_DOCUMENTS]


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
    BenchmarkCase("member renewal coupon", "青柚会员计划会发什么优惠券？", "青柚会员计划", ("7 天体验优惠券",), ("QY-HARDWARE-2026",)),
    BenchmarkCase("member privacy boundary", "青柚会员计划不能导入什么？", "青柚会员计划", ("未授权手机号",), ("备用路由器",)),
    BenchmarkCase("member launch owner combined", "青柚会员计划上线窗口和负责人是什么？", "青柚会员计划", ("2026-08-18 19:30", "沈知夏"), ("韩序",)),
    BenchmarkCase("member first step", "青柚会员计划续费提醒先做什么？", "青柚会员计划", ("先确认续费意愿",), ("投屏",)),
    BenchmarkCase("member exact title", "青柚会员计划是哪一个编号？", "青柚会员计划", ("QY-MEMBER-2026",), ("QY-HARDWARE-2026",)),
    BenchmarkCase("hardware coverage", "青柚硬件巡检覆盖哪些设备？", "青柚硬件巡检", ("会议室投屏", "备用路由器", "直播麦克风"), ("7 天体验优惠券",)),
    BenchmarkCase("hardware exact title", "青柚硬件巡检是哪一个编号？", "青柚硬件巡检", ("QY-HARDWARE-2026",), ("QY-MEMBER-2026",)),
    BenchmarkCase("hardware router", "青柚硬件巡检是否覆盖备用路由器？", "青柚硬件巡检", ("备用路由器",), ("7 天体验优惠券",)),
    BenchmarkCase("hardware mic", "青柚硬件巡检有没有直播麦克风？", "青柚硬件巡检", ("直播麦克风",), ("沈知夏",)),
    BenchmarkCase("hardware projector", "青柚硬件巡检有没有会议室投屏？", "青柚硬件巡检", ("会议室投屏",), ("续费",)),
    BenchmarkCase("invoice required fields", "蓝鲸发票规则需要用户提供什么？", "蓝鲸发票规则", ("抬头", "税号", "接收邮箱"), ("BJ-REFUND-42",)),
    BenchmarkCase("invoice not required", "蓝鲸发票规则不需要提供什么？", "蓝鲸发票规则", ("银行卡号",), ("先安抚情绪",)),
    BenchmarkCase("invoice id", "BJ-INVOICE-2026 对应哪份资料？", "蓝鲸发票规则", ("BJ-INVOICE-2026",), ("BJ-REFUND-42",)),
    BenchmarkCase("invoice owner variant", "蓝鲸发票规则由谁维护？", "蓝鲸发票规则", ("陆芷",), ("人工复核",)),
    BenchmarkCase("invoice payment timing", "付款后几天内可以开蓝鲸发票？", "蓝鲸发票规则", ("3 个工作日",), ("取消订单",)),
    BenchmarkCase("invoice email", "蓝鲸发票规则里接收邮箱有什么用？", "蓝鲸发票规则", ("接收邮箱",), ("退款凭证",)),
    BenchmarkCase("refund id", "BJ-REFUND-42 是什么流程的升级码？", "蓝鲸退款流程", ("BJ-REFUND-42",), ("BJ-INVOICE-2026",)),
    BenchmarkCase("refund evidence", "蓝鲸退款流程证据来源是什么？", "蓝鲸退款流程", ("订单截图", "订单号"), ("税号",)),
    BenchmarkCase("refund no memory", "蓝鲸退款流程不要把什么写入长期记忆？", "蓝鲸退款流程", ("退款凭证", "长期记忆"), ("电子普通发票",)),
    BenchmarkCase("refund cancel order", "用户取消订单时按哪个流程处理？", "蓝鲸退款流程", ("取消订单",), ("付款后 3 个工作日",)),
    BenchmarkCase("refund bank card", "蓝鲸退款流程要不要用户发银行卡号？", "蓝鲸退款流程", ("不要要求用户", "银行卡号"), ("税号",)),
    BenchmarkCase("refund manual review", "蓝鲸退款流程最后提交什么复核？", "蓝鲸退款流程", ("人工复核",), ("陆芷",)),
    BenchmarkCase("equipment borrow window", "雪松设备清单借用窗口是什么？", "雪松设备清单", ("工作日 10:00-18:00",), ("2026-08-22",)),
    BenchmarkCase("equipment cabinet", "雪松设备清单储物柜在哪里？", "雪松设备清单", ("B2 储物柜",), ("Electron userData",)),
    BenchmarkCase("capture card location", "采集卡放在哪里？", "雪松设备清单", ("B2-08",), ("B2-06",)),
    BenchmarkCase("microphone location", "直播麦克风位置是哪里？", "雪松设备清单", ("B2-03",), ("B2-08",)),
    BenchmarkCase("router count", "雪松设备清单有几台备用路由器？", "雪松设备清单", ("备用路由器", "2"), ("采集卡 | 1",)),
    BenchmarkCase("equipment id", "XS-EQUIP-2026 是哪份清单？", "雪松设备清单", ("XS-EQUIP-2026",), ("XH-CONTENT-2026",)),
    BenchmarkCase("content id", "星河内容排期编号是什么？", "星河内容排期", ("XH-CONTENT-2026",), ("XS-EQUIP-2026",)),
    BenchmarkCase("content owner", "星河内容排期负责人是谁？", "星河内容排期", ("任屿",), ("许棠",)),
    BenchmarkCase("content launch theme", "星河内容排期首发内容是什么？", "星河内容排期", ("本地优先与隐私可控",), ("优惠码",)),
    BenchmarkCase("content screenshot key", "星河内容排期发布前截图要检查什么？", "星河内容排期", ("截图是否含 Key",), ("银行卡号",)),
    BenchmarkCase("content id reviewer", "XH-CONTENT-2026 对应谁审核？", "星河内容排期", ("白珩",), ("许棠",)),
    BenchmarkCase("content release field", "星河内容排期发布字段有哪些？", "星河内容排期", ("发布时间", "负责人", "审核人"), ("优惠码",)),
    BenchmarkCase("course id", "YD-COURSE-2026 是哪份资料？", "云朵课程报名", ("YD-COURSE-2026",), ("YD-TEACHER-2026",)),
    BenchmarkCase("course owner", "云朵课程报名负责人是谁？", "云朵课程报名", ("许棠",), ("程砚",)),
    BenchmarkCase("course coupon phrase", "云朵课程报名优惠口令是什么？", "云朵课程报名", ("YUNDOU-CLASS-66",), ("YD-TEACHER-2026",)),
    BenchmarkCase("course coupon scope", "云朵课程报名优惠码能用于其他活动吗？", "云朵课程报名", ("不可用于其他活动",), ("上课时间",)),
    BenchmarkCase("course seats", "云朵课程报名名额有多少人？", "云朵课程报名", ("60 人",), ("米洛",)),
    BenchmarkCase("course deadline variant", "云朵课程报名什么时候截止？", "云朵课程报名", ("2026-08-28",), ("2026-09-03",)),
    BenchmarkCase("teacher id", "YD-TEACHER-2026 是哪份资料？", "云朵课程讲师安排", ("YD-TEACHER-2026",), ("YD-COURSE-2026",)),
    BenchmarkCase("teacher topic", "云朵课程讲师安排主题是什么？", "云朵课程讲师安排", ("本地记忆与知识库边界",), ("优惠码",)),
    BenchmarkCase("teacher time", "云朵课程讲师安排上课时间是什么？", "云朵课程讲师安排", ("2026-09-03 20:00",), ("2026-08-28",)),
    BenchmarkCase("teacher assistant variant", "云朵课程讲师安排的助教叫什么？", "云朵课程讲师安排", ("米洛",), ("许棠",)),
    BenchmarkCase("teacher speaker variant", "云朵课程讲师安排谁来主讲？", "云朵课程讲师安排", ("程砚",), ("许棠",)),
    BenchmarkCase("teacher no coupon", "云朵课程讲师安排里有没有优惠码？", "云朵课程讲师安排", ("YD-TEACHER-2026",), ("YUNDOU-CLASS-66",)),
    BenchmarkCase("security sensitive action", "资料安全红线遇到敏感资料怎么处理？", "资料安全红线", ("停止导入", "脱敏"), ("YUNDOU-CLASS-66",)),
    BenchmarkCase("security allowed", "资料安全红线哪些资料可以导入？", "资料安全红线", ("产品说明", "学习笔记", "公开资料摘要"), ("银行卡号",)),
    BenchmarkCase("security cookie", "资料安全红线能导入 Cookie 吗？", "资料安全红线", ("Cookie",), ("云朵课程",)),
    BenchmarkCase("security scan code", "资料安全红线提到扫码凭证了吗？", "资料安全红线", ("扫码凭证",), ("订单截图",)),
    BenchmarkCase("security api key", "资料安全红线关于 API Key 怎么说？", "资料安全红线", ("完整 API Key",), ("API Key 不进入 SQLite",)),
    BenchmarkCase("security unauthorized chat", "资料安全红线能导入未授权聊天记录吗？", "资料安全红线", ("未授权聊天记录",), ("本地记忆",)),
    BenchmarkCase("import id", "KB-IMPORT-2026 是哪份规范？", "知识库导入规范", ("KB-IMPORT-2026",), ("CARE-TONE-2026",)),
    BenchmarkCase("import deletion rule", "知识库导入规范删除规则是什么？", "知识库导入规范", ("不再进入检索结果", "不再注入 prompt"), ("localStorage fallback",)),
    BenchmarkCase("import chunking variant", "知识库导入规范怎么做切片？", "知识库导入规范", ("同一事实组", "同一切片"), ("电子普通发票",)),
    BenchmarkCase("import markdown", "知识库导入规范支持 Markdown 吗？", "知识库导入规范", ("Markdown",), ("PDF",)),
    BenchmarkCase("import plain text", "知识库导入规范支持纯文本吗？", "知识库导入规范", ("纯文本",), ("Cookie",)),
    BenchmarkCase("import no prompt after delete", "知识库导入规范说删除后还注入 prompt 吗？", "知识库导入规范", ("不再注入 prompt",), ("继续读取旧数据",)),
    BenchmarkCase("tone id", "CARE-TONE-2026 是哪份资料？", "情绪陪伴话术", ("CARE-TONE-2026",), ("KB-IMPORT-2026",)),
    BenchmarkCase("tone boundary", "情绪陪伴话术边界是什么？", "情绪陪伴话术", ("不要承诺替用户做现实世界决定",), ("退款",)),
    BenchmarkCase("tone pause", "情绪陪伴话术允许用户怎样？", "情绪陪伴话术", ("允许用户暂停",), ("人工复核",)),
    BenchmarkCase("tone choices", "情绪陪伴话术要给用户什么感觉？", "情绪陪伴话术", ("给出选择",), ("60 人",)),
    BenchmarkCase("tone no lecture", "情绪陪伴话术为什么不要急着讲道理？", "情绪陪伴话术", ("不要一上来讲大道理",), ("退款",)),
    BenchmarkCase("migration id", "DESKTOP-MIGRATION-2026 是哪份说明？", "桌面数据迁移说明", ("DESKTOP-MIGRATION-2026",), ("CARE-TONE-2026",)),
    BenchmarkCase("migration api key refill", "桌面数据迁移说明 API Key 怎么办？", "桌面数据迁移说明", ("需要用户在桌面版重新填写",), ("完整 API Key",)),
    BenchmarkCase("migration fallback name", "桌面数据迁移说明提到哪个 fallback？", "桌面数据迁移说明", ("localStorage fallback",), ("不再注入 prompt",)),
    BenchmarkCase("migration db path variant", "桌面版数据库路径是什么？", "桌面数据迁移说明", ("Electron userData/backend/suoyi.sqlite",), ("backend/data",)),
    BenchmarkCase("migration failure behavior", "迁移失败时桌面数据迁移说明怎么处理？", "桌面数据迁移说明", ("继续读取旧数据",), ("不再进入检索结果",)),
    BenchmarkCase("generic id", "编号是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic budget", "预算是多少？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic deadline", "截止日期是哪天？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic charge", "谁负责？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic upgrade code", "升级码是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("unrelated song", "帮我写一首歌", None, should_inject=False),
    BenchmarkCase("unrelated travel", "周末适合去哪旅游？", None, should_inject=False),
    BenchmarkCase("unrelated math", "帮我算一下 123 乘以 456", None, should_inject=False),
    BenchmarkCase("unrelated recipe", "番茄炒蛋怎么做？", None, should_inject=False),
    BenchmarkCase("unrelated movie", "推荐一部电影", None, should_inject=False),
]


DISTRACTOR_CASES = [
    BenchmarkCase(
        "large corpus distractor owner 07",
        "萤火运营复盘档案 07 的负责人是谁？",
        "萤火运营复盘档案 07",
        ("顾南",),
        ("YH-DISTRACTOR-2026-08", "沈知夏"),
    ),
    BenchmarkCase(
        "large corpus distractor budget 12",
        "萤火退款跟进档案 12 的预算是多少？",
        "萤火退款跟进档案 12",
        ("4.2 万元",),
        ("21.6 万元", "YH-DISTRACTOR-2026-11"),
    ),
    BenchmarkCase(
        "large corpus distractor id 18",
        "YH-DISTRACTOR-2026-18 是哪份资料？",
        "萤火退款跟进档案 18",
        ("YH-DISTRACTOR-2026-18",),
        ("YH-DISTRACTOR-2026-17", "BJ-REFUND-42"),
    ),
    BenchmarkCase(
        "large corpus distractor launch 24",
        "萤火退款跟进档案 24 什么时候上线？",
        "萤火退款跟进档案 24",
        ("2026-10-05 10:30",),
        ("2026-10-04", "2026-08-18"),
    ),
    BenchmarkCase(
        "large corpus generic owner remains clarify",
        "这些萤火档案的负责人是谁？",
        None,
        should_inject=False,
        needs_clarification=True,
    ),
]

LEXICAL_CASES.extend(DISTRACTOR_CASES)


HYBRID_CASES = [
    BenchmarkCase("renewal paraphrase", "老用户续费提醒一开始要先做什么？", "青柚会员计划", ("先确认续费意愿",), ("韩序",), retrieval_mode="hybrid"),
    BenchmarkCase("refund paraphrase", "客户要退钱时售后开头先做啥？", "蓝鲸退款流程", ("先安抚情绪", "核对订单号"), ("电子普通发票",), retrieval_mode="hybrid"),
    BenchmarkCase("privacy paraphrase", "别把银行卡和密钥塞进资料库是哪份规范？", "资料安全红线", ("银行卡号", "完整 API Key"), ("YUNDOU-CLASS-66",), retrieval_mode="hybrid"),
    BenchmarkCase("deleted prompt wording", "删掉资料以后还应该给模型参考吗？", "知识库导入规范", ("不再注入 prompt",), ("继续读取旧数据",), retrieval_mode="hybrid"),
    BenchmarkCase("emotion paraphrase", "用户难过时别急着讲道理应该按哪条话术？", "情绪陪伴话术", ("先接住情绪", "不要一上来讲大道理"), ("退款",), retrieval_mode="hybrid"),
    BenchmarkCase("migration paraphrase", "换桌面版后本地数据库文件在什么位置？", "桌面数据迁移说明", ("Electron userData/backend/suoyi.sqlite",), ("backend/data",), retrieval_mode="hybrid"),
    BenchmarkCase("coupon paraphrase", "云朵课的优惠口令是哪一个？", "云朵课程报名", ("YUNDOU-CLASS-66",), ("YD-TEACHER-2026",), retrieval_mode="hybrid"),
    BenchmarkCase("reviewer paraphrase", "星河发布内容由谁审核？", "星河内容排期", ("白珩",), ("许棠",), retrieval_mode="hybrid"),
    BenchmarkCase("renewal coupon paraphrase", "老会员续费会给几天的券？", "青柚会员计划", ("7 天体验优惠券",), ("备用路由器",), retrieval_mode="hybrid"),
    BenchmarkCase("hardware paraphrase", "会议室投屏和路由器巡检属于哪份资料？", "青柚硬件巡检", ("会议室投屏", "备用路由器"), ("续费",), retrieval_mode="hybrid"),
    BenchmarkCase("invoice paraphrase", "付款后多久能拿到电子发票？", "蓝鲸发票规则", ("3 个工作日", "电子普通发票"), ("BJ-REFUND-42",), retrieval_mode="hybrid"),
    BenchmarkCase("refund memory paraphrase", "退钱凭证能不能写进长期记忆？", "蓝鲸退款流程", ("不要把退款凭证写入长期记忆",), ("电子普通发票",), retrieval_mode="hybrid"),
    BenchmarkCase("equipment paraphrase", "B2 储物柜里备用路由器是哪一行？", "雪松设备清单", ("备用路由器", "B2-06"), ("采集卡",), retrieval_mode="hybrid"),
    BenchmarkCase("content screenshot paraphrase", "发星河内容前要确认截图里没有什么？", "星河内容排期", ("截图是否含 Key",), ("Cookie",), retrieval_mode="hybrid"),
    BenchmarkCase("teacher paraphrase", "云朵课讲本地记忆边界的人是谁？", "云朵课程讲师安排", ("程砚",), ("YUNDOU-CLASS-66",), retrieval_mode="hybrid"),
    BenchmarkCase("security stop paraphrase", "资料里发现身份证或密钥时第一步怎么办？", "资料安全红线", ("停止导入", "脱敏"), ("订单号",), retrieval_mode="hybrid"),
    BenchmarkCase("import format paraphrase", "现在知识库可以喂哪些文本格式？", "知识库导入规范", ("纯文本", "Markdown"), ("电子普通发票",), retrieval_mode="hybrid"),
    BenchmarkCase("tone choice paraphrase", "安慰用户时别命令他，要先怎么回应？", "情绪陪伴话术", ("先接住情绪", "给出选择"), ("退款",), retrieval_mode="hybrid"),
    BenchmarkCase("migration key paraphrase", "桌面迁移会不会把模型密钥写进数据库？", "桌面数据迁移说明", ("API Key 不进入 SQLite",), ("完整 API Key",), retrieval_mode="hybrid"),
    BenchmarkCase("migration fallback paraphrase", "桌面迁移失败还能读旧浏览器数据吗？", "桌面数据迁移说明", ("localStorage fallback", "继续读取旧数据"), ("不再注入 prompt",), retrieval_mode="hybrid"),
]


def seed_realistic_documents(client: TestClient) -> None:
    for payload in BENCHMARK_DOCUMENTS:
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
    assert len(BENCHMARK_DOCUMENTS) >= 36
    assert len(LEXICAL_CASES) >= 120
    assert len(LEXICAL_CASES) + len(HYBRID_CASES) >= 140

    with TestClient(app) as client:
        seed_realistic_documents(client)
        failures = [failure for case in LEXICAL_CASES if (failure := evaluate_case(client, case))]

    assert not failures, "\n".join(failures)


def test_realistic_hybrid_benchmark_with_mock_embeddings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-realistic.sqlite"))
    runtime = realistic_runtime_config()

    assert len(HYBRID_CASES) >= 20

    with TestClient(app) as client:
        seed_realistic_documents(client)
        reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert reindex.status_code == 200
        assert reindex.json()["failed"] == 0
        assert reindex.json()["indexed"] >= len(BENCHMARK_DOCUMENTS)

        failures = [failure for case in HYBRID_CASES if (failure := evaluate_case(client, case, runtime=runtime))]

    assert not failures, "\n".join(failures)
