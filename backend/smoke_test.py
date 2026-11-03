# -*- coding: utf-8 -*-
"""后端接口冒烟测试（历史版本，针对运行中的服务）。

⚠ 注意（整改 B4）：本脚本会对其指向的服务创建/删除业务数据。
默认测试套件请使用 tests/run_tests.py（隔离临时库，绝不触碰正式数据）。
本脚本仅建议对一次性演示实例使用，或改写 BASE 指向测试服务。
"""
import io
import json
import sys
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:8000"
sys.stdout.reconfigure(encoding="utf-8")
results = []


def call(method, path, body=None, expect=200, form=None):
    url = BASE + path
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data, ct = form
        headers["Content-Type"] = ct
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            code = r.status
            payload = r.read()
            ctype = r.headers.get("content-type", "")
            if "json" in ctype:
                return code, json.loads(payload)
            return code, payload[:80]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]


def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail[:120]}")


# 基础
code, r = call("GET", "/api/health")
check("health", code == 200 and r["ok"])

# 工作台
code, r = call("GET", "/api/dashboard")
check("dashboard", code == 200 and r["project_count"] > 0 and len(r["type_distribution"]) > 0,
      f"projects={r['project_count']} trend={len(r['win_trend'])} milestones={len(r['upcoming_milestones'])}")

# 项目库
code, r = call("GET", "/api/projects")
check("projects.list", code == 200 and len(r) == 12, f"count={len(r)}")
kw = urllib.parse.quote("中学")
code, r = call("GET", f"/api/projects?keyword={kw}")
check("projects.search", code == 200 and len(r) == 1 and "中学" in r[0]["name"], r[0]["name"] if r else "")
code, r = call("GET", "/api/projects?region=%E9%BE%99%E5%B2%97%E5%8C%BA")
check("projects.filter.region", code == 200 and all(p["region"] == "龙岗区" for p in r), f"count={len(r)}")
code, r = call("GET", "/api/projects/1")
check("projects.detail", code == 200 and r["id"] == 1, r["name"])
code, r = call("POST", "/api/projects", body={
    "name": "测试新建项目-光明区保障房工程", "code": "TEST-001", "region": "光明区",
    "project_type": "房建", "budget": 5000, "deadline": "2026-11-30"})
check("projects.create", code == 200 and r["id"] > 0, f"id={r.get('id')}")
test_id = r["id"]
code, r = call("POST", "/api/projects", body={"name": "重复编号项目", "code": "TEST-001"})
check("projects.create.dup-code", code == 400, str(r))
code, r = call("PUT", f"/api/projects/{test_id}", body={"budget": 6600, "stage": "跟踪中"})
check("projects.update", code == 200 and r["budget"] == 6600)
code, r = call("POST", f"/api/projects/{test_id}/favorite")
check("projects.favorite", code == 200 and r["favorite"] is True)
code, r = call("DELETE", f"/api/projects/{test_id}")
check("projects.delete", code == 200)
code, r = call("GET", f"/api/projects/{test_id}")
check("projects.deleted-404", code == 404)

# 公告
code, r = call("GET", "/api/announcements?page_size=5")
check("ann.list", code == 200 and r["total"] >= 15 and len(r["items"]) == 5, f"total={r['total']}")
code, r = call("GET", "/api/announcements?ann_type=%E4%B8%AD%E6%A0%87%E5%85%AC%E5%91%8A")
check("ann.filter.type", code == 200 and all(i["ann_type"] == "中标公告" for i in r["items"]), f"count={len(r['items'])}")
code, r = call("GET", "/api/announcements/1")
check("ann.detail", code == 200 and r["is_demo"] is True)
code, r = call("POST", "/api/announcements", body={"title": "手动录入测试公告", "ann_type": "招标公告", "publish_date": "2026-10-30"})
check("ann.create", code == 200 and r["is_demo"] is False)
code, r = call("DELETE", f"/api/announcements/{r['id']}")
check("ann.delete", code == 200)
code, r = call("POST", "/api/announcements/fetch")
check("ann.fetch.not_configured", code == 200 and r["status"] == "not_configured", r.get("message", "")[:60])

# 文件
code, r = call("GET", "/api/documents")
check("docs.list", code == 200 and len(r) == 3, f"count={len(r)}")
boundary = "----testboundary123"
file_body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"测试招标文件.pdf\"\r\n"
             f"Content-Type: application/pdf\r\n\r\nPDF-BYTES-123\r\n"
             f"--{boundary}\r\nContent-Disposition: form-data; name=\"project_id\"\r\n\r\n1\r\n"
             f"--{boundary}--\r\n").encode()
code, r = call("POST", "/api/documents/upload",
               form=(file_body, f"multipart/form-data; boundary={boundary}"))
check("docs.upload", code == 200 and r["status"] == "待解析", r.get("original_name", str(r)[:80]))
doc_id = r["id"]
code, r = call("POST", f"/api/documents/{doc_id}/parse")
check("docs.parse.demo", code == 200 and r["result"]["is_demo"] is True, str(r)[:100])
code, r = call("GET", "/api/documents")
check("docs.parsed-status", code == 200 and any(d["id"] == doc_id and d["status"] == "解析完成" for d in r))
code, r = call("POST", "/api/documents/upload", form=(
    (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"bad.txt\"\r\n\r\nX\r\n"
     f"--{boundary}--\r\n").encode(), f"multipart/form-data; boundary={boundary}"))
check("docs.upload.reject-type", code == 400)
code, r = call("DELETE", f"/api/documents/{doc_id}")
check("docs.delete", code == 200)

# 投标要求
code, r = call("GET", "/api/requirements?project_id=1")
check("req.list.by-project", code == 200 and len(r) == 9, f"count={len(r)}")
code, r = call("GET", "/api/requirements?category=credit")
check("req.list.by-category", code == 200 and all(x["category"] == "credit" for x in r), f"count={len(r)}")
code, r = call("POST", "/api/requirements", body={
    "project_id": 1, "category": "technical", "name": "测试要求-夜间施工许可", "content": "测试内容",
    "source_text": "测试出处", "page_no": "P10", "importance": "high"})
check("req.create", code == 200 and r["id"] > 0)
req_id = r["id"]
code, r = call("PUT", f"/api/requirements/{req_id}", body={"status": "已完成", "confirmed": True})
check("req.update", code == 200 and r["status"] == "已完成" and r["confirmed"] is True)
code, r = call("DELETE", f"/api/requirements/{req_id}")
check("req.delete", code == 200)
code, r = call("GET", "/api/requirements/summary")
check("req.summary", code == 200 and r["technical"]["total"] == 4)

# 历史项目
code, r = call("GET", "/api/history?page_size=5")
check("hist.list", code == 200 and r["total"] == 15 and len(r["items"]) == 5, f"total={r['total']}")
kw = urllib.parse.quote("中铁")
code, r = call("GET", f"/api/history?keyword={kw}")
check("hist.search.winner", code == 200 and all("中铁" in (i["winner"] + "".join(i["participants"])) for i in r["items"]),
      f"count={len(r['items'])}")
code, r = call("GET", "/api/history/1")
check("hist.detail", code == 200 and r["bid_amount"] > 0)
code, r = call("GET", "/api/history/stats")
check("hist.stats", code == 200 and r["total"] == 15 and r["avg_amount"] > 0)
code, r = call("GET", "/api/history/import/template")
check("hist.template", code == 200 and bytes([0x50, 0x4B]) in r if isinstance(r, bytes) else False, "xlsx magic")

# AI
code, r = call("GET", "/api/ai/sessions")
check("ai.sessions", code == 200 and len(r) >= 1)
code, r = call("POST", "/api/ai/chat", body={"context_type": "general", "message": "平台能做什么？"})
check("ai.chat.general", code == 200 and r["is_mock"] is True and "模拟回复" in r["reply"], r["reply"][:80])
sess = r["session_id"]
code, r = call("POST", "/api/ai/chat", body={"session_id": sess, "context_type": "project", "context_ref": "1",
                                             "message": "这个项目的要点？"})
check("ai.chat.project", code == 200 and "项目编号" in r["reply"])
code, r = call("POST", "/api/ai/chat", body={"session_id": sess, "context_type": "history", "message": "学校类项目中标价水平"})
check("ai.chat.history", code == 200 and "中标均价" in r["reply"])
code, r = call("GET", f"/api/ai/sessions/{sess}")
check("ai.session.messages", code == 200 and len(r["messages"]) == 6, f"msg={len(r['messages'])}")
code, r = call("GET", "/api/ai/config")
check("ai.config", code == 200 and r["connected"] is False)

# 投标管理
code, r = call("GET", "/api/bids/projects")
check("bids.list", code == 200 and len(r) == 5 and all("progress" in x for x in r), f"count={len(r)}")
code, r = call("GET", "/api/bids/projects/1/overview")
check("bids.overview", code == 200 and len(r["tasks"]) == 5 and len(r["milestones"]) == 3
      and len(r["deliverables"]) == 2)
code, r = call("POST", "/api/bids/tasks", body={"project_id": 1, "title": "测试任务", "priority": "low"})
check("bids.task.create", code == 200)
task_id = r["id"]
code, r = call("PUT", f"/api/bids/tasks/{task_id}", body={"status": "已完成"})
check("bids.task.update", code == 200 and r["status"] == "已完成")
code, r = call("DELETE", f"/api/bids/tasks/{task_id}")
check("bids.task.delete", code == 200)
code, r = call("POST", "/api/bids/milestones", body={"project_id": 1, "name": "测试节点", "date": "2026-11-11", "kind": "其他"})
check("bids.milestone.create", code == 200)
ms_id = r["id"]
code, r = call("DELETE", f"/api/bids/milestones/{ms_id}")
check("bids.milestone.delete", code == 200)
d_boundary = "----delboundary456"
del_body = (f"--{d_boundary}\r\nContent-Disposition: form-data; name=\"project_id\"\r\n\r\n1\r\n"
            f"--{d_boundary}\r\nContent-Disposition: form-data; name=\"category\"\r\n\r\n技术方案\r\n"
            f"--{d_boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"技术标V1.pdf\"\r\n\r\nPDFDEL\r\n"
            f"--{d_boundary}--\r\n").encode()
code, r = call("POST", "/api/bids/deliverables/upload",
               form=(del_body, f"multipart/form-data; boundary={d_boundary}"))
check("bids.deliverable.upload", code == 200 and r["name"] == "技术标V1.pdf", str(r)[:80])
del_id = r["id"]
code, r = call("DELETE", f"/api/bids/deliverables/{del_id}")
check("bids.deliverable.delete", code == 200)

# 设置与系统状态
code, r = call("GET", "/api/settings")
check("settings.list", code == 200 and "model" in r and "basic" in r, f"groups={list(r.keys())}")
code, r = call("PUT", "/api/settings", body={"key": "basic.company_name", "value": "测试公司名称"})
check("settings.update", code == 200 and r["value"] == "测试公司名称")
code, r = call("PUT", "/api/settings", body={"key": "basic.company_name", "value": "示例建工有限公司"})
check("settings.restore", code == 200)
code, r = call("GET", "/api/system/status")
check("system.status", code == 200 and r["database"]["tables"]["tender_projects"] > 0,
      f"db={r['database']['size_kb']}KB tables={len(r['database']['tables'])}")

# 汇总
fails = [n for n, ok, _ in results if not ok]
print(f"\n===== 总计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)} =====")
if fails:
    print("失败项：", fails)
    sys.exit(1)
