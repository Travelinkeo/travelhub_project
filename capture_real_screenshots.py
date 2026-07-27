import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

artifact_dir = r"C:\Users\ARMANDO\.gemini\antigravity\brain\b61c38ba-47ea-41c8-82d1-fd3f1c9fa1de"
promo_dir = r"c:\Users\ARMANDO\travelhub_project\capturas_promocionales"
os.makedirs(promo_dir, exist_ok=True)

# 1. Login via Selenium UI Form
print("Navigating to login page...")
driver.get("http://localhost:8000/accounts/login/")
time.sleep(2)

try:
    user_input = driver.find_element(By.NAME, "username")
    pass_input = driver.find_element(By.NAME, "password")

    user_input.clear()
    user_input.send_keys("admin")
    pass_input.clear()
    pass_input.send_keys("admin123")
    pass_input.send_keys(Keys.RETURN)

    time.sleep(4)
    print(f"Current URL after login submit: {driver.current_url}")
except Exception as e:
    print(f"Login error: {e}")

# 2. Capture pages
pages = [
    ("real_landing.png", "1_landing_page.png", "http://localhost:8000/"),
    (
        "real_dashboard.png",
        "2_dashboard_operaciones.png",
        "http://localhost:8000/bookings/dashboard/modern/",
    ),
    (
        "real_gds_analyzer.png",
        "3_analizador_gds.png",
        "http://localhost:8000/system/intelligence/gds-analyzer/",
    ),
    (
        "real_brain_assistant.png",
        "4_asistente_brain_ia.png",
        "http://localhost:8000/accounting/asistente/",
    ),
    ("real_wiki_gds.png", "5_wiki_gds.png", "http://localhost:8000/system/wiki/gds/"),
    (
        "real_configuracion.png",
        "6_configuracion_agencia.png",
        "http://localhost:8000/system/setup/perfil/",
    ),
]

for art_name, promo_name, url in pages:
    art_path = os.path.join(artifact_dir, art_name)
    promo_path = os.path.join(promo_dir, promo_name)

    driver.get(url)
    time.sleep(3)

    print(f"Capturing {url} -> Current URL: {driver.current_url}")

    driver.save_screenshot(art_path)
    driver.save_screenshot(promo_path)
    print(f"  -> Saved {art_name} / {promo_name} ({os.path.getsize(art_path)} bytes)")

driver.quit()
print("🎉 ALL REAL SYSTEM SCREENSHOTS CAPTURED SUCCESSFULLY!")
