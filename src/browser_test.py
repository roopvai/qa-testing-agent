from playwright.sync_api import sync_playwright

def take_screenshot(url: str, output_path: str = "screenshot.png"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        try:
            page.wait_for_selector("text=AI Test Case", timeout=30000)  # up to 30s
        except Exception as e:
            print(f"Warning: expected text never appeared — {e}")
        page.wait_for_timeout(1000)
        page.screenshot(path=output_path)
        browser.close()
        print(f"Screenshot saved to {output_path}")

if __name__ == "__main__":
    take_screenshot("https://srs-test-agent-ai.streamlit.app/")
EOF
