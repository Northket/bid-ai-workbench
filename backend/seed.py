"""演示数据种子：首次启动时写入，所有演示数据均带明确标记。

说明：招标公告为演示数据（is_demo=True），不代表真实公告；
真实数据源（深圳公共资源交易平台）接入接口已在 API 层预留。
"""
import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import (Announcement, BidRequirement, BidTask, ChatMessage, ChatSession,
                    Deliverable, DocumentFile, HistoricalProject, Milestone,
                    TenderProject)

BASE = date(2026, 10, 30)


def seed_if_empty(db: Session) -> bool:
    if db.query(TenderProject).count() > 0:
        return False
    _seed_projects(db)
    _seed_announcements(db)
    _seed_documents(db)
    _seed_requirements(db)
    _seed_history(db)
    _seed_chat(db)
    db.commit()
    return True


def _seed_projects(db: Session):
    rows = [
        # code, name, region, type, method, tenderer, agency, budget(万), publish, deadline, stage, participating, favorite, desc
        ("SZ2026-SG001", "示例中学泥岗校区改扩建工程施工总承包", "罗湖区", "房建", "公开招标",
         "示例市建筑工务署教育工程管理中心", "示例市国际招标有限公司", 28600,
         BASE - timedelta(days=25), BASE + timedelta(days=12), "投标中", True, True,
         "项目位于罗湖区泥岗片区，总建筑面积约8.6万平方米，包含教学楼、宿舍楼、体育馆及地下室工程。"),
        ("SZ2026-DL002", "龙华区观澜大道市政道路改造工程", "龙华区", "市政", "公开招标",
         "示例市交通运输局龙华管理局", "示例市机电设备招标中心", 15400,
         BASE - timedelta(days=18), BASE + timedelta(days=8), "投标中", True, False,
         "观澜大道（梅观高速-高尔夫大道）改造，全长约4.2公里，含道路、交通、给排水、照明及景观工程。"),
        ("SZ2026-MQ003", "前海自贸区T3栋超高层写字楼幕墙工程", "前海合作区", "装饰装修", "公开招标",
         "示例市前海开发投资控股有限公司", "示例市建材交易集团", 9800,
         BASE - timedelta(days=12), BASE + timedelta(days=20), "跟踪中", False, True,
         "T3栋塔楼高度约248米，单元式幕墙约5.6万平方米，含玻璃幕墙、石材幕墙及雨棚工程。"),
        ("SZ2026-WL004", "宝安区固戍污水处理厂提标扩建工程", "宝安区", "水利", "公开招标",
         "示例市水务局宝安管理局", "示例市水务工程招标代理有限公司", 21300,
         BASE - timedelta(days=40), BASE - timedelta(days=5), "投标中", True, False,
         "现状20万吨/日处理能力提标至35万吨/日，含深度处理单元、污泥处置及厂区配套工程。"),
        ("SZ2026-FM005", "南山区智慧城市感知体系终端安装工程", "南山区", "机电安装", "邀请招标",
         "示例市南山区政务服务和数据管理局", "示例市信息工程招标有限公司", 4600,
         BASE - timedelta(days=9), BASE + timedelta(days=15), "跟踪中", False, False,
         "全区约1200套智能感知终端安装调试，含杆件、供电、通信及平台接入。"),
        ("SZ2026-GM006", "光明科学城大科学装置区配套道路工程", "光明区", "市政", "公开招标",
         "示例市光明区建筑工务署", "示例市国际招标有限公司", 12750,
         BASE - timedelta(days=6), BASE + timedelta(days=26), "跟踪中", False, True,
         "大科学装置区周边三条配套道路，总长约3.1公里，城市主干道标准。"),
        ("SZ2027-SG007", "福田区中小学校舍安全隐患整治工程（第二批）", "福田区", "房建", "公开招标",
         "示例市福田区教育局", "示例市建材交易集团", 7400,
         BASE - timedelta(days=60), BASE - timedelta(days=20), "已结束", False, False,
         "辖区12所学校抗震加固、消防设施改造及外立面整治。"),
        ("SZ2027-ZX008", "坪山区生物医药产业园区标准厂房及配套工程", "坪山区", "房建", "公开招标",
         "示例市坪山区产业投资服务有限公司", "示例市机电设备招标中心", 33800,
         BASE - timedelta(days=3), BASE + timedelta(days=32), "跟踪中", False, False,
         "总建筑面积约12.8万平方米，含4栋标准厂房、研发中心及员工宿舍。"),
        ("SZ2026-JD009", "地铁14号线坳背站附属结构及接驳工程", "龙岗区", "交通", "公开招标",
         "示例市地铁集团有限公司", "示例市国际招标有限公司", 8900,
         BASE - timedelta(days=33), BASE - timedelta(days=2), "已结束", False, False,
         "车站C/D出入口及地下接驳通道施工，含围护结构、降水及监控量测。"),
        ("SZ2026-LH010", "罗湖区老旧小区改造提升工程（桂园片区）", "罗湖区", "房建", "公开招标",
         "示例市罗湖区住房和建设局", "示例市建材交易集团", 6200,
         BASE - timedelta(days=15), BASE + timedelta(days=18), "投标中", True, False,
         "桂园片区9个老旧小区综合改造，含管网更新、外立面翻新、加装电梯及小区智慧化。"),
        ("SZ2026-YT011", "盐田区海滨栈道修复及景观提升工程", "盐田区", "园林绿化", "公开招标",
         "示例市盐田区城市管理和综合执法局", "示例市水务工程招标代理有限公司", 5300,
         BASE - timedelta(days=21), BASE + timedelta(days=5), "投标中", True, True,
         "大梅沙-小梅沙段栈道修复约2.8公里，含景观照明、护栏及配套设施。"),
        ("SZ2027-LG012", "龙岗区文体中心室内精装修工程", "龙岗区", "装饰装修", "公开招标",
         "示例市龙岗区文化广电旅游体育局", "示例市国际招标有限公司", 11200,
         BASE - timedelta(days=1), BASE + timedelta(days=40), "跟踪中", False, False,
         "文体中心剧院、图书馆及展览馆室内精装修，装修面积4.3万平方米。"),
    ]
    for r in rows:
        db.add(TenderProject(
            code=r[0], name=r[1], region=r[2], project_type=r[3], tender_method=r[4],
            tenderer=r[5], agency=r[6], budget=r[7], publish_date=r[8], deadline=r[9],
            stage=r[10], participating=r[11], favorite=r[12], description=r[13],
        ))
    db.flush()

    # 为参与投标的项目生成任务/节点/成果示例
    participating = db.query(TenderProject).filter(TenderProject.participating == True).all()  # noqa: E712
    for p in participating:
        db.add_all([
            BidTask(project_id=p.id, title="招标文件研读与疑点汇总", owner="李工",
                    due_date=BASE + timedelta(days=2), status="已完成", priority="high"),
            BidTask(project_id=p.id, title="编制施工组织设计（技术标）", owner="王工",
                    due_date=BASE + timedelta(days=6), status="进行中", priority="high"),
            BidTask(project_id=p.id, title="商务标报价测算与复核", owner="赵工",
                    due_date=BASE + timedelta(days=8), status="进行中", priority="high"),
            BidTask(project_id=p.id, title="资信标材料收集（资质/业绩/财务）", owner="陈工",
                    due_date=BASE + timedelta(days=4), status="进行中", priority="medium"),
            BidTask(project_id=p.id, title="投标文件合稿、盖章与封装", owner="周工",
                    due_date=BASE + timedelta(days=10), status="待办", priority="high"),
        ])
        db.add_all([
            Milestone(project_id=p.id, name="招标文件获取截止", date=BASE + timedelta(days=1), kind="其他",
                      description="确认已获取完整招标文件及图纸"),
            Milestone(project_id=p.id, name="答疑与澄清截止", date=BASE + timedelta(days=3), kind="答疑",
                      description="提交书面疑问"),
            Milestone(project_id=p.id, name="投标截止（开标）", date=p.deadline or BASE, kind="开标",
                      description="完成投标文件递交"),
        ])
        db.add_all([
            Deliverable(project_id=p.id, name=f"{p.code}-技术标-初稿.docx", category="技术方案",
                        version="V0.9", size=2457600),
            Deliverable(project_id=p.id, name=f"{p.code}-商务报价测算表.xlsx", category="商务报价",
                        version="V1.0", size=389120),
        ])


def _seed_announcements(db: Session):
    projects = db.query(TenderProject).all()
    rows = []
    for i, p in enumerate(projects):
        rows.append(Announcement(
            title=f"{p.name}【招标公告】",
            ann_type="招标公告",
            project_code=p.code,
            source="深圳公共资源交易平台（演示数据）",
            source_url="https://www.szggzy.cn",
            publish_date=p.publish_date,
            content=(f"招标条件：{p.name} 已由相关主管部门批准建设，招标人为 {p.tenderer}，"
                     f"资金来源为财政性资金{'及自筹' if i % 2 else ''}。项目已具备招标条件，现进行公开招标。\n"
                     f"项目概况：{p.description}\n"
                     f"招标控制价：{p.budget:.2f} 万元。\n"
                     f"投标人资格要求：具备相应施工总承包{['一级', '二级', '三级'][i % 3]}及以上资质，"
                     f"项目负责人须具备有效注册建造师证书。\n"
                     f"投标截止时间：{p.deadline}。（本条为演示数据，不代表真实公告）"),
            is_demo=True,
        ))
        if p.stage == "已结束":
            rows.append(Announcement(
                title=f"{p.name}【中标公告】",
                ann_type="中标公告",
                project_code=p.code,
                source="深圳公共资源交易平台（演示数据）",
                source_url="https://www.szggzy.cn",
                publish_date=p.deadline + timedelta(days=3) if p.deadline else None,
                content=(f"项目编号：{p.code}。中标人：示例市第{['一', '二', '三', '五'][i % 4]}建筑工程有限公司；"
                         f"中标价：{p.budget * 0.93:.2f} 万元。公示期为3个工作日。（本条为演示数据，不代表真实公告）"),
                winner=f"示例市第{['一', '二', '三', '五'][i % 4]}建筑工程有限公司",
                win_amount=round(p.budget * 0.93, 2),
                is_demo=True,
            ))
            rows.append(Announcement(
                title=f"{p.name}【开标公告】",
                ann_type="开标公告",
                project_code=p.code,
                source="深圳公共资源交易平台（演示数据）",
                source_url="https://www.szggzy.cn",
                publish_date=p.deadline,
                content=f"项目编号：{p.code}，于 {p.deadline} 在深圳公共资源交易中心开标，共 6 家单位投标。（演示数据）",
                is_demo=True,
            ))
    db.add_all(rows)


def _seed_documents(db: Session):
    p1 = db.query(TenderProject).filter(TenderProject.code == "SZ2026-SG001").first()
    p2 = db.query(TenderProject).filter(TenderProject.code == "SZ2026-DL002").first()
    p3 = db.query(TenderProject).filter(TenderProject.code == "SZ2026-WL004").first()
    demo_result = {
        "is_demo": True,
        "note": "演示解析结果：该记录为演示数据，未接入真实文档解析服务。",
        "sections": [
            {"title": "评标办法", "items": ["综合评估法：技术标40分 + 商务标50分 + 资信标10分",
                                        "技术标合格线24分，商务标最低价得满分"]},
            {"title": "废标条款（节选演示）", "items": [
                "投标文件未按规定格式签字盖章的",
                "投标报价高于招标控制价的",
                "项目经理承担在建项目超过规定数量的"]},
            {"title": "关键时间", "items": ["答疑截止：截标前10日", "投标有效期：90日"]},
        ],
        "suggested_requirements": [
            {"category": "technical", "name": "施工组织设计含深基坑专项方案", "source_text": "技术标准及要求 第3.2条"},
            {"category": "business", "name": "报价不得高于控制价且不低于成本", "source_text": "投标人须知前附表"},
            {"category": "credit", "name": "近三年类似业绩不少于3项", "source_text": "资格审查条件"},
        ],
    }
    db.add_all([
        DocumentFile(original_name="示例中学改扩建工程招标文件.pdf", stored_name="", file_type="pdf",
                     size=8_912_384, project_id=p1.id if p1 else None, status="解析完成",
                     parse_result=json.dumps(demo_result, ensure_ascii=False), is_demo=True),
        DocumentFile(original_name="观澜大道改造工程招标文件及工程量清单.pdf", stored_name="", file_type="pdf",
                     size=12_439_040, project_id=p2.id if p2 else None, status="待解析", is_demo=True),
        DocumentFile(original_name="固戍污水厂提标扩建答疑补遗.docx", stored_name="", file_type="docx",
                     size=812_544, project_id=p3.id if p3 else None, status="解析失败",
                     error_message="演示错误：文档部分内容为扫描件，OCR 通道未接入（演示数据用于展示错误状态）",
                     is_demo=True),
    ])


def _seed_requirements(db: Session):
    p1 = db.query(TenderProject).filter(TenderProject.code == "SZ2026-SG001").first()
    p2 = db.query(TenderProject).filter(TenderProject.code == "SZ2026-DL002").first()
    if not p1:
        return
    rows = [
        # project, category, name, content, source, page, importance, status, confirmed
        (p1, "technical", "施工组织设计编制深度",
         "包含施工部署、进度计划、平面布置、主要施工方案、质量/安全/文明施工保证措施，篇幅不超过200页。",
         "第六章 投标文件格式 6.1", "P88-102", "high", "进行中", False),
        (p1, "technical", "深基坑专项施工方案",
         "地下室开挖深度超过5米，须提供深基坑支护专项方案并附专家论证意见（可中标后补交论证记录）。",
         "第七章 技术标准及要求 3.2", "P156", "high", "未开始", False),
        (p1, "technical", "绿色施工与智慧工地要求",
         "须承诺接入示例市智慧工地监管平台，配置实名制闸机、扬尘噪声在线监测设备。",
         "第七章 技术标准及要求 5.4", "P162", "medium", "已完成", True),
        (p1, "business", "投标报价上限",
         "投标报价不得高于招标控制价 28600 万元，也不得低于企业个别成本。",
         "第二章 投标人须知前附表 3.2", "P15", "high", "进行中", False),
        (p1, "business", "工程量清单报价完整性",
         "分部分项、措施项目、其他项目、规费税金均须报价，不得缺项漏项；暂列金额按给定金额计入。",
         "第五章 工程量清单说明", "P71", "high", "已完成", True),
        (p1, "business", "投标保证金",
         "金额 80 万元，须从基本账户转出，保函形式须为深圳公共资源交易中心认可的电子保函。",
         "第二章 投标人须知前附表 4.1", "P16", "medium", "已完成", True),
        (p1, "credit", "企业资质等级",
         "具备建筑工程施工总承包一级及以上资质，具备有效安全生产许可证。",
         "第一章 招标公告 3.1", "P3", "high", "已完成", True),
        (p1, "credit", "类似工程业绩",
         "近三年（2023年至今）完成至少3项建筑面积5万平方米以上的学校或公共建筑业绩，须提供中标通知书+合同+验收证明。",
         "第一章 招标公告 3.3", "P4", "high", "进行中", False),
        (p1, "credit", "项目经理资格与在建情况",
         "拟派项目经理须为建筑工程专业一级注册建造师，且未担任其他在建项目项目经理。",
         "第一章 招标公告 3.4", "P4", "medium", "已完成", True),
        (p2, "technical", "交通疏解方案",
         "观澜大道为现状主干道，须分四阶段交通疏解，提供占道施工许可办理计划。",
         "第七章 技术标准及要求 2.3", "P120", "high", "未开始", False),
        (p2, "business", "措施费报价要求",
         "交通疏解、管线迁改等措施工作内容按总价包干，结算不因工程量变化调整。",
         "第五章 工程量清单说明 1.5", "P63", "medium", "进行中", False),
        (p2, "credit", "市政公用工程业绩",
         "近五年完成至少2项合同额8000万元以上的市政道路工程业绩。",
         "第一章 招标公告 3.3", "P3", "high", "未开始", False),
    ]
    for r in rows:
        db.add(BidRequirement(project_id=r[0].id, category=r[1], name=r[2], content=r[3],
                              source_text=r[4], page_no=r[5], importance=r[6],
                              status=r[7], confirmed=r[8]))


def _seed_history(db: Session):
    companies = ["示例市第一建筑工程有限公司", "示例市市政工程总公司", "示例铁建集团深圳分公司",
                 "示例建工集团股份有限公司", "示例建设集团第三工程有限公司", "示例市路桥建设集团"]
    rows = [
        ("示例外国语学校初中部改扩建工程", "SZ2025-SG101", "南山区", "房建", "示例市建筑工务署",
         0.92, 21500, 22800, BASE - timedelta(days=300)),
        ("龙华区有轨电车示范线延伸段土建工程", "SZ2025-JT102", "龙华区", "交通", "示例市交通运输局",
         0.89, 18600, 20900, BASE - timedelta(days=280)),
        ("福田区智慧停车系统建设项目", "SZ2025-ZH103", "福田区", "机电安装", "示例市交通运输局福田管理局",
         0.95, 3800, 4000, BASE - timedelta(days=265)),
        ("宝安区碧道建设工程（一期）", "SZ2025-BD104", "宝安区", "水利", "示例市水务局",
         0.91, 12700, 13900, BASE - timedelta(days=250)),
        ("南山区科技园写字楼室内装修工程", "SZ2025-ZX105", "南山区", "装饰装修", "示例市投资控股有限公司",
         0.94, 5600, 6000, BASE - timedelta(days=235)),
        ("龙岗区第二人民医院装修改造工程", "SZ2025-SG106", "龙岗区", "房建", "示例市卫生健康委员会",
         0.90, 9800, 10800, BASE - timedelta(days=220)),
        ("光明区光明大道市政工程", "SZ2025-SZ107", "光明区", "市政", "示例市光明区建筑工务署",
         0.93, 14200, 15200, BASE - timedelta(days=200)),
        ("罗湖区东门商圈外立面综合整治工程", "SZ2025-SG108", "罗湖区", "房建", "示例市罗湖区住房和建设局",
         0.88, 7200, 8100, BASE - timedelta(days=180)),
        ("坪山区新能源汽车产业基地配套道路", "SZ2026-SZ109", "坪山区", "市政", "示例市坪山区建筑工务署",
         0.91, 11600, 12700, BASE - timedelta(days=160)),
        ("盐田港后方陆域污水处理设施工程", "SZ2026-WL110", "盐田区", "水利", "示例市水务局盐田管理局",
         0.90, 8900, 9800, BASE - timedelta(days=140)),
        ("前海合作区景观桥工程施工", "SZ2026-JG111", "前海合作区", "园林绿化", "示例市前海开发投资控股有限公司",
         0.93, 6400, 6900, BASE - timedelta(days=120)),
        ("深圳北站东广场交通改善工程", "SZ2026-JT112", "龙华区", "交通", "示例市交通运输局龙华管理局",
         0.89, 10500, 11800, BASE - timedelta(days=95)),
        ("大鹏新区滨海旅游公路路基工程", "SZ2026-DP113", "大鹏新区", "交通", "示例市交通运输局大鹏管理局",
         0.92, 7800, 8500, BASE - timedelta(days=70)),
        ("宝安中心区图书馆机电安装工程", "SZ2026-JD114", "宝安区", "机电安装", "示例市宝安区文化广电旅游体育局",
         0.94, 4300, 4600, BASE - timedelta(days=45)),
        ("龙华区实验学校建设工程", "SZ2026-SG115", "龙华区", "房建", "示例市龙华区教育局",
         0.91, 19700, 21600, BASE - timedelta(days=20)),
    ]
    for i, r in enumerate(rows):
        winner = companies[i % len(companies)]
        bidders = [c for j, c in enumerate(companies) if j % len(companies) != i % len(companies)][:4] + [winner]
        db.add(HistoricalProject(
            project_name=r[0], project_code=r[1], region=r[2], project_type=r[3],
            tenderer=r[4], winner=winner,
            bid_amount=round(r[5] * r[7], 2), control_amount=r[7],
            participants=bidders, bid_open_date=r[8],
            remarks="演示数据：中标结果不代表真实公示内容", is_demo=True,
        ))


def _seed_chat(db: Session):
    s = ChatSession(title="演示会话：学校类项目询价", context_type="history")
    db.add(s)
    db.flush()
    db.add_all([
        ChatMessage(session_id=s.id, role="user", content="深圳学校类房建项目最近的中标价大概什么水平？", is_mock=False),
        ChatMessage(session_id=s.id, role="assistant", content=(
            "基于历史项目库（3 条学校/教育类记录）的统计：\n"
            "· 中标均价：约 16033 万元；\n"
            "· 近期同类：龙华区实验学校建设工程 中标 19677 万元（控制价 21600 万元，下浮约 8.9%）。\n"
            "（模拟回复 · 演示阶段未接入真实大模型，内容基于本地数据库规则生成）"), is_mock=True),
    ])
