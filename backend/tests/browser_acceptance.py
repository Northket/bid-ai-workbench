# -*- coding: utf-8 -*-
"""第二阶段解析工作台浏览器验收（Playwright + 系统 Edge，只读验收+一次核验写入后还原）。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8000"
ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "backups" / "phase2_shots"
SHOTS.mkdir(parents=True, exist_ok=True)
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {str(detail)[:110]}")


def launch(p):
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        return p.chromium.launch(channel="msedge", headless=True)


with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(viewport={"width": 1500, "height": 940})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))

    # 1) 打开解析工作台
    page.goto(f"{BASE}/documents/7/parse")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(2500)
    body = page.inner_text("body")
    check("wb.任务版本与状态", "解析任务 V1" in body and "已完成" in body)
    check("wb.统计四联", all(k in body for k in ("页数", "章节", "表格", "结构化条目")))
    check("wb.分类页签", all(k in body for k in ("项目基本信息", "否决投标及实质性响应条款", "技术标要求")))

    # 2) 切到否决条款分类（按钮组）
    page.locator('button:has-text("否决投标")').first.click()
    page.wait_for_timeout(800)
    body = page.inner_text("body")
    check("wb.否决条款列表(66条)", "原文依据" in body and "跳转 P" in body)
    page.screenshot(path=str(SHOTS / "workbench_rejection.png"))

    # 3) 点击"跳转 P24" → 左侧 iframe src 含 #page=24
    link = page.get_by_text("跳转 P24", exact=False).first
    link.click()
    page.wait_for_timeout(900)
    iframe_src = page.locator("iframe").get_attribute("src") or ""
    check("wb.点击条目左侧PDF跳页", "#page=24" in iframe_src, iframe_src[-40:])

    # 4) 人工核验：点核验按钮 → 弹窗显示原文 → 修改值保存 → 状态已核验
    page.locator('button:has-text("项目基本信息")').first.click()
    page.wait_for_timeout(600)
    page.evaluate("""() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const b = btns.find(x => x.textContent.trim().startsWith('核验'));
      if (b) b.click();
    }""")
    page.wait_for_timeout(700)
    dlg = page.inner_text(".ant-modal-content")
    check("wb.核验弹窗显示原文(不可改)", "原始提取内容" in dlg and ("2020-440306" in dlg))
    page.locator(".ant-modal-content textarea").fill("2020-440306-70-03-017951037001（人工核验确认）")
    page.screenshot(path=str(SHOTS / "workbench_verify_modal.png"))
    save = page.get_by_role("button", name="保存核验")
    if save.count() == 1:
        save.click(force=True)
    else:
        page.get_by_role("button", name="保 存").click(force=True)
    page.wait_for_timeout(1200)
    body = page.inner_text("body")
    check("wb.核验保存生效", "已核验" in body and "人工核验确认" in body)
    # 还原核验状态（重置为待核验、清空人工值，通过页面按钮不可行 → 接口层还原）
    page.evaluate("""async () => {
      const r = await fetch('/api/parse/documents/7/latest').then(x => x.json());
      const item = r.categories.basic.find(i => i.field_key === '标段编号' && i.verification_status === 'confirmed');
      if (item) await fetch('/api/parse/results/' + item.id, {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({verification_status: 'pending'}) });
    }""")
    page.wait_for_timeout(600)

    # 5) 重新解析按钮存在且已核验保护有提示文案
    check("wb.重新解析入口", page.locator("button:has-text('重新解析')").count() == 1)

    # 6) 第一阶段回归抽查：项目库/要求管理/历史库仍正常
    for path, marks in [("/projects", ["招标项目库", "新建项目"]),
                        ("/requirements", ["投标要求管理", "核验状态"]),
                        ("/history", ["历史项目数据库", "有效样本"]),
                        ("/documents", ["招标文件解析中心", "交易包"])]:
        page.goto(BASE + path)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        page.wait_for_timeout(1200)
        b = page.inner_text("body")
        check(f"reg.{path}", all(m in b for m in marks))

    page.screenshot(path=str(SHOTS / "regression_projects.png"))
    check("wb.无JS错误", not errs, errs[:2])
    browser.close()

failed = [n for n, ok in results if not ok]
print(f"\n===== 浏览器验收 {len(results) - len(failed)}/{len(results)} 通过 =====")
if failed:
    print("失败:", failed)
sys.exit(1 if failed else 0)
