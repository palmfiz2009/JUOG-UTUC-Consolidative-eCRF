"""Real, public TEST Streamlit UI smoke and negative-auth test.

No mock backend; no TEST/PROD data writes; no credentials. Intended for
independent CI runners only. Full CRF UAT requires separate assertions.
"""
from __future__ import annotations
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BASE = "https://juog-utuc01-uat.streamlit.app"
ARTIFACTS = Path("tests/live-uat-artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)
assert urlparse(BASE).scheme == "https" and urlparse(BASE).netloc == "juog-utuc01-uat.streamlit.app"
findings = []

def record(name, result, detail=""):
    findings.append({"test": name, "result": result, "detail": detail[:200]})
    print(f"{result} {name}: {detail[:200]}", flush=True)

def require(condition, name, detail):
    if not condition:
        record(name, "FAIL", detail)
        raise AssertionError(name+": "+detail)
    record(name, "PASS", detail)

def nav(page, label):
    link = page.get_by_text(label, exact=True).first
    link.wait_for(timeout=30000)
    link.click()
    page.wait_for_timeout(1400)
    ex = page.locator('[data-testid="stException"]')
    require(ex.count() == 0, "page_no_streamlit_exception_"+label, "no stException")

def backend_probe():
    try:
        with urllib.request.urlopen(BASE+"/_stcore/health", timeout=12) as resp:
            body = resp.read(80).decode("utf-8", "replace").strip()
            print("TEST BACKEND HEALTH",json.dumps({
                "status":resp.status,"body_is_ok":body.lower() == "ok",
                "body_len":len(body)
            }),flush=True)
    except Exception as exc:
        print("TEST BACKEND HEALTH FAILED", type(exc).__name__,
              "http_status", getattr(exc, "code", None), flush=True)

def wait_loaded(page):
    """Wake a hibernating Streamlit Community Cloud app when necessary.

    Print only public page health signals (no page text, form values, email or IDs).
    Never proceed with UI actions unless the UAT-only banner is visible.
    """
    for attempt in range(1):
        try:
            response = page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            body = page.locator("body")
            visible = body.inner_text(timeout=6000).lower()
            print("LIVE URL HEALTH", json.dumps({
                "host": urlparse(page.url).netloc, "path": urlparse(page.url).path,
                "status": response.status if response else None,
                "title": page.title()[:120],
                "uat_only": "uat only" in visible,
                "sleeping": "gone to sleep" in visible or "get this app back up" in visible,
                "not_found": "does not exist" in visible or "cannot find" in visible,
                "login_required": "sign in" in visible or "log in" in visible,
                "streamlit_error": page.locator('[data-testid="stException"]').count() > 0,
            }, ensure_ascii=False), flush=True)
            diagnostic = body.inner_text(timeout=6000)[:700]
            diagnostic = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL_REDACTED]", diagnostic)
            diagnostic = re.sub(r"JUOG[-_][A-Za-z0-9-]+", "[ID_REDACTED]", diagnostic)
            print("LIVE BODY PREVIEW SANITIZED", repr(diagnostic[:700]), flush=True)
            print("LIVE DOM SIGNALS", json.dumps({
                "text_length": len(body.inner_text(timeout=6000)),
                "links": [x[:60] for x in page.get_by_role("link").all_text_contents()[:12]],
                "headings": [x[:60] for x in page.get_by_role("heading").all_text_contents()[:8]],
                "buttons_count": page.get_by_role("button").count(),
                "streamlit_status_elements": page.locator('[data-testid^="st"]').count(),
            }, ensure_ascii=False), flush=True)
            if "get this app back up" in visible or "gone to sleep" in visible:
                for name in [re.compile("get this app back up", re.I),re.compile("wake", re.I)]:
                    button = page.get_by_role("button", name=name)
                    if button.count():
                        print("Streamlit sleeping: click wake-up button", flush=True)
                        button.first.click()
                        page.wait_for_timeout(7500)
                        break
            page.get_by_text("UAT ONLY", exact=False).first.wait_for(timeout=18000)
            return
        except Exception as exc:
            print("LIVE TEST BANNER NOT FOUND", type(exc).__name__,
                  "url_host", urlparse(page.url).netloc,
                  "page_title", page.title()[:120], flush=True)
            if attempt == 0:
                raise
            print("TEST app retry",attempt+1,flush=True)
            time.sleep(5)

def run():
    backend_probe()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.set_default_timeout(18000)
        network = {"ws": [], "ws_closed":0, "ws_errors":0, "ws_sent":0, "ws_received":0,
                   "failed_requests": [], "stcore_http_statuses": [], "http_errors": [],
                   "js_errors":0, "console_errors":0, "console_categories":[]}
        def on_ws(ws):
            network["ws"].append(urlparse(ws.url).path[:80])
            ws.on("close", lambda _: network.__setitem__("ws_closed", network["ws_closed"]+1))
            ws.on("socketerror", lambda _: network.__setitem__("ws_errors", network["ws_errors"]+1))
            ws.on("framesent", lambda _: network.__setitem__("ws_sent", network["ws_sent"]+1))
            ws.on("framereceived", lambda _: network.__setitem__("ws_received", network["ws_received"]+1))
        def on_response(resp):
            if "_stcore" in urlparse(resp.url).path:
                network["stcore_http_statuses"].append({
                    "path":urlparse(resp.url).path[:75], "status":resp.status})
            if resp.status >= 400:
                network["http_errors"].append({
                    "host": urlparse(resp.url).netloc,
                    "path": urlparse(resp.url).path[:100],
                    "status": resp.status})
        def on_console(msg):
            if msg.type != "error": return
            network["console_errors"] += 1
            lowered = msg.text.lower()
            category = next((k for k in (
                "websocket", "403", "404", "429", "502", "503", "failed to fetch",
                "connection", "blocked", "uncaught", "content security policy"
            ) if k in lowered), "other")
            network["console_categories"].append(category)
        page.on("websocket", on_ws)
        page.on("response", on_response)
        page.on("requestfailed", lambda req: network["failed_requests"].append({
            "host":urlparse(req.url).netloc,"path":urlparse(req.url).path[:70]}))
        page.on("pageerror", lambda _: network.__setitem__("js_errors", network["js_errors"]+1))
        page.on("console", on_console)
        try:
            try:
                wait_loaded(page)
            except Exception:
                print("TEST BROWSER NETWORK HEALTH", json.dumps(network,ensure_ascii=False)[:1500],flush=True)
                raise
            require(urlparse(page.url).netloc == "juog-utuc01-uat.streamlit.app",
                    "test_host_exact", "Connected to known TEST host")
            require("UAT ONLY" in page.locator("body").inner_text(),
                    "test_only_banner", "Explicit UAT-only banner visible")

            # Inspect the actual deployed TEST app, not a localhost mock.
            nav(page, "中央MDT審査申請")
            require(page.get_by_label("本人同意取得日*", exact=True).count() > 0,
                    "screening_consent_field", "Consent date available in live TEST form")
            require(page.get_by_label("ECOG PS*", exact=True).count() > 0,
                    "screening_ecog_field", "ECOG PS available in live TEST form")
            button = page.get_by_role("button", name=re.compile("中央MDT審査を申請")).first
            require(button.count() > 0 and not button.is_enabled(),
                    "screening_blank_rejected", "Blank screening cannot be submitted")

            nav(page, "周術期・術後30日")
            require(page.get_by_role("heading", name=re.compile("周術期・術後30日CRF")).count() > 0,
                    "day30_page_open", "Real deployed 30-day form loaded")
            require(page.get_by_label("30日評価日*", exact=True).count() > 0,
                    "day30_visit_date_present", "30-day date field present")

            nav(page, "術後90日")
            require(page.get_by_role("heading", name=re.compile("術後90日CRF")).count() > 0,
                    "day90_page_open", "Real deployed 90-day form loaded")

            nav(page, "定期経過（6〜24か月）")
            require(page.get_by_role("heading", name=re.compile("定期経過報告CRF")).count() > 0,
                    "followup_page_open", "Real deployed follow-up form loaded")

            nav(page, "事務局専用：中央MDT集約・正式登録")
            pw = page.get_by_label("事務局パスワード", exact=True)
            require(pw.count() == 1, "admin_requires_password",
                    "Admin login gate rendered; no privileged read performed")
            pw.fill("UAT-NOT-A-VALID-ADMIN-PASSWORD-20261109")
            page.get_by_role("button", name="ログイン", exact=True).click()
            page.get_by_text("パスワードが違います。", exact=False).wait_for(timeout=20000)
            require(page.get_by_role("button", name="ログアウト").count() == 0,
                    "auth01_wrong_password_rejected",
                    "Wrong password rejected and authenticated controls absent")
            record("production_write", "NOT_ATTEMPTED", "Never connected to PROD or submitted CRFs")
            record("test_data_write", "NOT_ATTEMPTED", "No save/draft/submit click")
        finally:
            report = {
                "target": BASE, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "test_kind": "live-test-frontend-read-and-invalid-admin-only",
                "formal_uat_claim": "Only complete predefined acceptance criteria can be judged PASS",
                "cases": findings
            }
            (ARTIFACTS/"results.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            browser.close()
    print("Completed live TEST browser smoke + negative-auth checks", flush=True)

if __name__ == "__main__":
    run()
