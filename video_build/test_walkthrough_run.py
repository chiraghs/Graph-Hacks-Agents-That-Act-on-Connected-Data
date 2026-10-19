from playwright.sync_api import sync_playwright
import time

def test_run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            headless=True
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        print("Testing Scene 1: Connected-Graph...")
        page.goto("http://localhost:8000/connected-graph")
        page.wait_for_timeout(2000)
        page.click("#btn-theme-toggle")
        page.wait_for_timeout(1000)
        page.click("#btn-theme-toggle")
        page.wait_for_timeout(1000)

        print("Testing Scene 2: Asset Drawer...")
        page.evaluate("selectAsset('A-ROB-03')")
        page.wait_for_timeout(2000)

        print("Testing Scene 3: Command Center...")
        page.click("#nav-btn-dashboard")
        page.wait_for_timeout(2000)

        print("Testing Scene 4: Intelligence Console...")
        page.click("#nav-btn-agents")
        page.wait_for_timeout(1000)
        page.evaluate("startInvestigation()")
        page.wait_for_timeout(3000)

        print("Testing Scene 5: Simulator...")
        page.click("#nav-btn-simulator")
        page.wait_for_timeout(2000)

        print("Testing Scene 6: Approvals...")
        page.click("#nav-btn-approvals")
        page.wait_for_timeout(1000)
        page.click("button:has-text('Approve & Execute Mitigation Plan')")
        page.wait_for_timeout(1000)

        print("Testing Scene 7: Audit, Control Room, Integrations...")
        page.click("#nav-btn-audit")
        page.wait_for_timeout(1000)
        page.click("#nav-btn-control-room")
        page.wait_for_timeout(1000)
        page.click("#nav-btn-integrations")
        page.wait_for_timeout(2000)

        context.close()
        browser.close()
        print("All UI interactions verified successfully!")

if __name__ == "__main__":
    test_run()
