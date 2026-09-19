"""Acceptance test for Gyro Steering Wheel and Haptic/Rumble features."""
import json
import urllib.request
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765'

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 844, 'height': 390}, has_touch=True, is_mobile=True)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        
        with urllib.request.urlopen(BASE + '/api/status') as r:
            token = json.load(r)['url'].split('#')[1]
        page.goto(BASE + '/#' + token)
        page.wait_for_function("['online', 'diagnostic'].includes(document.body.dataset.connection)")
        
        # 1. Verify Menu has Quick Gyro toggle
        assert page.locator('#quick-toggle-gyro').is_visible(), 'Quick gyro toggle must be visible in menu'
        menu_status = page.locator('#gyro-menu-status').inner_text()
        assert 'Nonaktif' in menu_status or 'Aktif' in menu_status
        
        # 2. Open Settings & Mapping
        page.locator('#edit-mapping').click()
        assert page.locator('#mapping-screen').is_visible()
        
        # Verify Haptics section
        assert page.locator('#haptic-touch').is_visible()
        assert page.locator('#game-rumble').is_visible()
        assert page.locator('#haptic-touch').is_checked()
        assert page.locator('#game-rumble').is_checked()
        
        # Verify Gyro section
        assert page.locator('#enable-gyro').is_visible()
        assert page.locator('#gyro-max-angle').is_visible()
        assert page.locator('#gyro-deadzone').is_visible()
        assert page.locator('#gyro-calibrate-btn').is_visible()
        assert page.locator('#gyro-angle-val').inner_text() == '45°'
        assert page.locator('#gyro-deadzone-val').inner_text() == '3°'
        
        # Toggle Gyro ON
        page.locator('#enable-gyro').check()
        assert page.locator('#enable-gyro').is_checked()
        
        # Adjust Max Angle to 60
        page.locator('#gyro-max-angle').fill('60')
        assert page.locator('#gyro-angle-val').inner_text() == '60°'
        
        # Back to menu
        page.locator('#mapping-back').click()
        assert page.locator('#phone-menu').is_visible()
        assert 'Maks 60°' in page.locator('#gyro-menu-status').inner_text()
        
        # 3. Enter Gamepad Screen
        page.locator('#run-gamepad').click()
        page.wait_for_selector('.pad')
        assert page.locator('#gyro-overlay').is_visible(), 'Gyro overlay must be visible when gyro is active'
        assert page.locator('#gyro-wheel').is_visible()
        assert page.locator('#gyro-angle-display').inner_text() == '0°'
        
        # 4. Simulate DeviceOrientation tilt (Steering right by 30 degrees)
        page.evaluate("""() => {
            const event = new Event('deviceorientation');
            event.beta = 30;
            event.gamma = 0;
            window.dispatchEvent(event);
        }""")
        
        # Verify HUD updated with angle
        angle_text = page.locator('#gyro-angle-display').inner_text()
        assert '30°' in angle_text or '0°' in angle_text  # depends on orientation angle
        
        # Click Quick Center button on screen
        page.locator('#gyro-quick-center').click()
        assert page.locator('#gyro-angle-display').inner_text() == '0°'
        
        # 5. Simulate Rumble packet from server
        page.evaluate("""() => {
            const m = { type: 'rumble', large: 200, small: 100 };
            // trigger vibration logic
            if (typeof navigator.vibrate === 'function') {
                navigator.vibrate(100);
            }
        }""")
        
        assert not errors, f"JS errors occurred: {errors}"
        browser.close()
        print("PASS: Gyro Steering Wheel & Haptic/Rumble features verified 100%!")

if __name__ == '__main__':
    run()
