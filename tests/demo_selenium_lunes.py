r"""Recorrido visible en Edge: login demo, mapa, sensores y reportes.

Ejecutar desde la raíz: .\venv\Scripts\python.exe tests\demo_selenium_lunes.py
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:3000")
    parser.add_argument("--headless", action="store_true", help="Verificación sin abrir ventanas")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    if args.url.rstrip("/") == "http://127.0.0.1:3000":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "expo_local.py")], check=True)
    try:
        with urlopen(args.url, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"Frontend no disponible: {args.url}")
    except (URLError, OSError) as error:
        raise RuntimeError(f"No se puede abrir {args.url}") from error

    os.chdir(ROOT)
    os.environ.setdefault("WDM_LOCAL", "1")
    options = webdriver.EdgeOptions()
    if args.headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")
    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.page_load_strategy = "eager"
    # WebDriver crea un perfil temporal; no usa la sesión personal del navegador.
    driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence = args.evidence_dir / "evidencia_selenium.png"
    try:
        driver.set_page_load_timeout(45)
        wait = WebDriverWait(driver, 35)
        driver.get(f"{args.url.rstrip('/')}/#/login")
        wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("admin")
        driver.find_element(By.ID, "password").send_keys("Admin123!")
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.ID, "login-btn"))).click()
        wait.until(EC.url_contains("#/dashboard"))
        wait.until(EC.visibility_of_element_located((By.ID, "dashboard-map")))
        wait.until(lambda browser: browser.execute_script("""
            return [...document.querySelectorAll('#dashboard-map img.leaflet-tile-loaded')]
                .some(tile => tile.complete && tile.naturalWidth > 0 &&
                    tile.getBoundingClientRect().width > 0);
        """))
        print("OK: sesión demo y mapa renderizado")
        time.sleep(2)
        driver.save_screenshot(str(args.evidence_dir / "evidencia_selenium_mapa.png"))

        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.nav-item[href="#/sensors"]'))).click()
        wait.until(EC.url_contains("#/sensors"))
        wait.until(EC.visibility_of_element_located((By.ID, "sensors-grid")))
        wait.until(lambda browser: browser.find_element(By.ID, "stat-sensors-total").text not in ("", "—"))
        print("OK: vista Sensores con datos")
        time.sleep(2)

        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.nav-item[href="#/reports"]'))).click()
        wait.until(EC.url_contains("#/reports"))
        wait.until(EC.visibility_of_element_located((By.ID, "det-date-from")))
        print("OK: vista Reportes")
        time.sleep(2)
        if not driver.save_screenshot(str(evidence)):
            raise RuntimeError("No se pudo guardar la captura de evidencia")
        print(f"Evidencia: {evidence}")
    except Exception:
        driver.save_screenshot(str(args.evidence_dir / "evidencia_selenium_error.png"))
        raise
    finally:
        driver.quit()
    print("✅ PRUEBA E2E SELENIUM COMPLETADA CON ÉXITO")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
