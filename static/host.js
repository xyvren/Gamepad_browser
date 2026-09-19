const $=s=>document.querySelector(s);
let lastStatus=null,currentProto='http';
function render(d){
 const slot=Number($('#host-slot').value),entry=d.slots?.find(s=>s.slot===slot);
 const mode=entry?.mode||d.mode;
 $('#server').textContent='SERVER ONLINE';$('#driver').textContent=mode==='xinput'?'XINPUT READY':'DRIVER BELUM SIAP';
 $('#url').value=currentProto==='https'?(d.https_url||d.url||''):(d.url||'');
 $('#connection').textContent=`${d.connected_count??(d.connected?1:0)} / ${d.capacity||4} stik terhubung`;
 $('#subtitle').textContent=`Stik ${slot} · ${entry?.connected?'HP terhubung':'menunggu HP'}`;
 for(const option of $('#host-slot').options){const s=d.slots?.find(s=>s.slot===Number(option.value));option.textContent=`Stik ${option.value}${s?.connected?' · Terhubung':''}`;}
 $('#notice').hidden=mode==='xinput';
 if(mode!=='xinput'){$('#notice').replaceChildren(document.createTextNode((entry?.error||d.error||'Driver belum aktif.')+' '));const a=document.createElement('a');a.href='https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0';a.target='_blank';a.rel='noreferrer';a.textContent='Driver resmi ViGEmBus ↗';$('#notice').append(a);}
 const s=entry?.state||{buttons:[],axes:[0,0,0,0],triggers:[0,0]};
 for(const [id,i]of [['axis-left',0],['axis-right',2]]){$('#'+id).style.left=(50+s.axes[i]*42)+'%';$('#'+id).style.top=(50+s.axes[i+1]*42)+'%';}
 $('#buttons').textContent=s.buttons.length?s.buttons.map(x=>x.toUpperCase()).join(' · '):'Tidak ada tombol ditekan';$('#triggers').textContent=`L2 ${Math.round(s.triggers[0]*100)}% / R2 ${Math.round(s.triggers[1]*100)}%`;$('#packets').textContent=(entry?.packets??0)+' paket input';
}
async function refresh(){try{if(!document.hidden){const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error();lastStatus=await r.json();render(lastStatus);}}catch{$('#server').textContent='SERVER OFFLINE';$('#connection').textContent='Koneksi server terputus';}finally{setTimeout(refresh,500);}}
$('#host-slot').onchange=()=>{if(lastStatus)render(lastStatus);};
$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText($('#url').value);$('#copy').textContent='Tersalin';setTimeout(()=>$('#copy').textContent='Salin',1500);}catch{$('#url').select();$('#copy').textContent='Ctrl+C';}};
const btnHttp=$('#btn-proto-http'),btnHttps=$('#btn-proto-https');
if(btnHttp&&btnHttps){
 btnHttp.onclick=()=>{
  currentProto='http';
  btnHttp.style.background='var(--accent)';btnHttp.style.color='#101214';
  btnHttps.style.background='#20252a';btnHttps.style.color='#c0c9ce';
  const qr=$('.qr');if(qr)qr.src='/api/qr?proto=http&_t='+Date.now();
  if(lastStatus)render(lastStatus);
 };
 btnHttps.onclick=()=>{
  currentProto='https';
  btnHttps.style.background='var(--accent)';btnHttps.style.color='#101214';
  btnHttp.style.background='#20252a';btnHttp.style.color='#c0c9ce';
  const qr=$('.qr');if(qr)qr.src='/api/qr?proto=https&_t='+Date.now();
  if(lastStatus)render(lastStatus);
 };
}
refresh();
