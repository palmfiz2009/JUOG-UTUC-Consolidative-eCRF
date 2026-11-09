"""Browser-driven 30-day UAT against the actual Streamlit page + loopback mock backend.

External access is NOT used: requires an injected local [registry] URL exactly on
127.0.0.1. Synthetic subject JUOG-999 with historical, date-consistent details.
The mock emulates Google Apps Script contracts, not the actual deployed TEST GAS.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "tests" / "ui-artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
APP = "http://127.0.0.1:18652"
MOCK = "http://127.0.0.1:18651"
SYNTHETIC_ID = "JUOG-999"
SYNTHETIC_EMAIL = "uat@example.invalid"


def wait_for(url, seconds=45):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.35)
    raise RuntimeError("Local test service not ready: " + url)


def open_form(page):
    page.goto(APP, wait_until="domcontentloaded", timeout=45000)
    page.get_by_text("周術期・術後30日", exact=True).first.click()
    page.get_by_role("heading", name=re.compile("周術期・術後30日CRF")).wait_for(timeout=30000)
    # Streamlit can render the text delta before client-side widget mounting.
    try:
        page.locator('[data-testid="stSelectbox"]').first.wait_for(timeout=18000)
    except Exception:
        print("RENDER DEBUG: no stSelectbox after 18s; testids", page.locator("[data-testid]").evaluate_all(
            "(els) => [...new Set(els.map(e=>e.getAttribute('data-testid')))].slice(0,150)"
        ), flush=True)
        print("RENDER DEBUG roles", {
            "combobox": page.get_by_role("combobox").count(),
            "textbox": page.get_by_role("textbox").count(),
            "inputs": page.locator("input").count(),
            "frames": [f.url for f in page.frames],
        }, flush=True)


def control(page, label):
    return page.get_by_label(label, exact=True).first


def set_text(page, label, value):
    element = control(page, label)
    element.fill(value)
    element.press("Tab")


def set_date(page, label, iso):
    element = control(page, label)
    placeholder = element.get_attribute("placeholder") or ""
    input_type = element.get_attribute("type") or ""
    print("DATE INPUT", label, element.evaluate("(e) => e.outerHTML.slice(0, 800)"), flush=True)
    # React date input implementations differ: native input[type=date] uses ISO;
    # textual date controls may use YYYY/MM/DD or MM/DD/YYYY.
    formats = [iso, iso.replace("-", "/"), iso[5:7] + "/" + iso[8:10] + "/" + iso[:4]]
    if "YYYY/MM/DD" in placeholder.upper():
        formats = [formats[1], formats[0], formats[2]]
    if "MM/DD/YYYY" in placeholder.upper():
        formats = [formats[2], formats[0], formats[1]]
    for formatted in formats:
        try:
            element.fill(formatted, timeout=4500)
            element.press("Tab")
            time.sleep(0.18)
            value = element.input_value()
            print("DATE ATTEMPT", label, formatted, repr(value), flush=True)
            digits = [int(n) for n in re.findall(r"\d+", value)]
            intended = [int(n) for n in iso.split("-")]
            if digits == intended or digits == intended[1:] + intended[:1]:
                return
            if value == formatted:
                return
        except Exception as exc:
            print("DATE ATTEMPT ERROR", label, formatted, type(exc).__name__, str(exc)[:220], flush=True)
    raise AssertionError("Date entry failed: " + label + " / type=" + input_type + " placeholder=" + placeholder)


def choose(page, label, option):
    # Streamlit 1.x releases use different internal selectbox markup.
    # Prefer accessible names rather than assumptions about BaseWeb internals.
    candidates = [
        page.get_by_role("combobox", name=label, exact=True).first,
        page.get_by_label(label, exact=True).first,
        page.locator('[data-testid="stSelectbox"]').filter(has_text=label).first,
    ]
    did_open = False
    for selector in candidates:
        try:
            if selector.count():
                selector.click(timeout=2500)
                did_open = True
                break
        except Exception as exc:
            print("Select candidate failed:", label, type(exc).__name__, flush=True)
    if not did_open:
        page.screenshot(path=str(ARTIFACTS / "select-failure.png"), full_page=True)
        print("SELECTBOX DEBUG", page.locator('[data-testid="stSelectbox"]').evaluate_all(
            "(els) => els.map(e => e.outerHTML.slice(0, 1000))"
        ), flush=True)
        print("PAGE BODY", page.locator("body").inner_text()[-8500:], flush=True)
        print("STREAMLIT EXCEPTION", page.locator('[data-testid="stException"]').all_text_contents(), flush=True)
        raise AssertionError("Could not open selectbox " + label)
    opt = page.get_by_role("option", name=option, exact=True)
    txt = page.get_by_text(option, exact=True)
    print("SELECT DEBUG", label,
          "options", page.locator('[role="option"]').all_inner_texts()[:15],
          "comboboxes", page.get_by_role("combobox").count(),
          "text matches", txt.count(), flush=True)
    if opt.count():
        opt.first.click()
    elif txt.count():
        txt.last.click()
    else:
        # Streamlit's 40-facility menu is virtualized. Searching the combobox
        # explicitly is required before the non-visible option exists in DOM.
        combobox = page.get_by_role("combobox").first
        print("COMBOBOX HTML", combobox.evaluate("(e) => e.outerHTML.slice(0, 900)"), flush=True)
        combobox.fill(option)
        page.get_by_role("option", name=option, exact=True).wait_for(timeout=7500)
        page.get_by_role("option", name=option, exact=True).click()


def radio(page, option):
    page.get_by_text(option, exact=True).last.click()


def fill_form(page):
    choose(page, "施設名*", "関西医科大学")
    set_text(page, "JUOG登録番号*", SYNTHETIC_ID)
    set_text(page, "担当者メールアドレス*", SYNTHETIC_EMAIL)
    radio(page, "実施しなかった")
    set_date(page, "EVP最終投与日*", "2026-08-10")
    set_date(page, "手術予定日*", "2026-08-25")
    choose(page, "手術未施行理由*", "患者希望")
    set_date(page, "30日評価日*", "2026-09-24")
    set_date(page, "30日評価に用いた採血日*", "2026-09-24")
    set_text(page, "Hb (g/dL)", "13.4")
    set_text(page, "WBC (/μL)", "6200")
    choose(page, "術後治療・今後の予定*", "無治療（経過観察）")
    radio(page, "生存")
    set_date(page, "最終生存確認日*", "2026-09-24")


def run_case():
    startup_log = ARTIFACTS / "streamlit.log"
    logs = startup_log.open("w", encoding="utf-8")
    mock_log = (ARTIFACTS / "mock-backend.log").open("w", encoding="utf-8")
    env = dict(os.environ)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    processes = []
    page = None
    try:
        mock = subprocess.Popen(
            [sys.executable, "-u", "tests/mock_registry.py"], cwd=ROOT,
            stdout=mock_log, stderr=subprocess.STDOUT, env=env
        )
        processes.append(mock)
        wait_for(MOCK + "/health")
        print("LOCAL_MOCK_ONLY backend ready", flush=True)
        # Explicit safety gate: no credentials in the checked-out project.
        conf = ROOT / ".streamlit" / "secrets.toml"
        if not conf.is_file():
            raise RuntimeError("Missing local CI-only secrets.toml")
        settings = conf.read_text(encoding="utf-8")
        assert 'url = "http://127.0.0.1:18651/"' in settings, "Non-loopback registry URL forbidden"
        assert "LOCAL-UAT-TOKEN-DO-NOT-USE-ELSEWHERE" in settings

        app = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.headless", "true", "--server.port", "18652",
            "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false",
        ], cwd=ROOT, stdout=logs, stderr=subprocess.STDOUT, env=env)
        processes.append(app)
        wait_for(APP + "/_stcore/health", seconds=70)
        print("Streamlit local instance ready", flush=True)

        with sync_playwright() as play:
            browser = play.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(12000)
            open_form(page)
            fill_form(page)
            page.get_by_role("button", name=re.compile("仮保存")).click()
            page.get_by_text("仮保存を確認しました", exact=False).wait_for(timeout=20000)
            print("PASS browser initial form draft save", flush=True)

            # Separate Streamlit session: draft must come from mock backend, not stale widget state.
            page.close()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(12000)
            open_form(page)
            page.get_by_role("button", name=re.compile("再開")).click()
            set_text(page, "JUOG登録番号", SYNTHETIC_ID)
            set_text(page, "担当者メールアドレス", SYNTHETIC_EMAIL)
            page.get_by_role("button", name="読み込む").click()
            page.get_by_text("仮保存データを読み込みました", exact=False).wait_for(timeout=20000)
            assert control(page, "Hb (g/dL)").input_value() == "13.4"
            assert control(page, "WBC (/μL)").input_value() == "6200"
            assert control(page, "30日評価日*").input_value()
            assert "関西医科大学" in page.locator('[data-testid="stSelectbox"]').filter(has_text="施設名*").first.inner_text()
            print("PASS browser draft restore after fresh session", flush=True)

            page.get_by_role("button", name="事務局へ確定送信").click()
            page.get_by_text("送信が完了しました", exact=False).wait_for(timeout=20000)
            page.get_by_text("version 1", exact=False).wait_for(timeout=12000)
            with urllib.request.urlopen(MOCK + "/_test/state", timeout=3) as r:
                result = json.load(r)
            assert result["events"] == ["save_draft", "get_draft", "get_draft", "save_crf", "delete_draft"], result["events"]
            assert len(result["crfs"]) == len(result["audit"]) == 1
            stored, audit = result["crfs"][0], result["audit"][0]
            assert stored["record_version"] == audit["record_version"] == 1
            assert stored["submission_id"] == audit["submission_id"]
            assert stored["record_key"] == audit["record_key"]
            assert stored["data"]["day30_labs"]["Hb"] is not None
            assert str(stored["data"]["day30_labs"]["Hb"]) in ("13.4", "13.40")
            assert stored["facility_code"] == "F11"
            assert result["draft"] is None
            print("PASS browser formal save and mock CRF/audit linkage", flush=True)
            page.screenshot(path=str(ARTIFACTS / "success.png"), full_page=True)
            browser.close()
    except Exception:
        import traceback
        traceback.print_exc()
        if page:
            try:
                page.screenshot(path=str(ARTIFACTS / "failure.png"), full_page=True)
                print("BROWSER INPUTS", page.locator("input").evaluate_all(
                    "(els) => els.map(e => ({label: e.getAttribute('aria-label'), type:e.type, value:e.value, placeholder:e.placeholder}))"
                ), flush=True)
                print("BROWSER TEXT", page.locator("body").inner_text()[-6500:], flush=True)
            except Exception as inner:
                print("Capture failed:", str(inner), flush=True)
        raise
    finally:
        for process in reversed(processes):
            process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
        logs.close()
        mock_log.close()
        print("Streamlit log saved at", startup_log, flush=True)


if __name__ == "__main__":
    run_case()
