"""Playwright UI UAT for the real 90-day and 6-24m forms with local mock GAS.

No patient data or actual TEST/production systems are accessed.
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
ARTIFACTS = ROOT / "tests" / "followup-ui-artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
APP = "http://127.0.0.1:18662"
MOCK = "http://127.0.0.1:18661"
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


def open_form(page, sidebar_label, title_fragment):
    page.goto(APP, wait_until="domcontentloaded", timeout=45000)
    page.get_by_text(sidebar_label, exact=True).first.click()
    page.get_by_role("heading", name=re.compile(title_fragment)).wait_for(timeout=30000)
    page.get_by_role("textbox").first.wait_for(timeout=25000)


def control(page, label):
    return page.get_by_label(label, exact=True).first


def set_text(page, label, value):
    element = control(page, label)
    element.fill(value)
    element.press("Tab")


def set_date(page, label, iso):
    element = control(page, label)
    intended = [int(n) for n in iso.split("-")]
    if element.get_attribute("role") == "group":
        # Streamlit/React Aria date widgets contain three distinct contenteditable
        # spinbuttons (year/month/day). Filling the outer group is invalid.
        for part, value in zip(("year", "month", "day"), intended):
            part_input = element.locator(f'[data-type="{part}"][contenteditable="true"]').first
            part_input.click()
            part_input.press("ControlOrMeta+A")
            part_input.type(str(value), delay=35)
        element.locator('[data-type="day"][contenteditable="true"]').first.press("Tab")
        visible = element.inner_text()
        digits = [int(n) for n in re.findall(r"\d+", visible)]
        print("SEGMENTED DATE", label, repr(visible), digits, flush=True)
        if digits != intended:
            raise AssertionError("Segmented date mismatch: " + label + " wanted " + iso + " got " + visible)
        return
    placeholder = element.get_attribute("placeholder") or ""
    formats = [iso, iso.replace("-", "/"), iso[5:7] + "/" + iso[8:10] + "/" + iso[:4]]
    if "YYYY/MM/DD" in placeholder.upper():
        formats = [formats[1], formats[0], formats[2]]
    if "MM/DD/YYYY" in placeholder.upper():
        formats = [formats[2], formats[0], formats[1]]
    for formatted in formats:
        try:
            element.fill(formatted, timeout=4500)
            element.press("Tab")
            value = element.input_value()
            digits = [int(n) for n in re.findall(r"\d+", value)]
            if digits == intended or digits == intended[1:] + intended[:1]:
                print("TEXT DATE", label, repr(value), flush=True)
                return
        except Exception:
            continue
    raise AssertionError("Date entry failed: " + label + " / placeholder=" + placeholder)

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
        combobox = page.get_by_role("combobox", name=label, exact=True).first
        print("COMBOBOX HTML", combobox.evaluate("(e) => e.outerHTML.slice(0, 900)"), flush=True)
        combobox.fill(option)
        page.get_by_role("option", name=option, exact=True).wait_for(timeout=7500)
        page.get_by_role("option", name=option, exact=True).click()


def radio(page, option):
    page.get_by_text(option, exact=True).last.click()



def select_radio(page, label, choice):
    radio = page.locator('[data-testid="stRadio"]').filter(has_text=label).first
    if not radio.count():
        raise AssertionError("Missing radio group " + label)
    radio.get_by_text(choice, exact=True).first.click()


def fill_source_identity(page):
    set_text(page, "JUOG登録番号*", SYNTHETIC_ID)
    set_text(page, "担当者メールアドレス*", SYNTHETIC_EMAIL)
    page.get_by_role("button", name="既存情報を取得").click()
    page.get_by_text("周術期・30日CRFの最新情報を取得しました", exact=False).wait_for(timeout=20000)


def fill_day90(page):
    fill_source_identity(page)
    set_date(page, "90日評価日*", "2026-05-30")
    select_radio(page, "今回の評価時における血液検査の実施（通常診療で実施された場合は検査結果を入力）*", "実施あり")
    set_date(page, "90日評価に用いた採血日*", "2026-05-30")
    set_text(page, "Hb (g/dL)", "12.9")
    set_text(page, "Na (mEq/L)", "139")
    choose(page, "尿細胞診*", "Negative (クラスI・II)")
    select_radio(page, "画像検査（CT/MRI等）の実施*", "未実施")
    set_text(page, "画像検査未実施理由*", "synthetic UAT; not performed")
    select_radio(page, "膀胱鏡の実施*", "未実施")
    set_text(page, "膀胱鏡未実施理由*", "synthetic UAT; not performed")
    select_radio(page, "尿路内再発の有無*", "なし")
    choose(page, "現在/これまでの術後治療*", "無治療（経過観察）")
    select_radio(page, "生存状況*", "生存")
    set_date(page, "最終生存確認日*", "2026-05-30")


def fill_followup(page):
    fill_source_identity(page)
    choose(page, "今回の報告時期*", "6ヶ月")
    set_date(page, "今回の評価日*", "2026-09-01")
    choose(page, "尿細胞診*", "Negative (クラスI・II)")
    select_radio(page, "画像検査（CT/MRI等）の実施*", "未実施")
    set_text(page, "画像検査未実施理由*", "synthetic UAT; not performed")
    select_radio(page, "膀胱鏡の実施*", "未実施")
    set_text(page, "膀胱鏡未実施理由*", "synthetic UAT; not performed")
    select_radio(page, "今回の評価時における血液検査の実施（通常診療で実施された場合は検査結果を入力）*", "実施あり")
    set_text(page, "Hb (g/dL)", "12.9")
    set_text(page, "Na (mEq/L)", "140")
    choose(page, "尿路内再発状況*", "なし")
    choose(page, "現在の主な治療状況*", "無治療（経過観察）")
    select_radio(page, "生存状況*", "生存")
    set_date(page, "最終生存確認日*", "2026-09-01")


def open_new_page(browser, label, title):
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    page.set_default_timeout(12000)
    open_form(page, label, title)
    return page


def verify_new_session_restore(browser, kind, nav, title):
    page = open_new_page(browser, nav, title)
    page.get_by_role("button", name=re.compile("再開")).click()
    # Popover and main form share the starred labels; the popover inputs
    # are mounted last in the DOM after opening the popover.
    id_field = page.get_by_label("JUOG登録番号*", exact=True).last
    id_field.fill(SYNTHETIC_ID)
    id_field.press("Tab")
    email_field = page.get_by_label("担当者メールアドレス*", exact=True).last
    email_field.fill(SYNTHETIC_EMAIL)
    email_field.press("Tab")
    if kind == "followup":
        choose(page, "再開する報告時期*", "6ヶ月")
    page.get_by_role("button", name="読み込む").click()
    page.get_by_text("仮保存データを読み込みました", exact=False).wait_for(timeout=20000)
    assert control(page, "Hb (g/dL)").input_value() == "12.9"
    expected_na = "139" if kind == "day90" else "140"
    assert control(page, "Na (mEq/L)").input_value() == expected_na
    visit_label = "90日評価日*" if kind == "day90" else "今回の評価日*"
    assert "2026" in control(page, visit_label).inner_text()
    if kind == "followup":
        assert page.get_by_role("combobox", name="今回の報告時期*", exact=True).input_value() == "6ヶ月"
    print("PASS", kind, "draft restore across fresh Streamlit sessions", flush=True)
    return page


def run_case():
    env = dict(os.environ)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    conf = ROOT / ".streamlit" / "secrets.toml"
    settings = conf.read_text(encoding="utf-8")
    assert 'url = "http://127.0.0.1:18661/"' in settings
    assert "LOCAL-UAT-TOKEN-DO-NOT-USE-ELSEWHERE" in settings
    streams = [
        (ARTIFACTS / "local-mock.log").open("w"),
        (ARTIFACTS / "streamlit.log").open("w"),
    ]
    processes = []
    page = None
    try:
        processes.append(subprocess.Popen([sys.executable, "-u", "tests/mock_followup_registry.py"],
            cwd=ROOT, stdout=streams[0], stderr=subprocess.STDOUT, env=env))
        wait_for(MOCK + "/health")
        processes.append(subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.headless", "true", "--server.address", "127.0.0.1",
            "--server.port", "18662", "--browser.gatherUsageStats", "false"],
            cwd=ROOT, stdout=streams[1], stderr=subprocess.STDOUT, env=env))
        wait_for(APP + "/_stcore/health", seconds=70)
        with sync_playwright() as play:
            browser = play.chromium.launch(headless=True)
            cases = [
                ("day90", "術後90日", "術後90日CRF", fill_day90,
                 "90日データを確定送信"),
                ("followup", "定期経過（6〜24か月）", "定期経過報告CRF",
                 fill_followup, "定期経過データを確定送信"),
            ]
            for kind, nav, title, fn, submit in cases:
                page = open_new_page(browser, nav, title)
                fn(page)
                page.get_by_role("button", name=re.compile("仮保存")).click()
                page.get_by_text("仮保存を確認しました", exact=False).wait_for(timeout=20000)
                print("PASS", kind, "draft saved", flush=True)
                page.close()
                page = verify_new_session_restore(browser, kind, nav, title)
                page.get_by_role("button", name=re.compile(submit)).click()
                page.get_by_text("送信が完了しました", exact=False).wait_for(timeout=20000)
                print("PASS", kind, "formal submit", flush=True)
                page.screenshot(path=str(ARTIFACTS / (kind + "-success.png")), full_page=True)
                page.close()
                page = None
            with urllib.request.urlopen(MOCK + "/_test/state", timeout=4) as resp:
                result = json.load(resp)
            assert len(result["crfs"]) == len(result["audit"]) == 2, result
            by_type = {row["crf_type"]: row for row in result["crfs"]}
            assert set(by_type) == {"day90", "followup"}
            for row in result["crfs"]:
                match = [a for a in result["audit"] if a["submission_id"] == row["submission_id"]]
                assert len(match) == 1
                assert row["record_version"] == match[0]["record_version"] == 1
                assert row["record_key"] == match[0]["record_key"]
            assert result["drafts"] == {}, result["drafts"]
            assert by_type["day90"]["data"]["labs"]["Na"] == 139.0
            assert by_type["followup"]["data"]["labs"]["Na"] == 140.0
            assert "JUOG-999|followup|6m" in [r["record_key"] for r in result["crfs"]]
            print("PASS two Streamlit UI submissions and mock CRF/audit integrity", flush=True)
            browser.close()
    except Exception:
        import traceback
        traceback.print_exc()
        if page is not None:
            try:
                page.screenshot(path=str(ARTIFACTS / "failure.png"), full_page=True)
                print("PAGE BODY", page.locator("body").inner_text()[-6000:], flush=True)
            except Exception:
                pass
        raise
    finally:
        for proc in reversed(processes):
            proc.terminate()
        for proc in reversed(processes):
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
        for stream in streams:
            stream.close()


if __name__ == "__main__":
    run_case()
