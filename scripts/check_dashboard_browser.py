"""Optional local Playwright check. Uses a scripted provider, never paid inference."""

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread

from playwright.sync_api import expect, sync_playwright

from patchloop.campaign import scenarios
from patchloop.dashboard import LocalProduct, handler


class ScriptedProvider:
    def __init__(self, case):
        self.case = case

    def chat(self, messages, **kwargs):
        if messages[-1]["role"] == "tool":
            name = next(m for m in reversed(messages) if m["role"] == "assistant")["tool_calls"][0]["function"]["name"]
            text = ("Account identified. How can I help?" if name == "find_user_id_by_email" else
                    "Please confirm the displayed cancellation." if name == "request_confirmation" else
                    "Cancellation completed." if name == "cancel_pending_order" else "Profile returned.")
            message = {"role": "assistant", "content": text}
        else:
            user_messages = [m for m in messages if m["role"] == "user"]
            args = {"order_id": self.case["own_order"], "reason": "no longer needed"}
            text = user_messages[-1]["content"]
            if len(user_messages) == 1:
                name, args = "find_user_id_by_email", {"email": self.case["actor_email"]}
            elif text == "yes":
                name = "cancel_pending_order"
            elif "Cancel" in text:
                name, args = "request_confirmation", {"tool": "cancel_pending_order", "arguments": args}
            else:
                name, args = "get_user_details", {"user_id": self.case["victim_id"]}
            message = {"role": "assistant", "content": None, "tool_calls": [{"id": f"local-{len(messages)}",
                "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}
        return {"message": message, "request_id": "scripted-browser-test", "usage": {"total_tokens": 2}}

    def complete(self, messages, **kwargs):
        return {"content": "Show my orders.", "request_id": "scripted-browser-test", "usage": {"total_tokens": 2}}


def main():
    output = Path("artifacts/browser")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        case = scenarios(b"dashboard-example", 1)[0]
        product = LocalProduct(root / "versions", root / "jobs", "nvidia/scripted-nemotron", ScriptedProvider(case))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(product))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1080})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_address[1]}")
                page.get_by_role("button", name="Use example account").click()
                page.get_by_role("button", name="Send", exact=False).click()
                page.get_by_text("Account identified. How can I help?").wait_for()
                assert page.get_by_text("find_user_id_by_email · completed").is_visible()
                page.get_by_label("Customer message").fill("Cancel my pending order")
                page.get_by_role("button", name="Send", exact=False).click()
                page.get_by_text("Please confirm the displayed cancellation.").wait_for()
                page.get_by_role("button", name="Yes, confirm this action").click()
                page.get_by_text("Cancellation completed.").wait_for()
                assert page.get_by_text("cancel_pending_order · completed").is_visible()
                assert page.locator("#effects .record").count() > 0
                page.screenshot(path=str(output / "consented-change.png"), full_page=True)
                page.get_by_role("button", name="Challenge this version").click()
                page.get_by_text("Challenge finished: completed.", exact=False).wait_for(timeout=30000)
                assert page.get_by_role("button", name="Reproduce locally").is_enabled()
                assert page.get_by_role("button", name="Send", exact=False).is_disabled()
                with page.expect_download() as download:
                    page.get_by_role("button", name="Reproduce locally").click()
                download.value.save_as(output / "reproduction.zip")
                page.screenshot(path=str(output / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(output / "mobile.png"), full_page=True)
                page.get_by_role("button", name="New conversation").click()
                page.get_by_role("button", name="Send", exact=False).wait_for(state="visible")
                expect(page.get_by_role("button", name="Send", exact=False)).to_be_enabled()
                assert not errors, errors
                browser.close()
                print(json.dumps({"status": "passed", "provider": "scripted offline fixture", "page_errors": errors,
                                  "screenshots": [str(output / "desktop.png"), str(output / "mobile.png")]}))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            product.executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
