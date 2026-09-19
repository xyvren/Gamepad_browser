"""Acceptance test for button and analog resizing."""
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
        
        # Open layout editor from menu
        page.locator('#edit-layout').click()
        assert page.locator('body').get_attribute('data-editing') == 'true'
        assert page.locator('#scale-up').is_visible(), 'Scale up button must be visible in edit tools'
        assert page.locator('#scale-down').is_visible(), 'Scale down button must be visible in edit tools'
        assert page.locator('#scale-label').is_visible()
        
        cross = page.locator('[data-button="cross"]')
        initial_box = cross.bounding_box()
        initial_w = initial_box['width']
        
        # Click cross button to select it
        cross.click()
        assert cross.evaluate("el => el.classList.contains('selected')"), 'Tapped control should be selected'
        
        # Enlarge button by clicking scale up 3 times (+30%)
        page.locator('#scale-up').click()
        page.locator('#scale-up').click()
        page.locator('#scale-up').click()
        
        assert page.locator('#scale-label').inner_text() == '130%'
        enlarged_box = cross.bounding_box()
        assert enlarged_box['width'] > initial_w * 1.25, f"Expected width > {initial_w * 1.25}, got {enlarged_box['width']}"
        
        # Save layout and reload to verify persistence
        page.locator('#save-layout').click()
        assert page.locator('body').get_attribute('data-editing') == 'false'
        page.reload()
        page.wait_for_function("['online', 'diagnostic'].includes(document.body.dataset.connection)")
        
        page.locator('#edit-layout').click()
        restored_box = cross.bounding_box()
        assert abs(restored_box['width'] - enlarged_box['width']) < 2, 'Enlarged size must persist across reload'
        
        # Reset layout restores initial size
        page.locator('#reset-layout').click()
        reset_box = cross.bounding_box()
        assert abs(reset_box['width'] - initial_w) < 2, 'Reset must restore default button size'
        assert page.locator('#scale-label').inner_text() == '100%'
        
        # Test global size settings in mapping screen
        page.locator('#save-layout').click()
        page.locator('#edit-mapping').click()
        assert page.locator('#global-btn-size').is_visible(), 'Global button size slider must be available'
        page.locator('#global-btn-size').fill('140')
        page.locator('#global-btn-size').dispatch_event('input')
        assert page.locator('#btn-size-val').inner_text() == '140%'
        
        page.locator('#mapping-back').click()
        page.locator('#edit-layout').click()
        global_enlarged = cross.bounding_box()
        assert global_enlarged['width'] > initial_w * 1.3, 'Global button slider must enlarge controls'
        
        # Reset mapping restores global size to 100%
        page.locator('#save-layout').click()
        page.locator('#edit-mapping').click()
        page.locator('#reset-mapping').click()
        assert page.locator('#btn-size-val').inner_text() == '100%'
        page.locator('#mapping-back').click()
        
        # Screenshot the editing mode with enlarged controls
        page.locator('#edit-layout').click()
        page.locator('[data-button="cross"]').click()
        page.locator('#scale-up').click()
        page.locator('#scale-up').click()
        page.screenshot(path='artifacts/editing-enlarged.png')
        page.locator('#save-layout').click()
        
        assert not errors, errors
        browser.close()
    print('PASS: button individual resize, persistent scale, reset, global size slider, zero JS errors')

if __name__ == '__main__':
    run()
