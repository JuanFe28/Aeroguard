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
    parser.add_argument("--extended", action="store_true", help="Comprueba escape de HTML y descarga CSV; crea una zona temporal")
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
    downloads = ROOT / 'tmp' / 'selenium-downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    options.add_experimental_option('prefs', {'download.default_directory': str(downloads), 'download.prompt_for_download': False})
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
        driver.find_element(By.ID, "password").send_keys(os.environ.get('AEROGUARD_E2E_PASSWORD', 'Admin@12345'))
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.ID, "login-btn"))).click()
        wait.until(EC.url_contains("#/dashboard"))
        wait.until(EC.visibility_of_element_located((By.ID, "dashboard-map")))
        wait.until(lambda browser: browser.execute_script("""
            return [...document.querySelectorAll('#dashboard-map img.leaflet-tile-loaded')]
                .some(tile => tile.complete && tile.naturalWidth > 0 &&
                    tile.getBoundingClientRect().width > 0);
        """))
        print("OK: sesión autenticada y mapa renderizado")
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
        if args.extended:
            driver.execute_script("window.__exportBlob = null; const original = URL.createObjectURL.bind(URL); URL.createObjectURL = blob => { window.__exportBlob = blob; return original(blob); };")
            driver.find_element(By.ID, 'gen-det-csv').click()
            wait.until(lambda browser: browser.execute_script('return window.__exportBlob?.type.startsWith("text/csv")'))
            print('OK: botón CSV entrega CSV real')
            name = '<img src=x onerror="window.__ag_xss=1">'
            result = driver.execute_async_script("""
                const done = arguments[arguments.length - 1];
                fetch('/api/v1/zones', {method:'POST', headers:{'Content-Type':'application/json', 'Authorization':'Bearer '+localStorage.getItem('ag_token')}, body:JSON.stringify({name:arguments[0], description:'</textarea><img src=x onerror="window.__ag_xss=1">', coordinates:[[7,-73],[7,-72.99],[7.01,-73]]})})
                    .then(async response => done({status:response.status, body:await response.json()})).catch(error => done({error:String(error)}));
            """, name)
            assert result['status'] == 201, result
            zone_id = result['body']['id']
            driver.get(args.url.rstrip('/') + '/#/zones')
            wait.until(lambda browser: browser.execute_script('return window.zonesVM?.state.zones.some(zone => zone.id === arguments[0])', zone_id))
            driver.execute_script('zonesVM._selectZone(zonesVM.state.zones.find(zone => zone.id === arguments[0])); zonesVM.openEditForm();', zone_id)
            wait.until(EC.visibility_of_element_located((By.ID, 'zone-name')))
            assert driver.find_element(By.ID, 'zone-name').get_attribute('value') == name
            assert driver.execute_script('return window.__ag_xss || 0') == 0
            driver.save_screenshot(str(args.evidence_dir / 'escape_html.png'))
            driver.execute_async_script("const done=arguments[arguments.length-1]; fetch('/api/v1/zones/'+arguments[0],{method:'DELETE',headers:{Authorization:'Bearer '+localStorage.getItem('ag_token')}}).then(response=>done(response.status));", zone_id)
            print('OK: nombre y formulario escapan HTML persistido sin ejecutar eventos')
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
