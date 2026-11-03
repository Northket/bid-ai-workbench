# -*- coding: utf-8 -*-
"""隔离测试套件（整改 B4）。

- 通过 BID_TEST_MODE 使用独立临时数据库与临时上传目录，
  绝不触碰正式库（backend/data/platform.db）与正式上传目录；
- 第一部分：原 54 项冒烟断言原样迁入（不得删减）；
- 第二部分：本次整改专项测试（软删除/统计口径/上传安全等）；
- 运行：venv\\Scripts\\python.exe tests\\run_tests.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["BID_TEST_MODE"] = "1"  # 必须在导入 app 之前设置

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402

import main as app_module  # noqa: E402
from database import DB_PATH, UPLOAD_DIR, SessionLocal  # noqa: E402

results = []


def json_str(o) -> str:
    try:
        return json.dumps(o, ensure_ascii=False)[:200]
    except Exception:
        return str(o)[:200]


def check(name: str, cond, detail=""):
    results.append((name, bool(cond), str(detail)[:220]))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {str(detail)[:120]}")


def multipart_file(filename: str, content: bytes, ctype="application/pdf", extra=None):
    files = {"file": (filename, content, ctype)}
    data = extra or {}
    return files, data


def section(title):
    print(f"\n========== {title} ==========")


with TestClient(app_module.app) as client:
    # ================= 第一部分：原 54 项冒烟断言（原样迁入） =================
    section("一、原有 54 项冒烟断言")

    r = client.get("/api/health").json()
    check("health", r["ok"] is True)

    r = client.get("/api/dashboard").json()
    check("dashboard", r["project_count"] > 0 and len(r["type_distribution"]) > 0,
          f"projects={r['project_count']} trend={len(r['win_trend'])} milestones={len(r['upcoming_milestones'])}")

    r = client.get("/api/projects").json()
    check("projects.list", len(r) == 12, f"count={len(r)}")
    r = client.get("/api/projects", params={"keyword": "中学"}).json()
    check("projects.search", len(r) == 1 and "中学" in r[0]["name"], r[0]["name"] if r else "")
    r = client.get("/api/projects", params={"region": "龙岗区"}).json()
    check("projects.filter.region", all(p["region"] == "龙岗区" for p in r), f"count={len(r)}")
    r = client.get("/api/projects/1").json()
    check("projects.detail", r["id"] == 1, r["name"])
    r = client.post("/api/projects", json={
        "name": "测试新建项目-光明区保障房工程", "code": "TEST-001", "region": "光明区",
        "project_type": "房建", "budget": 5000, "deadline": "2026-11-30"}).json()
    check("projects.create", r["id"] > 0, f"id={r.get('id')}")
    test_id = r["id"]
    resp = client.post("/api/projects", json={"name": "重复编号项目", "code": "TEST-001"})
    check("projects.create.dup-code", resp.status_code == 400, resp.text[:80])
    resp = client.put(f"/api/projects/{test_id}", json={"budget": 6600})
    check("projects.update", resp.status_code == 200 and resp.json()["budget"] == 6600)
    resp = client.post(f"/api/projects/{test_id}/favorite")
    check("projects.favorite", resp.status_code == 200 and resp.json()["favorite"] is True)
    check("projects.delete", client.delete(f"/api/projects/{test_id}").json()["ok"] is True)
    check("projects.deleted-404", client.get(f"/api/projects/{test_id}").status_code == 404)

    r = client.get("/api/announcements", params={"page_size": 5}).json()
    check("ann.list", r["total"] >= 15 and len(r["items"]) == 5, f"total={r['total']}")
    r = client.get("/api/announcements", params={"ann_type": "中标公告"}).json()
    check("ann.filter.type", all(i["ann_type"] == "中标公告" for i in r["items"]))
    r = client.get("/api/announcements/1").json()
    check("ann.detail", r["is_demo"] is True)
    r = client.post("/api/announcements", json={"title": "手动录入测试公告", "ann_type": "招标公告",
                                                "publish_date": "2026-10-30"}).json()
    check("ann.create", r["is_demo"] is False)
    check("ann.delete", client.delete(f"/api/announcements/{r['id']}").json()["ok"] is True)
    r = client.post("/api/announcements/fetch").json()
    check("ann.fetch.not_configured", r["status"] == "not_configured")

    r = client.get("/api/documents").json()
    check("docs.list", len(r) == 3, f"count={len(r)}")
    import io as _io
    import pymupdf as _pm
    _d = _pm.open()
    _pg = _d.new_page()
    _pg.insert_text((50, 60), "第一章  招标公告", fontname="china-s", fontsize=11)
    _pg.insert_text((50, 90), "招标人：测试置业有限公司", fontname="china-s", fontsize=11)
    _buf = _io.BytesIO()
    _d.save(_buf)
    _d.close()
    files = {"file": ("测试招标文件.pdf", _buf.getvalue(), "application/pdf")}
    resp = client.post("/api/documents/upload", files=files, data={"project_id": "1"})
    check("docs.upload", resp.status_code == 200 and resp.json()["status"] == "待解析",
          resp.json().get("original_name", resp.text[:80]))
    doc_id = resp.json()["id"]
    # 第二阶段语义：演示记录 → 演示结果；真实文件 → 真实引擎任务
    demo_doc = next(d for d in client.get("/api/documents").json() if d["is_demo"])
    r = client.post(f"/api/documents/{demo_doc['id']}/parse").json()
    check("docs.parse.demo", r["result"]["is_demo"] is True)
    r_real = client.post(f"/api/documents/{doc_id}/parse").json()
    check("docs.parse.real-task", r_real["ok"] is True and "task_id" in r_real)
    import time as _t0
    _dl = _t0.time() + 60
    while _t0.time() < _dl:
        if any(d["id"] == doc_id and d["status"] != "解析中" for d in client.get("/api/documents").json()):
            break
        _t0.sleep(0.5)
    check("docs.parsed-status", any(d["id"] == doc_id and d["status"] == "解析完成"
                                    for d in client.get("/api/documents").json()))
    files, data = multipart_file("bad.pdf", b"plain text not pdf")
    resp = client.post("/api/documents/upload", files=files, data=data)
    check("docs.upload.magic-check(原 reject-type)", resp.status_code == 400, resp.text[:80])
    check("docs.delete", client.delete(f"/api/documents/{doc_id}").json()["ok"] is True)

    r = client.get("/api/requirements", params={"project_id": 1}).json()
    check("req.list.by-project", len(r) == 9, f"count={len(r)}")
    r = client.get("/api/requirements", params={"category": "credit"}).json()
    check("req.list.by-category", all(x["category"] == "credit" for x in r), f"count={len(r)}")
    r = client.post("/api/requirements", json={
        "project_id": 1, "category": "technical", "name": "测试要求-夜间施工许可", "content": "测试内容",
        "source_text": "测试出处", "page_no": "P10", "importance": "high"}).json()
    check("req.create", r["id"] > 0)
    req_id = r["id"]
    r = client.put(f"/api/requirements/{req_id}", json={"status": "已完成", "confirmed": True}).json()
    check("req.update", r["status"] == "已完成" and r["confirmed"] is True)
    check("req.delete", client.delete(f"/api/requirements/{req_id}").json()["ok"] is True)
    r = client.get("/api/requirements/summary").json()
    check("req.summary", r["technical"]["total"] == 4)

    r = client.get("/api/history", params={"page_size": 5}).json()
    check("hist.list", r["total"] == 15 and len(r["items"]) == 5, f"total={r['total']}")
    r = client.get("/api/history", params={"keyword": "中铁"}).json()
    check("hist.search.winner", all("中铁" in (i["winner"] + "".join(i["participants"])) for i in r["items"]))
    r = client.get("/api/history/1").json()
    check("hist.detail", r["bid_amount"] > 0)
    r = client.get("/api/history/stats").json()
    check("hist.stats(新口径)", r["total"] == 15 and r["amount"]["avg"] and r["amount"]["valid_count"] == 15,
          f"avg={r['amount']['avg']} valid={r['amount']['valid_count']}")
    resp = client.get("/api/history/import/template")
    check("hist.template", resp.status_code == 200 and resp.content[:2] == b"PK", "xlsx magic")

    check("ai.sessions", len(client.get("/api/ai/sessions").json()) >= 1)
    r = client.post("/api/ai/chat", json={"context_type": "general", "message": "平台能做什么？"}).json()
    check("ai.chat.general", r["is_mock"] is True and "模拟回复" in r["reply"], r["reply"][:60])
    sess = r["session_id"]
    r = client.post("/api/ai/chat", json={"session_id": sess, "context_type": "project",
                                          "context_ref": "1", "message": "这个项目的要点？"}).json()
    check("ai.chat.project", "项目编号" in r["reply"])
    r = client.post("/api/ai/chat", json={"session_id": sess, "context_type": "history",
                                          "message": "学校类项目中标价水平"}).json()
    check("ai.chat.history", "统计" in r["reply"] or "有效样本" in r["reply"])
    r = client.get(f"/api/ai/sessions/{sess}").json()
    check("ai.session.messages", len(r["messages"]) == 6, f"msg={len(r['messages'])}")
    check("ai.config", client.get("/api/ai/config").json()["connected"] is False)

    r = client.get("/api/bids/projects").json()
    check("bids.list", len(r) == 5 and all("progress" in x for x in r), f"count={len(r)}")
    r = client.get("/api/bids/projects/1/overview").json()
    check("bids.overview", len(r["tasks"]) == 5 and len(r["milestones"]) == 3 and len(r["deliverables"]) == 2)
    r = client.post("/api/bids/tasks", json={"project_id": 1, "title": "测试任务", "priority": "low"}).json()
    check("bids.task.create", r["id"] > 0)
    task_id = r["id"]
    r = client.put(f"/api/bids/tasks/{task_id}", json={"status": "已完成"}).json()
    check("bids.task.update", r["status"] == "已完成")
    check("bids.task.delete", client.delete(f"/api/bids/tasks/{task_id}").json()["ok"] is True)
    r = client.post("/api/bids/milestones", json={"project_id": 1, "name": "测试节点",
                                                  "date": "2026-11-11", "kind": "其他"}).json()
    check("bids.milestone.create", r["id"] > 0)
    check("bids.milestone.delete", client.delete(f"/api/bids/milestones/{r['id']}").json()["ok"] is True)
    files = {"file": ("技术标V1.pdf", b"%PDF-1.4 deliverable", "application/pdf")}
    resp = client.post("/api/bids/deliverables/upload", files=files,
                       data={"project_id": "1", "category": "技术方案", "version": "V1.0"})
    check("bids.deliverable.upload", resp.status_code == 200 and resp.json()["name"] == "技术标V1.pdf")
    del_id = resp.json()["id"]
    check("bids.deliverable.delete", client.delete(f"/api/bids/deliverables/{del_id}").json()["ok"] is True)

    r = client.get("/api/settings").json()
    check("settings.list", "model" in r and "basic" in r, f"groups={list(r.keys())}")
    r = client.put("/api/settings", json={"key": "basic.company_name", "value": "测试公司名称"}).json()
    check("settings.update", r["value"] == "测试公司名称")
    client.put("/api/settings", json={"key": "basic.company_name", "value": "示例建工有限公司"})
    check("settings.restore", True)
    r = client.get("/api/system/status").json()
    check("system.status", r["database"]["tables"]["tender_projects"] > 0)

    # ================= 第二部分：整改专项测试 =================
    section("二、B1 项目软删除与关联完整性")

    # 1) 造一个带完整关联的项目
    p = client.post("/api/projects", json={"name": "软删除测试项目", "code": "SOFT-001",
                                           "region": "南山区", "project_type": "房建"}).json()
    pid = p["id"]
    files, data = multipart_file("软删除招标文件.pdf", b"%PDF-1.4 keep-me", extra={"project_id": str(pid)})
    d = client.post("/api/documents/upload", files=files, data=data).json()
    req = client.post("/api/requirements", json={"project_id": pid, "category": "technical",
                                                 "name": "软删除关联要求"}).json()
    tsk = client.post("/api/bids/tasks", json={"project_id": pid, "title": "软删除关联任务"}).json()
    files = {"file": ("软删除成果.pdf", b"%PDF-1.4 deliverable", "application/pdf")}
    dlv = client.post("/api/bids/deliverables/upload", files=files,
                      data={"project_id": str(pid)}).json()
    doc_stored = UPLOAD_DIR / "tender-docs" / d["stored_name"]
    dlv_path = UPLOAD_DIR.parent / dlv["file_path"]
    check("soft.关联就绪", doc_stored.exists() and dlv_path.exists())

    # 2) 影响范围
    imp = client.get(f"/api/projects/{pid}/delete-impact").json()
    check("soft.delete-impact", imp["documents"] == 1 and imp["requirements"] == 1
          and imp["tasks"] == 1 and imp["deliverables"] == 1, json_str(imp)[:120])

    # 3) 软删除：不报错、列表不可见、回收站可见、文件仍在
    r = client.delete(f"/api/projects/{pid}").json()
    check("soft.delete默认软删除", r["mode"] == "soft" and r["ok"] is True, r.get("message", "")[:80])
    check("soft.列表不可见", all(x["id"] != pid for x in client.get("/api/projects").json()))
    check("soft.详情404", client.get(f"/api/projects/{pid}").status_code == 404)
    deleted = client.get("/api/projects/deleted").json()
    check("soft.回收站可见", any(x["id"] == pid for x in deleted))
    check("soft.物理文件保留", doc_stored.exists() and dlv_path.exists())
    check("soft.dashboard排除", all(b["project_id"] != pid for b in
                                    client.get("/api/dashboard").json()["bid_progress"]))

    # 4) 恢复：关联关系完整
    r = client.post(f"/api/projects/{pid}/restore").json()
    check("soft.恢复", r["id"] == pid and r["deleted_at"] is None)
    ov = client.get(f"/api/bids/projects/{pid}/overview").json()
    d2 = client.get("/api/documents", params={"project_id": pid}).json()
    check("soft.恢复后关联完整", len(ov["tasks"]) == 1 and len(ov["deliverables"]) == 1
          and len(d2) == 1 and d2[0]["stored_name"] == d["stored_name"])

    # 5) 物理删除：文件不销毁（招标文件解除关联保留，成果文件归档 _orphaned）
    r = client.delete(f"/api/projects/{pid}", params={"permanent": "true"}).json()
    check("soft.permanent无500", r["ok"] is True and r["mode"] == "permanent", r.get("message", "")[:100])
    check("soft.招标文件保留且解除关联", doc_stored.exists() and
          all(x["project_id"] != pid for x in client.get("/api/documents").json()))
    orphan_files = list((UPLOAD_DIR / "_orphaned").rglob("*")) if (UPLOAD_DIR / "_orphaned").exists() else []
    check("soft.成果文件归档_orphaned", dlv_path.exists() is False and len(orphan_files) >= 1,
          f"orphaned={len(orphan_files)}")
    # 清理：解除关联的招标文件记录与磁盘文件
    left = [x for x in client.get("/api/documents").json() if x["stored_name"] == d["stored_name"]]
    for x in left:
        client.delete(f"/api/documents/{x['id']}")
    check("soft.清理完成", doc_stored.exists() is False)

    # 6) 无关联项目：软删除 → 重复软删除报错 → 彻底删除
    p2 = client.post("/api/projects", json={"name": "无关联项目", "code": "SOFT-002"}).json()
    client.delete(f"/api/projects/{p2['id']}")
    check("soft.重复软删除报错", client.delete(f"/api/projects/{p2['id']}").status_code == 400)
    r = client.delete(f"/api/projects/{p2['id']}", params={"permanent": "true"}).json()
    check("soft.无关联项目彻底删除", r["ok"] is True)
    check("soft.彻底删除后404", client.delete(f"/api/projects/{p2['id']}").status_code == 404)

    section("三、B2 历史统计口径（手算基准比对）")

    from services.history_service import normalize_company
    check("norm.后缀归一", normalize_company("示例市第一建筑工程有限责任公司")
          == normalize_company("示例市第一建筑工程有限公司"))
    check("norm.全角半角", normalize_company("某某（深圳） 有限公司") == normalize_company("某某(深圳)有限公司"))

    fixture = [
        # name, region, type, winner, control, bid, date
        ("统测-学校A", "南山区", "房建", "示例市第一建筑工程有限公司", 1000, 900, "2025-06-10"),
        ("统测-学校B", "南山区", "房建", "示例市第一建筑工程有限责任公司", 1000, 950, "2025-06-20"),
        ("统测-市政C", "福田区", "市政", "示例市市政工程总公司", 2000, 2200, "2025-07-01"),  # 中标>控制 → 待核验
        ("统测-市政D", "福田区", "市政", "示例市市政工程总公司", 1500, 0, "2025-07-10"),      # 缺中标价
        ("统测-房建E", "罗湖区", "房建", "示例铁建集团深圳分公司", 0, 800, "2025-08-01"),     # 缺控制价
        ("统测-学校F", "南山区", "房建", "示例市路桥建设集团", 1000, 800, "2024-05-01"),      # 2024 年样本
    ]
    created_ids = []
    for name, region, ptype, winner, control, bid, dt in fixture:
        r = client.post("/api/history", json={
            "project_name": name, "region": region, "project_type": ptype, "winner": winner,
            "control_amount": control, "bid_amount": bid, "bid_open_date": dt,
            "participants": ["示例市第一建筑工程有限公司", "示例市市政工程总公司"]}).json()
        created_ids.append(r["id"])

    s = client.get("/api/history/stats", params={"keyword": "统测"}).json()
    # 手算：有效报价 = 900,950,2200,800,800 → 5 条 avg=1130；下浮率有效 = A10% B5% F20% → avg=11.67
    check("stat.总数", s["total"] == 6, s["total"])
    check("stat.有效报价样本", s["amount"]["valid_count"] == 5, s["amount"]["valid_count"])
    check("stat.平均中标价(手算1130)", s["amount"]["avg"] == 1130.0, s["amount"]["avg"])
    check("stat.下浮率样本(手算3)", s["discount"]["valid_count"] == 3, s["discount"]["valid_count"])
    check("stat.平均下浮率(手算11.67)", abs(s["discount"]["avg"] - 11.67) < 0.01, s["discount"]["avg"])
    check("stat.待核验(手算1)", s["discount"]["pending_verification_count"] == 1,
          s["discount"]["pending_verification_note"][:80])
    check("stat.无效样本(手算2)", s["discount"]["invalid_count"] == 2)
    check("stat.口径跟随筛选-南山", client.get("/api/history/stats",
          params={"keyword": "统测", "region": "南山区"}).json()["total"] == 3)
    check("stat.口径跟随筛选-2024", client.get("/api/history/stats",
          params={"keyword": "统测", "date_from": "2024-01-01", "date_to": "2024-12-31"}).json()["total"] == 1)
    check("stat.列表与统计一致", client.get("/api/history", params={"keyword": "统测"}).json()["total"]
          == s["total"])
    wr = s["winner_ranking"][0]
    check("stat.同名归一排名(手算2次)", wr["count"] == 2, f"{wr['name']}={wr['count']}")
    check("stat.按年份分组", "2024" in s["by_year"] and s["by_year"]["2024"]["count"] == 1)
    for i in created_ids:
        client.delete(f"/api/history/{i}")
    check("stat.清理", client.get("/api/history/stats", params={"keyword": "统测"}).json()["total"] == 0)

    section("四、B3 上传安全")

    # 1) 正常 PDF / docx / xlsx
    ok_types = [("ok.pdf", b"%PDF-1.5 xxx", 200), ("ok.docx", b"PK\x03\x04zip", 200),
                ("ok.xlsx", b"PK\x03\x04zip", 200), ("ok.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1ole", 200),
                ("ok.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1ole", 200)]
    uploaded_ids = []
    for fname, content, expect in ok_types:
        files, data = multipart_file(fname, content)
        resp = client.post("/api/documents/upload", files=files, data=data)
        check(f"up.accept.{fname}", resp.status_code == expect,
              f"{resp.status_code} {resp.text[:60] if resp.status_code != 200 else 'ok'}")
        if resp.status_code == 200:
            uploaded_ids.append(resp.json()["id"])

    # 2) 扩展名伪装：文本/EXE 伪装 PDF
    for fname, content, why in [("fake.pdf", b"just plain text", "文本伪装PDF"),
                                ("mz.pdf", b"MZ\x90\x00\x03\x00exe", "EXE伪装PDF"),
                                ("fake.docx", b"%PDF-1.4 actually-pdf", "PDF伪装docx")]:
        files, data = multipart_file(fname, content)
        resp = client.post("/api/documents/upload", files=files, data=data)
        check(f"up.reject.{why}", resp.status_code == 400 and "不符" in resp.json()["detail"],
              resp.json().get("detail", "")[:80])

    # 3) 大小限制（改设置 1MB → 传 2MB → 还原设置）
    client.put("/api/settings", json={"key": "storage.max_size_mb", "value": "1"})
    big = b"%PDF-1.4" + b"0" * (2 * 1024 * 1024)
    files, data = multipart_file("big.pdf", big)
    resp = client.post("/api/documents/upload", files=files, data=data)
    check("up.大小限制拒绝", resp.status_code == 400 and "大小限制" in resp.json()["detail"],
          resp.json().get("detail", "")[:60])
    parts = list((UPLOAD_DIR / "tender-docs").glob("*.part"))
    check("up.无残留临时文件", len(parts) == 0, f"part files={len(parts)}")
    client.put("/api/settings", json={"key": "storage.max_size_mb", "value": "100"})
    # 限制恢复后同内容可传
    files, data = multipart_file("big-ok.pdf", b"%PDF-1.4" + b"0" * (2 * 1024 * 1024))
    resp = client.post("/api/documents/upload", files=files, data=data)
    check("up.恢复限制后可传", resp.status_code == 200)
    uploaded_ids.append(resp.json()["id"])

    # 4) 路径穿越文件名
    files, data = multipart_file("..\\..\\evil.pdf", b"%PDF-1.4 evil")
    resp = client.post("/api/documents/upload", files=files, data=data)
    check("up.路径穿越被净化", resp.status_code == 200
          and resp.json()["original_name"] == "evil.pdf"
          and ".." not in resp.json()["stored_name"],
          f"orig={resp.json().get('original_name')} stored={resp.json().get('stored_name')}")
    check("up.穿越文件落在目录内", (UPLOAD_DIR / "tender-docs" / resp.json()["stored_name"]).exists()
          and not (UPLOAD_DIR / "evil.pdf").exists())
    uploaded_ids.append(resp.json()["id"])

    # 5) 空文件
    files, data = multipart_file("empty.pdf", b"")
    resp = client.post("/api/documents/upload", files=files, data=data)
    check("up.空文件拒绝", resp.status_code == 400)

    # 6) 清理全部上传（磁盘与记录一致）
    for i in uploaded_ids:
        client.delete(f"/api/documents/{i}")
    left = [x for x in client.get("/api/documents").json() if x["original_name"].startswith(("ok.", "big-ok", "evil"))]
    check("up.清理完成", len(left) == 0)

    section("五、C1 投标要求与原始文件关联")

    files, data = multipart_file("溯源招标文件.pdf", b"%PDF-1.4 trace-source", extra={"project_id": "1"})
    doc = client.post("/api/documents/upload", files=files, data=data).json()
    r = client.post("/api/requirements", json={
        "project_id": 1, "category": "technical", "name": "溯源要求-保证金条款",
        "document_id": doc["id"], "page_number": 16, "chapter_title": "第二章 投标人须知前附表",
        "section_number": "4.1", "original_text": "投标保证金金额为80万元，须从基本账户转出……",
        "extraction_method": "rule", "verification_status": "pending"}).json()
    check("trace.创建含文件关联", r["document_id"] == doc["id"] and r["document_name"] == "溯源招标文件.pdf")
    check("trace.章节页码条款", r["page_number"] == 16 and "前附表" in r["chapter_title"] and r["section_number"] == "4.1")
    check("trace.原文片段", "80万元" in r["original_text"] and r["extraction_method"] == "rule")
    r2 = client.put(f"/api/requirements/{r['id']}", json={"verification_status": "confirmed"}).json()
    check("trace.核验确认记录人/时间", r2["verification_status"] == "confirmed"
          and r2["verified_at"] and r2["verified_by"])
    check("trace.旧字段同步", r2["confirmed"] is True)
    # 存量要求（无文件关联）不受影响：仍可读取且原内容字段保留
    legacy = client.get("/api/requirements", params={"project_id": 1}).json()
    legacy_no_doc = [x for x in legacy if x["id"] != r["id"]][0]
    check("trace.存量要求兼容且字段保留",
          legacy_no_doc["document_id"] is None
          and (legacy_no_doc["source_text"] != "" or legacy_no_doc["page_no"] != ""
               or legacy_no_doc["content"] != ""))
    # 删除文件 → 要求自动脱钩但保留原文片段
    client.delete(f"/api/documents/{doc['id']}")
    after = client.get("/api/requirements", params={"project_id": 1}).json()
    mine = [x for x in after if x["id"] == r["id"]][0]
    check("trace.删文件自动脱钩", mine["document_id"] is None and "80万元" in mine["original_text"])
    client.delete(f"/api/requirements/{r['id']}")
    check("trace.清理", all(x["id"] != r["id"] for x in
                            client.get("/api/requirements", params={"project_id": 1}).json()))

    section("六、C2 API Key 脱敏")

    put_resp = client.put("/api/settings", json={"key": "model.api_key", "value": "sk-SECRET-123456"}).json()
    check("key.写入不回显", put_resp.get("value", "") == "" and put_resp.get("has_value") is True)
    groups = client.get("/api/settings").json()
    model_rows = {x["key"]: x for x in groups["model"]}
    check("key.查询无明文", model_rows["model.api_key"]["value"] == ""
          and model_rows["model.api_key"]["has_value"] is True)
    raw_body = client.get("/api/settings").text
    check("key.原始响应无密钥串", "sk-SECRET-123456" not in raw_body)
    cfg = client.get("/api/ai/config").json()
    check("key.AI配置只报有无", cfg["has_api_key"] is True and "sk-SECRET" not in client.get("/api/ai/config").text)
    client.put("/api/settings", json={"key": "model.api_key", "value": ""})
    groups = client.get("/api/settings").json()
    check("key.清除后未配置", {x["key"]: x for x in groups["model"]}["model.api_key"]["has_value"] is False)

    section("七、C3 数据库迁移演练（原始库副本）")

    import shutil
    import subprocess
    BACKEND = Path(__file__).resolve().parent.parent
    ORIG_BACKUP = BACKEND / "backups" / "backup_20261031_003955" / "platform.db"
    if not ORIG_BACKUP.exists():
        check("mig.原始备份存在", False, f"未找到 {ORIG_BACKUP}")
    else:
        drill_dir = Path(tempfile.mkdtemp(prefix="bid_mig_drill_"))
        drill_db = drill_dir / "drill.db"
        shutil.copy(ORIG_BACKUP, drill_db)

        def alembic(*args):
            env = {k: v for k, v in os.environ.items() if k != "BID_TEST_MODE"}
            env["BID_DB_PATH"] = str(drill_db)
            return subprocess.run(
                [sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"), *args],
                cwd=str(BACKEND), env=env, capture_output=True, text=True, timeout=120)

        import sqlite3
        con = sqlite3.connect(str(drill_db))
        before = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ["tender_projects", "document_files", "bid_requirements",
                            "historical_projects", "bid_tasks"]}
        con.close()

        r = alembic("stamp", "0001")
        check("mig.stamp基线", r.returncode == 0, r.stderr.strip()[-100:] if r.returncode else "ok")
        r = alembic("upgrade", "head")
        check("mig.升级到head", r.returncode == 0, r.stderr.strip()[-120:] if r.returncode else "0001→0003")
        con = sqlite3.connect(str(drill_db))
        after = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in ["tender_projects", "document_files", "bid_requirements",
                           "historical_projects", "bid_tasks"]}
        cols_req = [row[1] for row in con.execute("PRAGMA table_info(bid_requirements)")]
        cols_prj = [row[1] for row in con.execute("PRAGMA table_info(tender_projects)")]
        ver = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        confirmed = con.execute(
            "SELECT COUNT(*) FROM bid_requirements WHERE verification_status='confirmed'").fetchone()[0]
        con.close()
        check("mig.数据量不变", before == after, f"{before} == {after}")
        check("mig.新列就位", "document_id" in cols_req and "deleted_at" in cols_prj)
        from scripts.db_migrate import HEAD as _MHEAD
        check("mig.版本=head", ver == _MHEAD, f"{ver} == {_MHEAD}")
        check("mig.存量回填", confirmed > 0, f"confirmed={confirmed}")

        r = alembic("downgrade", "0002")
        con = sqlite3.connect(str(drill_db))
        cols_req = [row[1] for row in con.execute("PRAGMA table_info(bid_requirements)")]
        con.close()
        check("mig.回滚0003成功", r.returncode == 0 and "document_id" not in cols_req,
              r.stderr.strip()[-100:] if r.returncode else "document_id 已移除")
        r = alembic("downgrade", "0001")
        con = sqlite3.connect(str(drill_db))
        cols_prj = [row[1] for row in con.execute("PRAGMA table_info(tender_projects)")]
        con.close()
        check("mig.回滚0002成功", r.returncode == 0 and "deleted_at" not in cols_prj,
              r.stderr.strip()[-100:] if r.returncode else "deleted_at 已移除")
        r = alembic("upgrade", "head")
        check("mig.可再升级", r.returncode == 0)
        shutil.rmtree(drill_dir, ignore_errors=True)

    section("八、第二阶段：解析引擎专项（构造样本）")

    import pymupdf
    from services.doc_parser.engine import (ParseEngineError, build_report,
                                             extract_structured, parse_document)

    def make_pdf(path: Path, pages: list[list[str]]):
        d = pymupdf.open()
        for lines in pages:
            pg = d.new_page()
            y = 60
            for ln in lines:
                pg.insert_text((50, y), ln, fontname="china-s", fontsize=11)
                y += 20
        d.save(str(path))
        d.close()

    tmpd = Path(tempfile.mkdtemp(prefix="bid_parse_test_"))

    # 1) 正常 PDF：多级章节 + 字段 + 日期 + 评分 + 表格页
    good = tmpd / "good.pdf"
    make_pdf(good, [
        ["标段编号：SZ-TEST-2026-001", "标段名称：解析引擎测试工程", "招 标 人：深圳市测试置业有限公司",
         "招标代理机构：深圳市测试招标有限公司", "第一章  招标公告", "一、项目概况",
         "（一）建设地点", "测试市测试区测试路 1 号", "2.1 建设规模：总建筑面积 10000 平方米"],
        ["第二章  投标须知", "投标文件递交截止时间为 2026 年 12 月 15 日 10 时 30 分。",
         "开标时间：2026年12月15日10:30", "第一章  工程量清单说明（略）"],
        ["第三章  评标办法", "评标方法：综合评估法", "商务标部分（40分）：报价准确性", "技术方案（30分）"],
        ["第四章  投标文件否决性条款", "1.逾期提交投标文件的；", "2.投标报价高于最高投标限价的；",
         "3.投标文件未按规定格式签字盖章的；"],
        ["施工组织设计应包括进度计划、质量保证措施、安全文明施工措施。", "智慧工地：投标人应接入实名制平台。"],
        [],  # 空白页
    ])
    parsed = parse_document(good)
    check("引擎.页数与空白页警告", parsed.page_count == 6 and any("空白" in w for w in parsed.warnings),
          f"pages={parsed.page_count} warnings={parsed.warnings}")
    l1 = [c for c in parsed.chapters if c.level == 1]
    check("引擎.一级章节识别", any("招标公告" in c.title for c in l1) and any("投标须知" in c.title for c in l1),
          " / ".join(c.full_title[:14] for c in l1))
    check("引擎.多级章节(一、/（一）)", any(c.level == 2 and c.number == "一、" for c in parsed.chapters)
          and any(c.level == 3 and c.number == "（一）" for c in parsed.chapters))
    items = extract_structured(parsed)
    cats = {it.category for it in items}
    check("引擎.七大类至少五类命中", len(cats) >= 5, str(sorted(cats)))
    basic = {i.field_key: i.value for i in items if i.category == "basic"}
    check("引擎.封面字段(含跨行空格标签)", basic.get("招标人") == "深圳市测试置业有限公司"
          and basic.get("标段编号") == "SZ-TEST-2026-001", json_str(basic)[:160])
    tl = {i.field_key: i.value for i in items if i.category == "timeline"}
    check("引擎.时间节点提取", tl.get("deadline", "").startswith("2026-12-15") and "10:30" in tl.get("deadline", ""),
          json_str(tl)[:120])
    check("引擎.否决条款", sum(1 for i in items if i.category == "rejection") >= 3)
    check("引擎.评分项分值", any("40" in i.value or "30" in i.value for i in items if i.category == "evaluation"))
    check("引擎.原文页码保留", all(i.pdf_page for i in items if i.category == "rejection"))

    # 2) 扫描/图片型 PDF（无文本层）
    scan = tmpd / "scan.pdf"
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_image(pg.rect, stream=pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20)).tobytes("png"))
    d.save(str(scan)); d.close()
    parsed = parse_document(scan)
    check("引擎.扫描页识别(OCR未接入如实标注)", parsed.image_pages == [1]
          and any("扫描" in w for w in parsed.warnings), json_str(parsed.warnings))

    # 3) 损坏 PDF
    bad = tmpd / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not a real pdf body" * 10)
    try:
        parse_document(bad)
        check("引擎.损坏PDF报错", False, "未抛异常")
    except (ParseEngineError, Exception) as e:
        check("引擎.损坏PDF报错", True, str(e)[:60])

    # 4) DOCX / XLSX 样本
    from docx import Document as DocxDocument
    dx = DocxDocument()
    dx.add_heading("第一章  招标公告", level=1)
    dx.add_paragraph("招标人：深圳市测试置业有限公司")
    t = dx.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "序号"; t.cell(0, 1).text = "条款"
    t.cell(1, 0).text = "1"; t.cell(1, 1).text = "逾期提交投标文件的；"
    dxp = tmpd / "good.docx"; dx.save(str(dxp))
    parsed = parse_document(dxp)
    check("引擎.DOCX解析", any("招标公告" in (c.title or "") for c in parsed.chapters)
          and len(parsed.tables) >= 1)
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.append(["工程量清单", "数量"]); ws.append(["土方开挖", "1000"])
    xlp = tmpd / "good.xlsx"; wb.save(str(xlp))
    parsed = parse_document(xlp)
    check("引擎.XLSX解析", "土方开挖" in parsed.pages[0].text)

    # 5) 特殊字符 roundtrip
    sp = tmpd / "special.pdf"
    make_pdf(sp, [["招标范围：含<管道>安装、“±0.00以上”、50%钢筋&混凝土；"]])
    parsed = parse_document(sp)
    check("引擎.特殊字符保留", "±0.00以上" in parsed.pages[0].text and "<管道>" in parsed.pages[0].text)

    section("九、第二阶段：解析 API 专项（隔离库）")

    def wait_task(tid: int, timeout_s: float = 60) -> dict:
        import time as _t
        t0 = _t.time()
        while _t.time() - t0 < timeout_s:
            t = client.get(f"/api/parse/tasks/{tid}").json()
            if t["status"] != "running":
                return t
            _t.sleep(0.5)
        return {"status": "timeout"}

    files, data = multipart_file("api测试招标文件.pdf", b"placeholder")
    # 用构造的完整 PDF 上传
    files = {"file": ("api测试招标文件.pdf", good.read_bytes(), "application/pdf")}
    resp = client.post("/api/documents/upload", files=files, data={"project_id": "1"})
    api_doc = resp.json()
    check("api.上传真实文件", resp.status_code == 200 and api_doc["status"] == "待解析")

    r = client.post(f"/api/parse/documents/{api_doc['id']}").json()
    check("api.启动解析任务V1", r["ok"] is True and r["version"] == 1, json_str(r)[:100])
    t = wait_task(r["task_id"])
    check("api.任务完成", t["status"] == "completed", json_str(t.get("error_message", ""))[:80])
    check("api.统计报告", t["stats"]["page_count"] == 6 and t["stats"]["chapter_count"] > 0)
    latest = client.get(f"/api/parse/documents/{api_doc['id']}/latest").json()
    check("api.结果持久化", latest["task"]["status"] == "completed"
          and sum(len(v) for v in latest["categories"].values()) > 0,
          json_str({k: len(v) for k, v in latest['categories'].items()}))
    rej = latest["categories"].get("rejection", [])
    target = next((x for x in rej if "逾期" in x["original_text"]), rej[0] if rej else None)
    check("api.否决条目带页码", target and target["pdf_page"] in (4,))

    # 人工核验 + 修改（原文保留）
    r2 = client.put(f"/api/parse/results/{target['id']}",
                    json={"verification_status": "confirmed", "manual_value": "人工修订后的条款文本"}).json()
    check("api.人工核验修改", r2["ok"] is True)
    latest = client.get(f"/api/parse/documents/{api_doc['id']}/latest").json()
    verified = [x for x in latest["categories"]["rejection"]
                if x["verification_status"] == "confirmed"][0]
    check("api.核验后值生效且原文保留", verified["value"] == "人工修订后的条款文本"
          and "逾期" in verified["original_text"])

    # 重新解析 → 版本 V2 + 已核验结转
    r3 = client.post(f"/api/parse/documents/{api_doc['id']}").json()
    t3 = wait_task(r3["task_id"])
    latest2 = client.get(f"/api/parse/documents/{api_doc['id']}/latest").json()
    carried = [x for x in latest2["categories"]["rejection"] if x["is_carried"]]
    check("api.重新解析版本递增", latest2["task"]["version"] == 2 and t3["status"] == "completed")
    check("api.已核验结转不被覆盖", len(carried) == 1 and carried[0]["value"] == "人工修订后的条款文本",
          f"carried={len(carried)}")

    # 导出
    resp = client.get(f"/api/parse/tasks/{latest2['task']['id']}/export")
    check("api.导出xlsx", resp.status_code == 200 and resp.content[:2] == b"PK")

    # 转投标要求
    r4 = client.post(f"/api/parse/results/{carried[0]['id']}/to-requirement").json()
    check("api.转投标要求(溯源字段)", r4["ok"] is True)
    reqs = client.get("/api/requirements", params={"project_id": 1}).json()
    conv = [x for x in reqs if x["name"] == "否决/无效投标情形" and x["document_id"] == api_doc["id"]]
    check("api.要求含文件溯源", len(conv) == 1 and conv[0]["original_text"]
          and conv[0]["extraction_method"] == "rule")

    # zip 交易包导入（构造 Project.xml + File.zip）
    def build_package(path: Path, inner_name: str = "招标项目/招标文件.pdf"):
        import zipfile as _zf
        inner_buf = _zf.ZipFile(tmpd / "inner.zip", "w")
        inner_buf.writestr(inner_name, good.read_bytes())
        inner_buf.writestr("招标项目/评定办法附表.pdf", good.read_bytes())
        inner_buf.close()
        pkg = _zf.ZipFile(path, "w")
        pkg.writestr("Project.xml",
                     "<项目信息><招标项目编号>PKG-001</招标项目编号><招标项目名称>测试交易包项目</招标项目名称>"
                     "<招标人>深圳地铁测试有限公司</招标人><招标代理>测试代理</招标代理></项目信息>")
        pkg.writestr("File.zip", (tmpd / "inner.zip").read_bytes())
        pkg.writestr("CaInfo.xml", "<ca/>")
        pkg.close()

    pkg_path = tmpd / "package.zip"
    build_package(pkg_path)
    files = {"file": ("测试交易包_V1.0.zip", pkg_path.read_bytes(), "application/zip")}
    resp = client.post("/api/documents/import-package", files=files, data={"project_id": "1"})
    imp = resp.json()
    check("api.zip导入", resp.status_code == 200 and len(imp["files"]) == 2 and imp["main_file"]["is_main"],
          json_str(imp)[:140])
    check("api.zip元数据", imp["meta"]["项目编号"] == "PKG-001" and imp["meta"]["招标人"] == "深圳地铁测试有限公司")
    check("api.zip记录SHA256", len(imp["source_sha256"]) == 64)
    # 导入的主文件解析
    r5 = client.post(f"/api/parse/documents/{imp['main_file']['id']}").json()
    t5 = wait_task(r5["task_id"])
    check("api.zip主文件解析成功", t5["status"] == "completed")
    # 重复导入同一 zip（幂等成功，独立记录）
    files = {"file": ("测试交易包_V1.0.zip", pkg_path.read_bytes(), "application/zip")}
    resp2 = client.post("/api/documents/import-package", files=files)
    check("api.重复导入独立成功", resp2.status_code == 200)
    # 非法 zip
    files = {"file": ("fake.zip", b"not a zip at all", "application/zip")}
    resp3 = client.post("/api/documents/import-package", files=files)
    check("api.损坏zip拒绝", resp3.status_code == 400)
    # 清理导入的测试文档
    docs_all = client.get("/api/documents").json()
    for x in docs_all:
        if x["id"] not in (1, 2, 3) and not x["is_demo"]:
            client.delete(f"/api/documents/{x['id']}")
    client.delete(f"/api/requirements/{conv[0]['id']}")
    shutil.rmtree(tmpd, ignore_errors=True)

    section("十、第二阶段：真实招标文件端到端（隔离库）")

    # 真实样本路径不写入源码（避免泄露项目信息），通过环境变量 BID_REAL_SAMPLE_ZIP 提供；
    # 未提供或文件不存在时如实跳过本节（不伪造结果）；提供后按通用断言校验导入/解析能力。
    _real_zip = os.environ.get("BID_REAL_SAMPLE_ZIP", "").strip()
    if not _real_zip or not Path(_real_zip).exists():
        print(f"[skip] 第十节真实文件端到端：未设置 BID_REAL_SAMPLE_ZIP 或文件不存在"
              f"（{_real_zip or '未提供路径'}），本节如实跳过")
    else:
        import hashlib as _hl
        real_zip_path = Path(_real_zip)
        real_sha = _hl.sha256(real_zip_path.read_bytes()).hexdigest()
        files = {"file": (real_zip_path.name, real_zip_path.read_bytes(), "application/zip")}
        resp = client.post("/api/documents/import-package", files=files)
        imp = resp.json()
        check("real.zip导入成功", resp.status_code == 200 and len(imp["files"]) >= 3,
              json_str(imp.get("files", []))[:160])
        check("real.SHA256一致(原件指纹)", imp["source_sha256"] == real_sha, imp["source_sha256"][:24])
        check("real.交易包元数据", bool(str(imp["meta"].get("项目名称", "")).strip())
              and bool(str(imp["meta"].get("招标人", "")).strip()),
              json_str(imp["meta"])[:120])
        main_id = imp["main_file"]["id"]
        r = client.post(f"/api/parse/documents/{main_id}").json()
        t = wait_task(r["task_id"], timeout_s=300)
        check("real.主文件解析完成", t["status"] == "completed"
              and t["stats"]["page_count"] >= 100, json_str(t.get("error_message", ""))[:80])
        s = t["stats"]
        check("real.章节/表格/字符", s["chapter_count"] > 50 and s["table_count"] > 5
              and s["char_count"] > 150000,
              f"chapters={s['chapter_count']} tables={s['table_count']} chars={s['char_count']}")
        ex = s["extracted_items"]
        check("real.七大类提取分布", ex.get("basic", 0) >= 8 and ex.get("rejection", 0) >= 50
              and ex.get("qualification", 0) >= 30 and ex.get("technical", 0) >= 10
              and ex.get("commercial", 0) >= 30, json_str(ex))
        latest = client.get(f"/api/parse/documents/{main_id}/latest").json()
        basic_items = {x["field_key"]: x["value"] for x in latest["categories"]["basic"]}
        check("real.封面关键字段", bool(str(basic_items.get("标段编号", "")).strip())
              and bool(str(basic_items.get("招标人", "")).strip()), json_str(basic_items)[:180])
        check("real.时间节点不猜测日期", all(bool(str(x["value"]).strip()) for x in latest["categories"]["timeline"]),
              "引擎不伪造日期；样本缺公告时应如实标注未明确")
        # 附表解析
        appendix = next((f for f in imp["files"] if "评定办法附表" in f["name"]), None)
        if appendix:
            ra = client.post(f"/api/parse/documents/{appendix['id']}").json()
            ta = wait_task(ra["task_id"], timeout_s=120)
            latest_a = client.get(f"/api/parse/documents/{appendix['id']}/latest").json()
            n_rej_a = len(latest_a["categories"].get("rejection", []))
            check("real.评定办法附表否决条款", ta["status"] == "completed" and n_rej_a >= 50,
                  f"附表否决条款 {n_rej_a} 条")
        # 清理真实样本（测试库）
        for f in imp["files"]:
            client.delete(f"/api/documents/{f['id']}")

# ================= 汇总 =================
failed = [n for n, ok, _ in results if not ok]
print(f"\n===== 测试总计 {len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)} =====")
print(f"测试数据库（临时，已隔离）: {DB_PATH}")
print(f"测试上传目录（临时）: {UPLOAD_DIR}")
if failed:
    print("失败项：")
    for n in failed:
        print("  -", n)
sys.exit(1 if failed else 0)
