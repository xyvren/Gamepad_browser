"""Live touch layout editor acceptance test."""
import json
import time
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
        page.wait_for_function("['online','diagnostic'].includes(document.body.dataset.connection)")
        
        # Enter edit layout from menu
        page.locator('#edit-layout').click()
        assert page.locator('body').get_attribute('data-editing') == 'true'
        assert page.locator('#edit-tools').is_visible()
        assert page.locator('.pad').bounding_box()['height'] == 390
        
        control = page.locator('[data-button="cross"]')
        old = control.bounding_box()
        x, y = old['x'] + old['width'] / 2, old['y'] + old['height'] / 2
        page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x - 70, y - 20, steps=8); page.mouse.up()
        new = control.bounding_box()
        assert abs(new['x'] - old['x'] + 70) < 3
        assert abs(new['y'] - old['y'] + 20) < 3
        
        with urllib.request.urlopen(BASE + '/api/status') as r:
            s = json.load(r)['state']
        assert s == {'buttons': [], 'axes': [0, 0, 0, 0], 'triggers': [0, 0]}, 'Editing must not send game input'
        
        page.locator('#save-layout').click()
        assert page.locator('#edit-tools').is_hidden()
        assert page.locator('#phone-menu').is_visible()
        
        page.reload()
        page.wait_for_function("['online','diagnostic'].includes(document.body.dataset.connection)")
        page.locator('#edit-layout').click()
        restored = control.bounding_box()
        assert abs(restored['x'] - new['x']) < 3, 'Layout not restored'
        
        # Reset layout restores default position
        page.locator('#reset-layout').click()
        assert abs(control.bounding_box()['x'] - old['x']) < 3, 'Reset failed'
        page.locator('#save-layout').click()
        
        for width, height in [(667, 375), (390, 844), (1024, 768)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_timeout(100)
            page.locator('#edit-layout').click()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight')
            for box in page.locator('[data-control]').all():
                r = box.bounding_box()
                assert r['x'] >= -1 and r['y'] >= -1 and r['x'] + r['width'] <= width + 1 and r['y'] + r['height'] <= height + 1, (width, height, box.get_attribute('data-control'), r)
            page.locator('#save-layout').click()
            
        # Invalid saved settings must not break controls.
        page.evaluate("localStorage.setItem('pocket-pad-layout-v2','{bad')")
        page.reload()
        page.locator('#edit-layout').click()
        assert page.locator('[data-button="cross"]').is_visible()
        assert not errors, errors
        browser.close()
    print('PASS: layout editor individual drag, scale/pos persistence, reset, boundary containment, corrupt storage recovery, zero JS errors')

if __name__ == '__main__':
    run()
