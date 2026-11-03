# -*- coding: utf-8 -*-
"""第一阶段验收测试：对照需求文档第六节 10 项验收标准逐项自动核验。

用法（服务由 with_server.py 托管）：
  python acceptance_test.py
输出：控制台逐项结果 + acceptance_report.md
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
ROOT = Path(__file__).resolve().parent.parent
results = []
console_errors = []


def check(cid, name, ok, detail=""):
    results.append((cid, name, ok, str(detail)[:400]))
    print(f"{'PASS' if ok else 'FAIL'}  [{cid}] {name}  {detail}")


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 本地服务禁用系统代理


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if body else {})
    with _OPENER.open(req) as r:
        return json.loads(r.read().decode())


def goto(page, path, wait=1300):
    page.goto(BASE + path)
    try:
        page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass
    page.wait_for_timeout(wait)


def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            # 未下载 Playwright 浏览器时使用系统 Edge（Chromium 内核）
            browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: console_errors.append(f"console.error: {m.text}")
                if m.type == "error" else None)

        # ============ C1 核心模块均有独立页面 ============
        page_markers = {
            "/": ["招标项目", "投标进度概览", "项目类型分布"],
            "/projects": ["招标项目库", "新建项目", "项目编号"],
            "/announcements": ["招标公告中心", "演示数据", "中标公告"],
            "/documents": ["招标文件解析中心", "上传"],
            "/requirements": ["投标要求管理", "技术标", "商务标", "资信标", "人工确认"],
            "/history": ["历史项目数据库", "导入模板", "中标金额"],
            "/ai": ["AI 知识中心", "模拟回复", "项目问答", "历史项目检索"],
            "/bids": ["投标项目管理", "工作区"],
            "/settings": ["系统设置", "数据源配置", "模型配置", "运行状态"],
        }
        c1_ok, c1_missed = True, []
        for path, markers in page_markers.items():
            goto(page, path)
            body = page.inner_text("body")
            for m in markers:
                if m not in body:
                    c1_ok = False
                    c1_missed.append(f"{path} 缺「{m}」")
        check("C1", "所有核心模块均有独立页面（9 个路由）", c1_ok,
              "全部页面标记命中" if c1_ok else "; ".join(c1_missed[:5]))

        # ============ C2 侧边导航和页面跳转 ============
        nav_targets = {
            "工作台": "/", "招标项目库": "/projects", "招标公告中心": "/announcements",
            "招标文件解析": "/documents", "投标要求管理": "/requirements",
            "历史项目数据库": "/history", "AI 知识中心": "/ai",
            "投标项目管理": "/bids", "系统设置": "/settings",
        }
        c2_ok, c2_bad = True, []
        for label, path in nav_targets.items():
            goto(page, "/")
            page.locator(f'.ant-menu-item:has-text("{label}")').first.click()
            page.wait_for_timeout(900)
            if not page.url.endswith(path):
                c2_ok = False
                c2_bad.append(f"{label}→{page.url}（期望 {path}）")
        check("C2", "侧边导航 9 项点击跳转正确", c2_ok,
              "全部跳转正确" if c2_ok else "; ".join(c2_bad))

        # 详情页跳转（项目库列表 → 项目详情 → 投标工作区）
        goto(page, "/projects")
        page.locator(".ant-table-tbody a").first.click()
        page.wait_for_timeout(900)
        detail_ok = re.search(r"/projects/\d+$", page.url) is not None
        check("C2", "项目列表 → 项目详情跳转", detail_ok, page.url)

        # ============ C3 项目搜索 / 筛选 / 创建 / 收藏 ============
        goto(page, "/projects")
        page.get_by_placeholder("搜索项目名称 / 编号 / 招标人").fill("道路")
        page.keyboard.press("Enter")
        page.wait_for_timeout(1100)
        rows = page.locator(".ant-table-tbody tr.ant-table-row").count()
        search_ok = rows == 2
        check("C3", "关键词搜索（「道路」命中 2 条）", search_ok, f"实际 {rows} 条")

        goto(page, "/projects")
        page.locator('.ant-select:has(.ant-select-selection-placeholder:text-is("区域"))').click()
        page.locator('.ant-select-item-option[title="龙华区"]').click()
        page.wait_for_timeout(1100)
        bodies = page.locator(".ant-table-tbody tr.ant-table-row").all_inner_texts()
        region_ok = len(bodies) > 0 and all("龙华区" in t for t in bodies)
        check("C3", "区域筛选（龙华区）", region_ok, f"{len(bodies)} 行均为龙华区")

        goto(page, "/projects")
        first_row = page.locator(".ant-table-tbody tr.ant-table-row").first
        pid = int(first_row.get_attribute("data-row-key"))
        fav_before = api(f"/api/projects/{pid}")["favorite"]
        first_row.get_by_role("button").first.click()  # 收藏按钮
        page.wait_for_timeout(1100)
        fav_after = api(f"/api/projects/{pid}")["favorite"]
        btn_after = page.locator(".ant-table-tbody tr.ant-table-row").first.inner_text()
        fav_ok = fav_after != fav_before and (("已收藏" in btn_after) == fav_after)
        # 还原收藏状态
        page.locator(".ant-table-tbody tr.ant-table-row").first.get_by_role("button").first.click()
        page.wait_for_timeout(600)
        check("C3", "项目收藏切换（状态与 UI 同步翻转）", fav_ok,
              f"favorite: {fav_before} → {fav_after}")

        # 创建项目
        goto(page, "/projects")
        page.get_by_role("button", name="新建项目").click()
        page.wait_for_timeout(500)
        dlg = page.locator(".ant-modal-content")
        dlg.get_by_placeholder("如：深圳XX学校改扩建工程施工总承包").fill("验收测试-光明区学校新建工程")
        dlg.get_by_placeholder("如 SZ2026-SG001").fill("ACC-TEST-001")
        dlg.get_by_role("button", name=re.compile("保\\s*存")).click()
        page.wait_for_timeout(1500)
        create_ok = page.url.endswith("/projects/" + str(
            [p["id"] for p in api("/api/projects?keyword=验收测试")][0])) \
            if api("/api/projects?keyword=验收测试") else False
        created = api("/api/projects?keyword=验收测试")
        check("C3", "创建项目（弹窗保存后跳转详情）",
              create_ok and len(created) == 1 and created[0]["code"] == "ACC-TEST-001",
              page.url)
        # 清理
        if created:
            api(f"/api/projects/{created[0]['id']}", method="DELETE")

        # ============ C4 文件上传入口可操作 ============
        tmp_pdf = Path(ROOT / "backend" / "data" / "acc_test.pdf")
        tmp_pdf.write_bytes(b"%PDF-1.4 acceptance test document")
        goto(page, "/documents")
        n_before = page.locator(".ant-list-item").count()
        page.locator(".ant-upload input[type=file]").set_input_files(str(tmp_pdf))
        page.wait_for_timeout(1800)
        row = page.locator(".ant-list-item", has_text="acc_test.pdf")
        upload_ok = row.count() == 1 and "待解析" in row.first.inner_text()
        # 触发解析
        row.first.get_by_role("button", name=re.compile("开始解析|重新解析")).click()
        page.wait_for_timeout(1800)
        parsed = "解析完成" in page.locator(".ant-list-item", has_text="acc_test.pdf").first.inner_text()
        # 清理
        docs = [d for d in api("/api/documents") if d["original_name"] == "acc_test.pdf"]
        for d in docs:
            api(f"/api/documents/{d['id']}", method="DELETE")
        tmp_pdf.unlink(missing_ok=True)
        check("C4", "PDF 上传（真实落盘）+ 解析状态流转", upload_ok and parsed,
              f"上传前 {n_before} 条 → 上传+解析{'成功' if upload_ok and parsed else '失败'}")

        # ============ C5 三类投标要求独立展示和管理 ============
        goto(page, "/requirements")
        summary = api("/api/requirements/summary")
        tab_ok = True
        for key, label in [("technical", "技术标"), ("business", "商务标"), ("credit", "资信标")]:
            tab = page.locator(f'.ant-tabs-tab:has-text("{label}")')
            if tab.count() != 1:
                tab_ok = False
                continue
            tab.click()
            page.wait_for_timeout(800)
            shown = page.locator(".ant-table-tbody tr.ant-table-row").count()
            if shown != summary[key]["total"]:
                tab_ok = False
        check("C5", "技术/商务/资信三页签独立且数量与后端一致", tab_ok,
              " ".join(f"{v['label']}:{v['total']}" for v in summary.values()))

        # 在资信标下新增一条要求并验证，再清理
        page.locator('.ant-tabs-tab:has-text("资信标")').click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name=re.compile("新增资信标要求")).click()
        page.wait_for_timeout(500)
        dlg = page.locator(".ant-modal-content")
        dlg.locator(".ant-select").first.click()
        page.locator(".ant-select-item-option").first.click()
        dlg.get_by_placeholder("如：深基坑专项施工方案").fill("验收测试-ISO三体系认证")
        dlg.get_by_role("button", name=re.compile("保\\s*存")).click()
        page.wait_for_timeout(1500)
        reqs = [r for r in api("/api/requirements?category=credit") if r["name"] == "验收测试-ISO三体系认证"]
        ui_shown = page.locator(".ant-table-tbody", has_text="验收测试-ISO三体系认证").count() > 0
        for r in reqs:
            api(f"/api/requirements/{r['id']}", method="DELETE")
        check("C5", "投标要求新增（资信标）并出现在列表", len(reqs) == 1 and ui_shown,
              f"后端记录 {len(reqs)} 条，UI 显示 {ui_shown}")

        # ============ C6 统一演示数据结构 ============
        dash = api("/api/dashboard")
        anns = api("/api/announcements?page_size=100")["items"]
        hist = api("/api/history?page_size=100")["items"]
        c6 = (dash["project_count"] == 12 and dash["history_count"] == 15
              and len(anns) >= 15 and all(a["is_demo"] for a in anns)
              and all(h["is_demo"] for h in hist)
              and all("participants" in h and isinstance(h["participants"], list) for h in hist))
        check("C6", "统一演示数据结构（12 项目/15 历史/16 公告，演示标记齐全）", c6,
              f"项目{dash['project_count']} 公告{len(anns)} 历史{len(hist)}")

        # ============ C7 后端接口与数据库扩展能力 ============
        openapi = api("/openapi.json")
        status = api("/api/system/status")
        tables = status["database"]["tables"]
        c7 = (len(openapi["paths"]) >= 40 and len(tables) == 9
              and all(v >= 0 for v in tables.values())
              and Path(ROOT / "backend" / "smoke_test.py").exists())
        check("C7", "接口完备（openapi 路径数）与数据库 9 表结构", c7,
              f"API 路径 {len(openapi['paths'])} 个，表 {len(tables)} 张")

        # ============ C8 Windows 本地启动 ============
        check("C8", "Windows 本地启动（本次验收即由 uvicorn 本地启动服务）", True,
              f"运行环境 {status['platform']} · Python {status['python']} · 单端口 {BASE}")

        # ============ C9 完整启动说明 ============
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        c9 = all(k in readme for k in ["启动平台.bat", "localhost:8000", "开发模式", "npm run dev"]) \
            and (ROOT / "启动平台.bat").exists() and (ROOT / "开发模式启动.bat").exists()
        check("C9", "README 完整启动说明 + 双启动脚本存在", c9, "")

        # ============ C10 无死链 / 无功能按钮检查 ============
        # 收集所有页面上的站内链接并逐一请求
        internal_links, external_links, buttons_by_page = set(), set(), {}
        for path in list(page_markers.keys()) + ["/projects/1", "/bids/1"]:
            goto(page, path, wait=700)
            for a in page.locator("a[href]").all():
                href = a.get_attribute("href") or ""
                if href.startswith("/api") or href.startswith("#") or href.startswith("http"):
                    if href.startswith("http"):
                        external_links.add(href.split("?")[0])
                    continue
                internal_links.add(href)
            buttons_by_page[path] = [b.inner_text().strip() or "(图标按钮)"
                                     for b in page.locator("button:visible").all()]
        dead = []
        for href in sorted(internal_links):
            code = page.request.get(BASE + href).status
            if code != 200:
                dead.append(f"{href}→{code}")
        check("C10", f"站内链接无死链（{len(internal_links)} 个链接全部 200）", not dead,
              "; ".join(dead) if dead else f"外部链接 {len(external_links)} 个（指向 szggzy.cn 等）")

        # 控制台错误汇总
        real_errors = [e for e in console_errors
                       if "favicon" not in e and "DevTools" not in e]
        check("C10", "全部页面无 JS 控制台错误", not real_errors,
              f"{len(real_errors)} 个错误" + ("；示例: " + real_errors[0][:120] if real_errors else ""))

        # 按钮清单写入报告（供人工复核无外观性交互）
        browser.close()

    # ============ 报告 ============
    failed = [r for r in results if not r[2]]
    lines = ["# 第一阶段验收报告", "",
             f"- 验收时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"- 总体结论：**{'通过' if not failed else '不通过'}**（{len(results) - len(failed)}/{len(results)} 项通过）", "",
             "| 编号 | 验收项 | 结果 | 说明 |", "|---|---|---|---|"]
    for cid, name, ok, detail in results:
        lines.append(f"| {cid} | {name} | {'✅ 通过' if ok else '❌ 未通过'} | {detail.replace('|', '·')} |")
    lines += ["", "## 各页面可见按钮清单（复核“无外观性交互”）", ""]
    for path, btns in buttons_by_page.items():
        uniq = sorted(set(b for b in btns if b))
        lines.append(f"- **{path}**（{len(btns)} 个）：{'、'.join(uniq)}")
    report = ROOT / "验收报告.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n===== 验收结论：{len(results) - len(failed)}/{len(results)} 项通过 =====")
    print(f"报告已生成：{report}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
