import os
import subprocess
import time
import urllib.request
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from scripts.issue_token import issue
from app.config import Settings

import tempfile

root = Path.cwd()

checkdir = tempfile.TemporaryDirectory()
api_env = dict(
    os.environ,
    DATABASE_URL="sqlite:///" + checkdir.name + "/app.db",
    QDRANT_PATH=checkdir.name + "/vectors",
    ARTIFACT_DIR=str(root / "runtime/ui-traces"),
)
log = open(root / "runtime/ui-check.log", "w")
api = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"],
    stdout=log,
    stderr=log,
    env=api_env,
)
ui = subprocess.Popen(["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=root / "frontend", stdout=log, stderr=log)
try:
    for i in range(100):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
            urllib.request.urlopen("http://127.0.0.1:5173", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        raise RuntimeError("Local services not ready")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.route(
            "**/*",
            lambda route: (
                route.continue_()
                if route.request.url.startswith(("http://localhost:", "http://127.0.0.1:"))
                else route.abort()
            ),
        )
        page.goto("http://localhost:5173")
        page.get_by_label("Secure session token").fill(issue("user_1", Settings()))
        page.get_by_role("button", name="Connect to workspace").click()
        page.get_by_text("Let’s work through it.").wait_for()
        Path("artifacts/screenshots").mkdir(parents=True, exist_ok=True)
        page.screenshot(path="artifacts/screenshots/01-chat.png", full_page=True)
        page.get_by_label("Message", exact=True).fill(
            "Compare Standard and Team plans, storage, users and priority support."
        )
        page.get_by_title("Send message").click()
        page.locator(".message.assistant").wait_for()
        page.screenshot(path="artifacts/screenshots/02-answer.png", full_page=True)
        page.get_by_role("button", name="Knowledge base", exact=True).click()
        page.locator(".doc-grid article").first.wait_for()
        page.screenshot(path="artifacts/screenshots/03-documents.png", full_page=True)
        page.get_by_role("button", name="Monitoring", exact=True).click()
        page.locator(".metrics").wait_for()
        page.screenshot(path="artifacts/screenshots/04-monitoring.png", full_page=True)
        print("Browser sign-in, live chat, documents and monitoring succeeded")
        browser.close()
finally:
    ui.terminate()
    api.terminate()
    ui.wait(timeout=10)
    api.wait(timeout=10)
    log.close()
    checkdir.cleanup()
