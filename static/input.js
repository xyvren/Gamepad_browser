/* Shared, testable wire format and physical-to-logical input mapping. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PadInput=api;})(globalThis,()=>{
'use strict';
const buttons=['cross','circle','square','triangle','up','down','left','right','l1','r1','l3','r3','share','options','home'];
const outputs=[...buttons,'l2','r2','disabled'];
function encode(state,seq){
 const packet=new ArrayBuffer(16),v=new DataView(packet);
 let mask=0;for(const b of state.buttons){const i=buttons.indexOf(b);if(i>=0)mask|=1<<i;}
 v.setUint16(0,mask,true);
 for(let i=0;i<4;i++)v.setInt16(2+i*2,Math.round(Math.max(-1,Math.min(1,state.axes[i]))*32767),true);
 v.setUint8(10,Math.round(state.triggers[0]*255));v.setUint8(11,Math.round(state.triggers[1]*255));v.setUint32(12,seq>>>0,true);return packet;
}
function mapButtons(sources,mapping){
 const held=new Set(),triggers=[0,0];
 for(const source of sources){const candidate=mapping[source],target=outputs.includes(candidate)?candidate:source;
  if(target==='l2')triggers[0]=1;else if(target==='r2')triggers[1]=1;else if(buttons.includes(target))held.add(target);
 }
 return {buttons:[...held],triggers};
}
function analog(x,y,deadzone){
 const n=Math.hypot(x,y);if(n<=deadzone||n===0)return [0,0];
 const scale=(Math.min(n,1)-deadzone)/(1-deadzone)/n;return [x*scale,y*scale];
}
return {buttons,outputs,encode,mapButtons,analog};
});
