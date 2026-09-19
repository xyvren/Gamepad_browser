"""Browser -> binary WebSocket -> actual Windows XInput integration."""
import ctypes
import json
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765'
def status():return json.load(urllib.request.urlopen(BASE+'/api/status'))
class Gamepad(ctypes.Structure):
    _fields_=[('buttons',ctypes.c_ushort),('lt',ctypes.c_ubyte),('rt',ctypes.c_ubyte),('lx',ctypes.c_short),('ly',ctypes.c_short),('rx',ctypes.c_short),('ry',ctypes.c_short)]
class State(ctypes.Structure):
    _fields_=[('packet',ctypes.c_uint),('pad',Gamepad)]
xinput=ctypes.WinDLL('xinput1_4.dll')
def pads():
    result=[]
    for i in range(4):
        s=State()
        if xinput.XInputGetState(i,ctypes.byref(s))==0:result.append(s.pad)
    return result

def press(page,selector):
    r=page.locator(selector).bounding_box();page.mouse.move(r['x']+r['width']/2,r['y']+r['height']/2);page.mouse.down()

def run():
    d=status();assert d['mode']=='xinput',d
    assert d['connected_count']==0,'Close HP connections before test: this sends real controller input'
    token=d['url'].split('#')[1];errors=[];out=Path('artifacts');out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/#'+token);page.wait_for_function("document.body.dataset.connection==='online'")
        assert page.locator('#phone-menu').is_visible()
        assert page.locator('#connected-count').inner_text()=='1 / 4 terhubung'
        page.locator('#run-gamepad').click();page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('#phone-menu').is_hidden() and page.locator('#play-status').is_visible()
        press(page,'[data-button="cross"]');time.sleep(.05)
        assert any(s.buttons&0x1000 for s in pads()),'A did not reach XInput'
        page.mouse.up();time.sleep(.04)
        assert all(not(s.buttons&0x1000) for s in pads()),'A stuck'
        r=page.locator('#left-stick').bounding_box();cx,cy=r['x']+r['width']/2,r['y']+r['height']/2
        page.mouse.move(cx,cy);page.mouse.down();page.mouse.move(cx+r['width']*.3,cy);time.sleep(.05)
        assert any(s.lx>20000 for s in pads()),'Analog not in XInput'
        page.mouse.up()
        press(page,'[data-trigger="0"]');time.sleep(.05)
        assert any(s.lt==255 for s in pads()),'L2 missing'
        page.mouse.up()
        cdp=context.new_cdp_session(page)
        points=[]
        for i,name in enumerate(['cross','up']):
            b=page.locator('[data-button="'+name+'"]').bounding_box();points.append({'x':b['x']+b['width']/2,'y':b['y']+b['height']/2,'id':i+3})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points});time.sleep(.05)
        assert any(s.buttons&0x1001==0x1001 for s in pads()),'Multitouch missing'
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});time.sleep(.04)
        assert all(s.buttons==0 for s in pads())
        page.screenshot(path=str(out/'controller-landscape.png'))
        # Home long-press returns menu, not game Guide input.
        press(page,'[data-button="home"]');page.wait_for_timeout(850);page.mouse.up()
        page.wait_for_function('!document.fullscreenElement')
        assert page.locator('#phone-menu').is_visible()
        # Select another slot and remap actual game output.
        page.locator('[data-slot="3"]').click();page.wait_for_function("document.querySelector('#assigned-slot').textContent==='03'")
        assert status()['slots'][2]['connected']
        page.locator('#edit-mapping').click();page.locator('[data-map="cross"]').select_option('circle');page.locator('#mapping-back').click()
        page.locator('#run-gamepad').click();page.wait_for_function('!!document.fullscreenElement')
        press(page,'[data-button="cross"]');time.sleep(.05)
        assert any(s.buttons&0x2000 for s in pads()),'Remapped B missing'
        assert all(not(s.buttons&0x1000) for s in pads()),'Original A was not remapped'
        page.mouse.up()
        page.evaluate('document.exitFullscreen()');page.wait_for_function("document.body.dataset.screen==='menu'")
        page.wait_for_function("document.querySelector('#ping-value').textContent!=='—'")
        page.wait_for_function("document.querySelector('#input-rtt').textContent!=='—'")
        page.screenshot(path=str(out/'menu-connected.png'))
        # A second independent phone receives another slot and roster is pushed live.
        other=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        second=other.new_page();second.goto(BASE+'/#'+token);second.wait_for_function("document.body.dataset.connection==='online'")
        page.wait_for_function("document.querySelector('#connected-count').textContent==='2 / 4 terhubung'")
        assert second.locator('#assigned-slot').inner_text()!='03'
        assert second.locator('[data-slot="3"]').is_disabled()
        other.close();page.wait_for_function("document.querySelector('#connected-count').textContent==='1 / 4 terhubung'")
        page.close();time.sleep(.2)
        assert status()['connected_count']==0
        assert all(s.buttons==0 and abs(s.lx)<5000 and s.lt==0 for s in pads())
        host=browser.new_page(viewport={'width':1440,'height':1000});host.on('pageerror',lambda e:errors.append(str(e)))
        host.goto(BASE+'/host');host.wait_for_function("document.querySelector('#driver').textContent==='XINPUT READY'")
        assert host.locator('.qr').evaluate('(i)=>i.complete&&i.naturalWidth>0')
        host.screenshot(path=str(out/'desktop-station.png'));browser.close()
    assert not errors,errors
    print('PASS: menu -> Run -> real fullscreen, instant binary button/analog/trigger/multi-touch to Windows XInput, Home return, live mapping to B, slot switching, two phones/roster/exclusivity, real RTT display, disconnect neutral, dashboard, no JS errors')
if __name__=='__main__':run()
