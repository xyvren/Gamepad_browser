(() => {
'use strict';
const $=s=>document.querySelector(s),body=document.body,pad=$('.pad'),input=window.PadInput;
const controls=[...document.querySelectorAll('[data-control]')];
const STORE='pocket-pad-layout-v2',SETTINGS='pocket-pad-settings-v1';
const storage={get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}}};
function stored(key){try{const v=JSON.parse(storage.get(key)||'{}');return v&&typeof v==='object'&&!Array.isArray(v)?v:{};}catch{return {};}}
let saved=stored(STORE),preferences=stored(SETTINGS);
let mapping=preferences.mapping&&typeof preferences.mapping==='object'?preferences.mapping:{};
let deadzone=Number.isFinite(preferences.deadzone)?Math.max(0,Math.min(.2,preferences.deadzone)):.06;
let swapSticks=preferences.swapSticks===true;
let buttonScale=Number.isFinite(preferences.buttonScale)?Math.max(60,Math.min(200,preferences.buttonScale)):100;
let stickScale=Number.isFinite(preferences.stickScale)?Math.max(60,Math.min(200,preferences.stickScale)):100;

// Haptics & Vibration
let hapticTouch=preferences.hapticTouch!==false;
let gameRumble=preferences.gameRumble!==false;

// Gyro Steering Wheel
let enableGyro=preferences.enableGyro===true;
let gyroMaxAngle=Number.isFinite(preferences.gyroMaxAngle)?Math.max(20,Math.min(90,preferences.gyroMaxAngle)):45;
let gyroDeadzone=Number.isFinite(preferences.gyroDeadzone)?Math.max(0,Math.min(10,preferences.gyroDeadzone)):3;
let gyroZeroAngle=0,lastGyroSend=0,currentSteerAngle=0;

let token=new URLSearchParams(location.hash.slice(1)).get('token');
try{token=token||sessionStorage.getItem('pad-token');if(token)sessionStorage.setItem('pad-token',token);}catch{}
if(token&&location.hash)history.replaceState(null,'',location.pathname);
let socket,retry,attempts=0,active=true,wake,editing=false,connected=false,slot=null,desiredSlot=null,pendingSlot=false;
let homeTimer,homePulse,homePointer=null,homeLong=false,seq=0,lastSent=0,lastWire=null,flushTimer;
let selectedControl=null;
const pendingAcks=new Map(),state={buttons:[],axes:[0,0,0,0],triggers:[0,0]},held=new Map(),sticks=new Map(),drags=new Map();
const physicalAxes=[0,0,0,0],pinchPointers=new Map();
let initialPinchDist=0,initialPinchScale=1;
let roster={capacity:4,connected_count:0,slots:[]};
const labels={cross:'× / A',circle:'○ / B',square:'□ / X',triangle:'△ / Y',up:'↑ D-pad',down:'↓ D-pad',left:'← D-pad',right:'→ D-pad',l1:'L1 / LB',r1:'R1 / RB',l2:'L2 / LT',r2:'R2 / RT',l3:'L3',r3:'R3',share:'Share / Back',options:'Options / Start',home:'Home / Guide',disabled:'Nonaktif'};
const orientation=()=>pad.clientWidth>=pad.clientHeight?'landscape':'portrait';

function triggerTouchHaptic(ms=18){
 if(hapticTouch&&typeof navigator.vibrate==='function'){
  try{navigator.vibrate(ms);}catch{}
 }
}

function defaults(){const w=pad.clientWidth,h=pad.clientHeight,p=w<h,unit=$('[data-control="cross"]').offsetWidth+5,dx=unit/w*100,dy=unit/h*100,lx=p?22:16,rx=p?78:84,cy=p?38:48;return {l2:[p?13:12,13],l1:[p?35:27,13],r1:[p?65:73,13],r2:[p?87:88,13],up:[lx,cy-dy],left:[lx-dx,cy],right:[lx+dx,cy],down:[lx,cy+dy],triangle:[rx,cy-dy],square:[rx-dx,cy],circle:[rx+dx,cy],cross:[rx,cy+dy],share:[p?40:43,p?24:30],home:[50,p?48:43],options:[p?60:57,p?24:30],'left-stick':[p?26:33,70],'right-stick':[p?74:67,70],l3:[p?26:33,p?84:92],r3:[p?74:67,p?84:92]};}
function getScale(el){
 if(!el)return buttonScale/100;
 const id=el.dataset.control,custom=saved[orientation()]||{};
 if(Array.isArray(custom[id])&&custom[id].length>=3&&Number.isFinite(custom[id][2]))return custom[id][2];
 return id.includes('stick')?stickScale/100:buttonScale/100;
}
function updateScaleLabel(){
 const scale=selectedControl?getScale(selectedControl):(buttonScale/100);
 const pct=Math.round(scale*100)+'%';
 const label=$('#scale-label');if(label)label.textContent=pct;
}
function place(el,x,y,scale){
 const w=pad.clientWidth,h=pad.clientHeight;if(!w||!h)return [x,y,scale||1];
 if(scale===undefined)scale=getScale(el);
 scale=Number.isFinite(scale)?Math.max(.6,Math.min(2.2,scale)):1;
 el.style.setProperty('--scale',scale);
 const hx=el.offsetWidth/2+4,hy=el.offsetHeight/2+4;
 x=Math.max(hx,Math.min(w-hx,x*w/100));y=Math.max(hy,Math.min(h-hy,y*h/100));
 el.style.left=x/w*100+'%';el.style.top=y/h*100+'%';
 return [Number((x/w*100).toFixed(2)),Number((y/h*100).toFixed(2)),Number(scale.toFixed(2))];
}
function layout(){
 if(!pad.clientWidth||!pad.clientHeight)return;
 const defs=defaults(),custom=saved[orientation()]||{};
 for(const el of controls){
  const id=el.dataset.control;
  let v=custom[id],x,y,s;
  if(Array.isArray(v)&&v.length>=2&&v.slice(0,2).every(n=>Number.isFinite(n)&&n>=0&&n<=100)){
   x=v[0];y=v[1];s=(v.length>=3&&Number.isFinite(v[2]))?v[2]:(id.includes('stick')?stickScale/100:buttonScale/100);
  }else{
   const def=defs[id]||[50,50];x=def[0];y=def[1];s=id.includes('stick')?stickScale/100:buttonScale/100;
  }
  place(el,x,y,s);
 }
 body.dataset.ready='true';
 updateScaleLabel();
}
function selectControl(el){
 selectedControl=el;
 controls.forEach(c=>c.classList.toggle('selected',c===el));
 updateScaleLabel();
}
function changeScale(delta){
 const key=orientation();
 if(!saved[key]||typeof saved[key]!=='object'||Array.isArray(saved[key]))saved[key]={};
 if(selectedControl){
  const id=selectedControl.dataset.control;
  const cur=saved[key][id]||[parseFloat(selectedControl.style.left)||50,parseFloat(selectedControl.style.top)||50,getScale(selectedControl)];
  const newScale=Math.round((Math.max(.6,Math.min(2.2,(cur[2]||getScale(selectedControl))+delta)))*10)/10;
  const pos=place(selectedControl,cur[0],cur[1],newScale);
  saved[key][id]=pos;
  updateScaleLabel();
  persistLayout();
 }else{
  buttonScale=Math.max(60,Math.min(200,Math.round(buttonScale+delta*100)));
  stickScale=Math.max(60,Math.min(200,Math.round(stickScale+delta*100)));
  for(const el of controls){
   const id=el.dataset.control;
   const cur=saved[key][id]||[parseFloat(el.style.left)||50,parseFloat(el.style.top)||50,getScale(el)];
   const isStick=id.includes('stick');
   const baseScale=isStick?stickScale/100:buttonScale/100;
   const newScale=Math.round((Math.max(.6,Math.min(2.2,(cur[2]||baseScale)+delta)))*10)/10;
   const pos=place(el,cur[0],cur[1],newScale);
   saved[key][id]=pos;
  }
  updateScaleLabel();
  persistLayout();
  persistSettings();
 }
}
function persistLayout(){storage.set(STORE,JSON.stringify(saved));}
function persistSettings(){storage.set(SETTINGS,JSON.stringify({mapping,deadzone,swapSticks,buttonScale,stickScale,hapticTouch,gameRumble,enableGyro,gyroMaxAngle,gyroDeadzone}));}
function sendState(force=false,critical=true){
 if(!connected||pendingSlot||socket?.readyState!==1)return;
 if(socket.bufferedAmount>4096){socket.close(4000,'Input queue stalled');return;}
 if(!critical&&socket.bufferedAmount>1024){if(!flushTimer)flushTimer=setTimeout(()=>{flushTimer=null;sendState(false,false);},4);return;}
 const packet=input.encode(state,seq),bytes=new Uint8Array(packet);
 if(!force&&lastWire&&bytes.subarray(0,12).every((v,i)=>v===lastWire[i]))return;
 const now=performance.now();if(seq%30===0){pendingAcks.set(seq,now);if(pendingAcks.size>64)pendingAcks.delete(pendingAcks.keys().next().value);}
 socket.send(packet);lastWire=bytes;lastSent=now;seq=(seq+1)>>>0;
}
function aggregate(){const mapped=input.mapButtons([...held.values()],mapping);state.buttons=mapped.buttons;state.triggers=mapped.triggers;sendState();}
function reset(){clearTimeout(homeTimer);clearTimeout(homePulse);homePointer=null;held.clear();sticks.clear();physicalAxes.fill(0);state.buttons=[];state.axes=[0,0,0,0];state.triggers=[0,0];document.querySelectorAll('.pressed,.active').forEach(e=>e.classList.remove('pressed','active'));document.querySelectorAll('.knob').forEach(e=>e.style.transform='');sendState(true);}

function computeSteeringAngle(e){
 const orient=window.screen?.orientation?.angle??(window.orientation||0);
 if(orient===90)return -(e.beta||0);
 if(orient===270||orient===-90)return e.beta||0;
 return e.gamma||0;
}

function handleOrientation(e){
 if(!enableGyro||body.dataset.screen!=='play')return;
 if(e.beta===null&&e.gamma===null)return;
 const raw=computeSteeringAngle(e);
 let diff=raw-gyroZeroAngle;
 while(diff>180)diff-=360;
 while(diff<-180)diff+=360;
 currentSteerAngle=diff;
 let steerVal=0;
 const absDiff=Math.abs(diff);
 if(absDiff>gyroDeadzone){
  const sign=diff>0?1:-1;
  const effective=(absDiff-gyroDeadzone)/Math.max(1,(gyroMaxAngle-gyroDeadzone));
  steerVal=sign*Math.min(1.0,effective);
 }
 if(!sticks.has($('#left-stick'))){
  physicalAxes[0]=steerVal;
  state.axes=swapSticks?[...physicalAxes.slice(2),...physicalAxes.slice(0,2)]:physicalAxes.slice();
  const now=performance.now();
  if(now-lastGyroSend>=16){
   lastGyroSend=now;
   sendState(false,false);
  }
 }
 const visualAngle=Math.max(-120,Math.min(120,diff));
 const wheel=$('#gyro-wheel');if(wheel)wheel.style.transform=`rotate(${visualAngle.toFixed(1)}deg)`;
 const display=$('#gyro-angle-display');if(display)display.textContent=`${diff>=0?'+':''}${Math.round(diff)}°`;
}

function calibrateGyro(){
 gyroZeroAngle=currentSteerAngle+gyroZeroAngle;
 triggerTouchHaptic(25);
 const display=$('#gyro-angle-display');if(display)display.textContent='0°';
 const wheel=$('#gyro-wheel');if(wheel)wheel.style.transform='rotate(0deg)';
}

async function requestGyroPermission(){
 if(typeof DeviceOrientationEvent!=='undefined'&&typeof DeviceOrientationEvent.requestPermission==='function'){
  try{const res=await DeviceOrientationEvent.requestPermission();return res==='granted';}catch{return false;}
 }
 return true;
}

function updateGyroUI(){
 const overlay=$('#gyro-overlay');
 if(overlay)overlay.hidden=!enableGyro||body.dataset.screen!=='play';
 const statusSmall=$('#gyro-menu-status');
 if(statusSmall){statusSmall.textContent=enableGyro?`Aktif · Maks ${gyroMaxAngle}°`:'Nonaktif · Aktifkan untuk main game balap';}
 const isHttps=location.protocol==='https:';
 const httpsBox=$('#gyro-https-box');
 if(httpsBox){
  httpsBox.hidden=isHttps;
  if(!isHttps){
   const link=$('#gyro-https-link');
   if(link)link.href=`https://${location.hostname}:8766/${location.search}#token=${token||''}`;
  }
 }
}

function screen(name){reset();drags.clear();selectControl(null);editing=name==='edit';body.dataset.editing=String(editing);body.dataset.screen=name;$('#phone-menu').hidden=name!=='menu';$('#mapping-screen').hidden=name!=='mapping';$('#edit-tools').hidden=!editing;$('#play-status').hidden=name!=='play';updateGyroUI();controls.forEach(el=>el.classList.remove('dragging','selected'));persistLayout();if(name==='play'||name==='edit')layout();}
function menu(){screen('menu');try{screenOrientationUnlock();if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});}catch{}}
function screenOrientationUnlock(){try{window.screen.orientation.unlock();}catch{}}
function showRoster(data){
 if(Array.isArray(data.slots))roster={capacity:data.capacity||4,connected_count:data.connected_count||0,slots:data.slots};
 $('#connected-count').textContent=`${roster.connected_count} / ${roster.capacity} terhubung`;
 $('#play-count').textContent=`${roster.connected_count}/${roster.capacity}`;
 $('#play-slot').textContent=slot?`P${slot}`:'P—';
 for(const button of document.querySelectorAll('[data-slot]')){const n=Number(button.dataset.slot),entry=roster.slots.find(s=>s.slot===n),mine=connected&&n===slot,busy=!!entry?.connected&&!mine;
  button.classList.toggle('selected',mine);button.disabled=busy||pendingSlot;button.setAttribute('aria-pressed',String(mine));button.querySelector('small').textContent=mine?'Kamu':busy?'Dipakai':'Kosong';
 }
}
function connectionUI(){
 $('#assigned-slot').textContent=connected?String(slot).padStart(2,'0'):'—';
 $('#assigned-name').textContent=connected?`Stik ${slot} · perangkat ini`:'Belum mendapat slot';
 $('#connection-status').textContent=connected?(body.dataset.connection==='online'?'Terhubung · XInput':'Mode diagnostik'):(body.dataset.connection==='connecting'?'Menghubungkan…':'Belum terhubung');
 $('#connection-detail').textContent=connected?'Siap menerima input dari HP ini.':token?'Pastikan server aktif dan slot tersedia.':'Scan QR dari dashboard desktop.';
 $('#run-gamepad').disabled=!connected||pendingSlot;
 showRoster(roster);
 updateGyroUI();
}
function connect(){
 clearTimeout(retry);if(!token||!active||socket?.readyState<2)return;
 body.dataset.connection='connecting';connectionUI();
 const url=`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws?token=${encodeURIComponent(token)}${desiredSlot?`&slot=${desiredSlot}`:''}`;
 socket=new WebSocket(url);socket.binaryType='arraybuffer';
 socket.onmessage=e=>{
  let m;try{m=JSON.parse(e.data);}catch{return;}
  if(m.type==='ready'){connected=true;pendingSlot=false;attempts=0;slot=m.slot||1;desiredSlot=slot;lastWire=null;body.dataset.connection=m.mode==='xinput'?'online':'diagnostic';$('#menu-notice').textContent=m.mode==='xinput'?'Input dikirim langsung saat tombol disentuh. Gunakan Wi-Fi 5 GHz dekat router untuk hasil terbaik.':m.message||'Mode tes. Input belum diterima game.';showRoster(m);connectionUI();reset();}
  else if(m.type==='roster')showRoster(m);
  else if(m.type==='rumble'){
   if(gameRumble&&typeof navigator.vibrate==='function'){
    const intensity=Math.max(m.large||0,m.small||0);
    if(intensity>0){
     const ms=Math.min(250,Math.round(40+(intensity/255)*160));
     try{navigator.vibrate(ms);}catch{}
    }else{
     try{navigator.vibrate(0);}catch{}
    }
   }
  }
  else if(m.type==='error'){pendingSlot=false;$('#menu-notice').textContent=m.message||'Slot tidak tersedia.';connectionUI();}
  else if(m.type==='pong'&&typeof m.time==='number')$('#ping-value').textContent=Math.max(0,performance.now()-m.time).toFixed(1);
  else if(m.type==='ack'){const start=pendingAcks.get(m.seq);if(start!==undefined){$('#input-rtt').textContent=(performance.now()-start).toFixed(1);pendingAcks.delete(m.seq);}if(Number.isFinite(m.server_ms))$('#server-time').textContent=m.server_ms.toFixed(2);}
 };
 socket.onclose=()=>{connected=false;pendingSlot=false;reset();pendingAcks.clear();clearTimeout(flushTimer);flushTimer=null;slot=null;body.dataset.connection='offline';for(const id of ['ping-value','input-rtt','server-time'])$('#'+id).textContent='—';connectionUI();$('#menu-notice').textContent='Koneksi terputus. Periksa Wi-Fi, pilih slot kosong, atau scan ulang QR bila server di-restart.';if(active)retry=setTimeout(connect,Math.min(5000,500*++attempts));};
 socket.onerror=()=>{body.dataset.connection='offline';connectionUI();};
}
async function acquireWake(){try{if(!wake||wake.released)wake=await navigator.wakeLock?.request('screen');}catch{}}
async function fullscreen(){try{if(!document.fullscreenElement&&document.documentElement.requestFullscreen){await document.documentElement.requestFullscreen();try{await window.screen.orientation.lock('landscape');}catch{}}}catch{}acquireWake();}
$('#run-gamepad').onclick=async()=>{if(!connected||pendingSlot)return;if(enableGyro)await requestGyroPermission();screen('play');fullscreen();};
$('#edit-layout').onclick=()=>screen('edit');
$('#edit-mapping').onclick=()=>screen('mapping');
$('#mapping-back').onclick=menu;
$('#save-layout').onclick=menu;
$('#reset-layout').onclick=()=>{delete saved[orientation()];persistLayout();selectControl(null);layout();};
$('#fullscreen').onclick=fullscreen;
$('#scale-up').onclick=()=>changeScale(.1);
$('#scale-down').onclick=()=>changeScale(-.1);
$('#reconnect').onclick=()=>{attempts=0;desiredSlot=null;if(socket?.readyState<2)socket.close();else connect();};
for(const button of document.querySelectorAll('[data-slot]'))button.onclick=()=>{
 const target=Number(button.dataset.slot);if(target===slot||pendingSlot)return;
 if(connected){reset();pendingSlot=true;connectionUI();socket.send(JSON.stringify({type:'select',slot:target}));}
 else{desiredSlot=target;if(socket?.readyState<2)socket.close();else connect();}
};
// Map the physical controls, keeping their original labels on the playing surface.
for(const source of [...input.buttons,'l2','r2']){
 const row=document.createElement('label');row.className='mapping-row';
 const label=document.createElement('span');label.textContent=labels[source];
 const select=document.createElement('select');select.dataset.map=source;select.setAttribute('aria-label',`Mapping ${labels[source]}`);
 for(const target of input.outputs){const option=document.createElement('option');option.value=target;option.textContent=labels[target];select.append(option);}
 select.value=input.outputs.includes(mapping[source])?mapping[source]:source;
 select.onchange=()=>{reset();mapping[source]=select.value;persistSettings();};row.append(label,select);$('#mapping-list').append(row);
}
$('#swap-sticks').checked=swapSticks;$('#swap-sticks').onchange=e=>{reset();swapSticks=e.target.checked;persistSettings();};
$('#deadzone').value=Math.round(deadzone*100);$('#deadzone-value').textContent=Math.round(deadzone*100)+'%';
$('#deadzone').oninput=e=>{deadzone=Number(e.target.value)/100;$('#deadzone-value').textContent=e.target.value+'%';persistSettings();};
const btnSizeInput=$('#global-btn-size'),btnSizeVal=$('#btn-size-val');
if(btnSizeInput){
 btnSizeInput.value=buttonScale;if(btnSizeVal)btnSizeVal.textContent=buttonScale+'%';
 btnSizeInput.oninput=e=>{buttonScale=Number(e.target.value);if(btnSizeVal)btnSizeVal.textContent=buttonScale+'%';persistSettings();layout();};
}
const stickSizeInput=$('#global-stick-size'),stickSizeVal=$('#stick-size-val');
if(stickSizeInput){
 stickSizeInput.value=stickScale;if(stickSizeVal)stickSizeVal.textContent=stickScale+'%';
 stickSizeInput.oninput=e=>{stickScale=Number(e.target.value);if(stickSizeVal)stickSizeVal.textContent=stickScale+'%';persistSettings();layout();};
}

// Haptic & Vibration DOM listeners
const hapticTouchBox=$('#haptic-touch');
if(hapticTouchBox){hapticTouchBox.checked=hapticTouch;hapticTouchBox.onchange=e=>{hapticTouch=e.target.checked;if(hapticTouch)triggerTouchHaptic(20);persistSettings();};}
const gameRumbleBox=$('#game-rumble');
if(gameRumbleBox){gameRumbleBox.checked=gameRumble;gameRumbleBox.onchange=e=>{gameRumble=e.target.checked;persistSettings();};}

// Gyro DOM listeners
const enableGyroBox=$('#enable-gyro');
if(enableGyroBox){
 enableGyroBox.checked=enableGyro;
 enableGyroBox.onchange=async e=>{
  enableGyro=e.target.checked;
  if(enableGyro)await requestGyroPermission();
  updateGyroUI();
  persistSettings();
 };
}
const gyroAngleInput=$('#gyro-max-angle'),gyroAngleVal=$('#gyro-angle-val');
if(gyroAngleInput){
 gyroAngleInput.value=gyroMaxAngle;if(gyroAngleVal)gyroAngleVal.textContent=gyroMaxAngle+'°';
 gyroAngleInput.oninput=e=>{gyroMaxAngle=Number(e.target.value);if(gyroAngleVal)gyroAngleVal.textContent=gyroMaxAngle+'°';updateGyroUI();persistSettings();};
}
const gyroDeadzoneInput=$('#gyro-deadzone'),gyroDeadzoneVal=$('#gyro-deadzone-val');
if(gyroDeadzoneInput){
 gyroDeadzoneInput.value=gyroDeadzone;if(gyroDeadzoneVal)gyroDeadzoneVal.textContent=gyroDeadzone+'°';
 gyroDeadzoneInput.oninput=e=>{gyroDeadzone=Number(e.target.value);if(gyroDeadzoneVal)gyroDeadzoneVal.textContent=gyroDeadzone+'°';persistSettings();};
}
const gyroCalBtn=$('#gyro-calibrate-btn');
if(gyroCalBtn)gyroCalBtn.onclick=calibrateGyro;
const gyroQuickCenter=$('#gyro-quick-center');
if(gyroQuickCenter)gyroQuickCenter.onclick=calibrateGyro;
const quickToggleGyro=$('#quick-toggle-gyro');
if(quickToggleGyro){
 quickToggleGyro.onclick=async()=>{
  enableGyro=!enableGyro;
  if(enableGyro)await requestGyroPermission();
  if(enableGyroBox)enableGyroBox.checked=enableGyro;
  triggerTouchHaptic(20);
  updateGyroUI();
  persistSettings();
 };
}

$('#reset-mapping').onclick=()=>{
 reset();mapping={};deadzone=.06;swapSticks=false;buttonScale=100;stickScale=100;
 hapticTouch=true;gameRumble=true;enableGyro=false;gyroMaxAngle=45;gyroDeadzone=3;
 for(const select of document.querySelectorAll('[data-map]'))select.value=select.dataset.map;
 $('#deadzone').value=6;$('#deadzone-value').textContent='6%';$('#swap-sticks').checked=false;
 if(btnSizeInput){btnSizeInput.value=100;if(btnSizeVal)btnSizeVal.textContent='100%';}
 if(stickSizeInput){stickSizeInput.value=100;if(stickSizeVal)stickSizeVal.textContent='100%';}
 if(hapticTouchBox)hapticTouchBox.checked=true;
 if(gameRumbleBox)gameRumbleBox.checked=true;
 if(enableGyroBox)enableGyroBox.checked=false;
 if(gyroAngleInput){gyroAngleInput.value=45;if(gyroAngleVal)gyroAngleVal.textContent='45°';}
 if(gyroDeadzoneInput){gyroDeadzoneInput.value=3;if(gyroDeadzoneVal)gyroDeadzoneVal.textContent='3°';}
 persistSettings();layout();updateGyroUI();
};

pad.addEventListener('pointerdown',e=>{
 if(editing&&e.target===pad){selectControl(null);}
});
for(const el of controls){
 el.addEventListener('pointerdown',e=>{
  if(!editing)return;
  e.preventDefault();e.stopImmediatePropagation();
  selectControl(el);
  if([...drags.values()].some(d=>d.el===el))return;
  const r=el.getBoundingClientRect();
  drags.set(e.pointerId,{el,dx:e.clientX-r.left-r.width/2,dy:e.clientY-r.top-r.height/2});
  el.setPointerCapture(e.pointerId);el.classList.add('dragging');
 },true);
 el.addEventListener('pointermove',e=>{
  const d=drags.get(e.pointerId);if(!d)return;
  e.preventDefault();e.stopImmediatePropagation();
  const r=pad.getBoundingClientRect(),curScale=getScale(d.el);
  const pos=place(d.el,(e.clientX-r.left-d.dx)/r.width*100,(e.clientY-r.top-d.dy)/r.height*100,curScale);
  const key=orientation();if(!saved[key]||typeof saved[key]!=='object'||Array.isArray(saved[key]))saved[key]={};
  saved[key][d.el.dataset.control]=pos;
 },true);
 const stop=e=>{const d=drags.get(e.pointerId);if(!d)return;drags.delete(e.pointerId);d.el.classList.remove('dragging');persistLayout();e.stopImmediatePropagation();};
 for(const event of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(event,stop,true);
}
// Two-finger pinch to resize in edit mode
pad.addEventListener('pointerdown',e=>{
 if(!editing)return;
 pinchPointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
 if(pinchPointers.size===2){
  const pts=[...pinchPointers.values()];
  initialPinchDist=Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y);
  initialPinchScale=selectedControl?getScale(selectedControl):(buttonScale/100);
 }
});
pad.addEventListener('pointermove',e=>{
 if(!editing||pinchPointers.size<2)return;
 pinchPointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
 const pts=[...pinchPointers.values()];
 const dist=Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y);
 if(initialPinchDist>15){
  const factor=dist/initialPinchDist;
  const targetScale=Math.round(Math.max(.6,Math.min(2.2,initialPinchScale*factor))*10)/10;
  const key=orientation();if(!saved[key]||typeof saved[key]!=='object'||Array.isArray(saved[key]))saved[key]={};
  if(selectedControl){
   const cur=saved[key][selectedControl.dataset.control]||[parseFloat(selectedControl.style.left)||50,parseFloat(selectedControl.style.top)||50];
   saved[key][selectedControl.dataset.control]=place(selectedControl,cur[0],cur[1],targetScale);
  }else{
   buttonScale=Math.round(targetScale*100);
   for(const c of controls){const cur=saved[key][c.dataset.control]||[parseFloat(c.style.left)||50,parseFloat(c.style.top)||50];saved[key][c.dataset.control]=place(c,cur[0],cur[1],targetScale);}
   persistSettings();
  }
  updateScaleLabel();
 }
});
const removePinch=e=>{
 if(pinchPointers.has(e.pointerId)){pinchPointers.delete(e.pointerId);if(pinchPointers.size<2){persistLayout();}}
};
for(const event of ['pointerup','pointercancel'])pad.addEventListener(event,removePinch);

for(const el of document.querySelectorAll('[data-button]:not([data-button="home"]),[data-trigger]')){
 el.addEventListener('pointerdown',e=>{
  if(body.dataset.screen!=='play')return;
  e.preventDefault();
  triggerTouchHaptic(18);
  el.setPointerCapture(e.pointerId);
  held.set(e.pointerId,el.dataset.control);
  aggregate();
  el.classList.add('pressed');
 });
 const release=e=>{if(!held.has(e.pointerId))return;held.delete(e.pointerId);aggregate();if(![...held.values()].includes(el.dataset.control))el.classList.remove('pressed');};
 for(const event of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(event,release);
}
const home=$('[data-button="home"]');
home.addEventListener('pointerdown',e=>{
 if(body.dataset.screen!=='play'||homePointer!==null)return;
 e.preventDefault();
 triggerTouchHaptic(25);
 home.setPointerCapture(e.pointerId);
 homePointer=e.pointerId;homeLong=false;home.classList.add('pressed');
 homeTimer=setTimeout(()=>{homeLong=true;menu();},750);
});
home.addEventListener('pointerup',e=>{if(e.pointerId!==homePointer)return;clearTimeout(homeTimer);homePointer=null;home.classList.remove('pressed');if(!homeLong&&body.dataset.screen==='play'){held.set('home-pulse','home');aggregate();homePulse=setTimeout(()=>{held.delete('home-pulse');aggregate();},70);}});
for(const event of ['pointercancel','lostpointercapture'])home.addEventListener(event,e=>{if(e.pointerId!==homePointer)return;clearTimeout(homeTimer);homePointer=null;home.classList.remove('pressed');});
for(const [id,offset] of [['left-stick',0],['right-stick',2]]){
 const el=$('#'+id),knob=el.querySelector('.knob');
 function move(event){const data=sticks.get(el);if(!data||data.id!==event.pointerId||body.dataset.screen!=='play')return;const samples=event.getCoalescedEvents?.(),e=samples?.length?samples[samples.length-1]:event;let x=(e.clientX-data.cx)/data.max,y=(e.clientY-data.cy)/data.max;const n=Math.hypot(x,y);if(n>1){x/=n;y/=n;}const v=input.analog(x,y,deadzone);physicalAxes[offset]=v[0];physicalAxes[offset+1]=v[1];state.axes=swapSticks?[...physicalAxes.slice(2),...physicalAxes.slice(0,2)]:physicalAxes.slice();sendState(false,false);knob.style.transform=`translate3d(${x*data.max}px,${y*data.max}px,0)`;}
 el.addEventListener('pointerdown',e=>{
  if(body.dataset.screen!=='play'||sticks.has(el))return;
  e.preventDefault();
  triggerTouchHaptic(15);
  const r=el.getBoundingClientRect();
  sticks.set(el,{id:e.pointerId,cx:r.left+r.width/2,cy:r.top+r.height/2,max:r.width*.34});
  el.setPointerCapture(e.pointerId);
  el.classList.add('active');
  move(e);
 });
 el.addEventListener('onpointerrawupdate' in window?'pointerrawupdate':'pointermove',move);
 const release=e=>{if(sticks.get(el)?.id!==e.pointerId)return;sticks.delete(el);physicalAxes[offset]=physicalAxes[offset+1]=0;state.axes=swapSticks?[...physicalAxes.slice(2),...physicalAxes.slice(0,2)]:physicalAxes.slice();sendState();el.classList.remove('active');knob.style.transform='';};
 for(const event of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(event,release);
}
window.addEventListener('deviceorientation',handleOrientation);
window.addEventListener('resize',()=>{reset();drags.clear();controls.forEach(e=>e.classList.remove('dragging'));layout();});
window.addEventListener('blur',reset);
window.addEventListener('pagehide',()=>{active=false;reset();persistLayout();socket?.close();});
window.addEventListener('pageshow',()=>{active=!document.hidden;connect();});
document.addEventListener('visibilitychange',()=>{active=!document.hidden;reset();if(active){connect();if(body.dataset.screen==='play')acquireWake();}else{clearTimeout(retry);socket?.close();}});
document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement&&body.dataset.screen==='play')menu();layout();});
document.addEventListener('contextmenu',e=>{if(body.dataset.screen==='play'||editing)e.preventDefault();});
// A held-state safety heartbeat, NOT an input dispatch interval.
setInterval(()=>{if(active&&connected&&performance.now()-lastSent>=100)sendState(true);},50);
setInterval(()=>{if(active&&connected&&socket?.readyState===1)socket.send(JSON.stringify({type:'ping',time:performance.now()}));},1000);
async function refreshOfflineRoster(){if(active&&!connected){try{const r=await fetch('/api/status',{cache:'no-store'});if(r.ok)showRoster(await r.json());}catch{}}}
setInterval(refreshOfflineRoster,2000);
connectionUI();connect();refreshOfflineRoster();
})();
