"""Mobile-viewport UI smoke test. Usage: python ui_flow.py <base_url> <screenshot_dir>"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE, OUT = sys.argv[1], Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
FIX = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parents[1] / "fixtures" / "coffee.png"
EMAIL = f"demo{int(time.time())}@mealsense.ai"


def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    print("shot", name)


with sync_playwright() as p:
    exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
    b = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
    page = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                      color_scheme=os.environ.get("UI_SCHEME", "light"))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(f"{BASE}/register")
    shot(page, "01_register")
    page.get_by_label("Name").fill("Joel")
    page.get_by_label("Email").fill(EMAIL)
    page.get_by_label("Password").fill("secret123")
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Let's personalise")).to_be_visible()
    page.get_by_label("Age").fill("42")
    page.get_by_role("button", name="Moderate").click()
    page.get_by_role("button", name="Halal").click()
    shot(page, "02_onboarding_personal")
    page.get_by_role("button", name="Continue").click()
    page.get_by_text("I consent").click()
    page.get_by_role("button", name="Type 2").click()
    page.get_by_role("button", name="Peanut").click()
    shot(page, "03_onboarding_health")
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Carbohydrate awareness").click()
    page.get_by_label("Daily calories").fill("1900")
    page.get_by_label("Daily carbs").fill("200")
    page.get_by_role("button", name="Finish").click()
    expect(page.get_by_text("Hi Joel")).to_be_visible()
    shot(page, "04_dashboard_empty")

    page.get_by_role("link", name="Capture meal").first.click()
    page.locator("input[type=file]:not([capture])").first.set_input_files(str(FIX))
    page.get_by_placeholder("e.g. chicken rice and kopi").fill("kaya toast and 2 boiled eggs")
    shot(page, "05_capture")
    page.get_by_role("button", name="ANALYZE MEAL").click()
    expect(page.get_by_text("Potential Glucose Impact")).to_be_visible(timeout=30000)
    page.wait_for_timeout(800)
    shot(page, "06_analysis_review")
    # pipeline drawer: compact progress bar, telemetry opens on demand
    expect(page.get_by_text("Analysis complete")).to_be_visible()
    page.get_by_role("button", name="Open analysis telemetry").click()
    drawer = page.get_by_role("dialog", name="Analysis telemetry")
    expect(drawer.get_by_text("Latency by step")).to_be_visible()
    expect(drawer.get_by_text("10/10 steps")).to_be_visible()
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "06a_telemetry_drawer.png"))
    drawer.get_by_role("button", name="Close").click()
    # top-3 candidates: switch to candidate 2, verify, switch back (confirm/override workflow)
    cands = page.locator("button", has_text="%").filter(has_text=". ")
    expect(cands.first).to_be_visible()
    assert cands.count() >= 3, f"expected top-3 candidates, got {cands.count()}"
    first_label = cands.nth(0).inner_text().split("\n")[0]
    second = cands.nth(1).inner_text().split("\n")[0]
    print("top-3:", [cands.nth(i).inner_text().replace("\n", " ") for i in range(3)])
    cands.nth(1).click()
    expect(page.locator("h3", has_text=second.split(". ", 1)[1].split(" ·")[0])).to_be_visible(timeout=15000)
    shot(page, "06b_candidate_override")
    page.locator("button", has_text=first_label).click()
    expect(page.locator("h3", has_text=first_label.split(". ", 1)[1].split(" ·")[0])).to_be_visible(timeout=15000)

    # correct portion of kaya toast
    card = page.locator(".card", has=page.get_by_role("heading", name="Kaya toast with butter"))
    card.get_by_role("button", name="Portion").click()
    card.locator("input[type=number]").fill("140")
    card.get_by_role("button", name="Save").click()
    expect(card.get_by_text("140 g")).to_be_visible()
    # add missing food
    page.get_by_role("button", name="Add missing food").click()
    page.get_by_placeholder("Search e.g.").fill("cucumber")
    page.get_by_role("button", name="Cucumber").first.click()
    page.get_by_role("button", name="Use Cucumber").click()
    expect(page.get_by_role("heading", name="Cucumber")).to_be_visible()
    # multi-food: numbered boxes on the photo; unidentified items must be named before saving
    boxes = page.locator("figure button[aria-label^='Item ']")
    print("boxes on photo:", boxes.count())
    while page.locator("h3", has_text="Unidentified food").count():
        unk = page.locator(".card", has=page.locator("h3", has_text="Unidentified food")).first
        title = unk.locator("h3").inner_text()
        unk.get_by_role("button", name="Name it").click()
        page.get_by_placeholder("Search e.g.").fill("bacon")
        dlg = page.get_by_role("dialog")
        dlg.get_by_role("button", name="Bacon").first.click()
        dlg.get_by_role("button", name="Use Bacon").click()
        expect(page.locator("h3", has_text=title)).to_have_count(0, timeout=15000)
        print("named", title, "-> Bacon")
    if page.locator("h3", has_text="Bacon").count() >= 2:  # merge duplicated items
        for c in page.locator(".card", has=page.locator("h3", has_text="Bacon")).all()[:2]:
            c.get_by_label("merge").check()
        page.get_by_role("button", name="Merge 2 items into one").click()
        expect(page.locator("h3", has_text="Bacon")).to_have_count(1, timeout=15000)
    if boxes.count() >= 2:
        expect(page.get_by_text("Meal composition")).to_be_visible()
        expect(page.get_by_text("Carbohydrate contribution by food (g)")).to_be_visible()
    shot(page, "07_after_corrections")
    # portion simulator: halve the kaya toast, compare, log a measured reading, apply
    sim = page.locator(".card", has=page.get_by_text("Portion simulator", exact=True))
    sim.get_by_label("Kaya toast with butter portion").fill("70")
    expect(sim.get_by_role("button", name="Apply 1 portion change(s)")).to_be_visible()
    expect(sim.locator("tr", has_text="Portion (g)").locator("td", has_text="-70")).to_be_visible(timeout=10000)
    sim.get_by_label("Glucose reading").fill("140")
    sim.get_by_label("Unit").select_option("mg/dL")
    sim.get_by_role("button", name="Log reading").click()
    expect(sim.get_by_text("7.8 mmol/L")).to_be_visible(timeout=10000)
    sim.scroll_into_view_if_needed()
    shot(page, "07b_portion_simulator")
    sim.get_by_role("button", name="Apply 1 portion change(s)").click()
    expect(card.get_by_text("70 g").first).to_be_visible(timeout=10000)
    page.get_by_role("button", name="Confirm & save meal").click()
    expect(page.get_by_text("Meal saved to your history")).to_be_visible()
    shot(page, "08_saved_meal")
    # forecast & what-if: add a second scenario and check cautions render
    expect(page.get_by_text("Forecast & what-if analysis")).to_be_visible(timeout=15000)
    page.get_by_role("button", name="Run hard right after").click()
    expect(page.get_by_text("Scenario 2:")).to_be_visible(timeout=15000)
    expect(page.get_by_text("within 15 min of eating").first).to_be_visible()
    page.get_by_text("Forecast & what-if analysis").scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    shot(page, "08b_forecast")

    page.get_by_role("link", name="History").click()
    expect(page.get_by_text("Kaya toast with butter").first).to_be_visible()
    shot(page, "09_history")
    page.get_by_role("link", name="Home").click()
    expect(page.get_by_text("Recent meals")).to_be_visible()
    page.wait_for_timeout(600)
    shot(page, "10_dashboard")
    page.goto(f"{BASE}/ai")
    expect(page.get_by_text("EXP-002").first).to_be_visible()
    shot(page, "11_ai_insights")
    page.goto(f"{BASE}/insights")
    page.wait_for_timeout(600)
    shot(page, "12_nutrition_insights")
    page.get_by_role("button", name="Menu").click()
    shot(page, "13_drawer")

    dpage = b.new_page(viewport={"width": 1366, "height": 900})
    dpage.goto(f"{BASE}/login")
    dpage.get_by_label("Email").fill(EMAIL)
    dpage.get_by_label("Password").fill("secret123")
    dpage.get_by_role("button", name="Log in").click()
    expect(dpage.get_by_text("Recent meals")).to_be_visible()
    dpage.wait_for_timeout(600)
    shot(dpage, "14_desktop_dashboard")
    dpage.get_by_role("link", name="Kaya toast", exact=False).first.click()
    expect(dpage.get_by_text("Potential Glucose Impact")).to_be_visible()
    dpage.wait_for_timeout(600)
    shot(dpage, "15_desktop_meal")
    print("EMAIL", EMAIL)
    print("JS errors:", errors)
    b.close()
