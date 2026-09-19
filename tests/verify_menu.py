"""Phone menu, layout and mapping smoke test; no controller input needed."""
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765'
def run():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE)
        assert page.locator('#phone-menu').is_visible(), 'Phone must start at menu'
        assert page.locator('.pad').is_hidden()
        assert page.locator('#run-gamepad').is_disabled()
        assert page.locator('#connected-count').is_visible()
        assert page.locator('#slot-picker button').count()==4
        page.locator('#edit-layout').click()
        assert page.locator('.pad').is_visible()
        assert page.locator('body').get_attribute('data-editing')=='true'
        control=page.locator('[data-button="cross"]');r=control.bounding_box()
        x,y=r['x']+r['width']/2,r['y']+r['height']/2
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x-25,y+55,steps=4);page.mouse.up()
        moved=control.bounding_box();assert abs(moved['y']-r['y']-55)<3
        page.locator('#save-layout').click()
        assert page.locator('#phone-menu').is_visible()
        page.locator('#edit-mapping').click()
        assert page.locator('#mapping-screen').is_visible()
        page.locator('select[data-map="cross"]').select_option('circle')
        page.locator('#swap-sticks').check()
        page.locator('#mapping-back').click()
        page.reload()
        page.locator('#edit-mapping').click()
        assert page.locator('select[data-map="cross"]').input_value()=='circle'
        assert page.locator('#swap-sticks').is_checked()
        page.locator('#reset-mapping').click()
        assert page.locator('select[data-map="cross"]').input_value()=='cross'
        assert not page.locator('#swap-sticks').is_checked()
        page.locator('#mapping-back').click();page.locator('#edit-layout').click()
        assert abs(control.bounding_box()['y']-moved['y'])<3
        page.locator('#reset-layout').click();page.locator('#save-layout').click()
        page.screenshot(path='artifacts/phone-menu.png',full_page=True)
        page.set_viewport_size({'width':844,'height':390})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors,errors
        browser.close()
    print('PASS: menu-first, disconnected Run disabled, 4 slot selectors, layout editing/save/reset, button mapping + stick swap persistence/reset, responsive menu, zero JS errors')
if __name__=='__main__':run()
