const test=require('node:test');
const assert=require('node:assert/strict');
const input=require('../static/input.js');
test('compact 16-byte packet carries mapped buttons, sticks and triggers',()=>{
 const buffer=input.encode({buttons:['circle','up'],axes:[1,-1,.5,0],triggers:[1,0]},42);
 assert.equal(buffer.byteLength,16);
 const v=new DataView(buffer);
 assert.equal(v.getUint16(0,true),18);
 assert.equal(v.getInt16(2,true),32767);
 assert.equal(v.getInt16(4,true),-32767);
 assert.equal(v.getUint8(10),255);
 assert.equal(v.getUint32(12,true),42);
});
test('mapping combines multiple fingers without losing shared targets',()=>{
 const mapping={cross:'circle',square:'circle',l2:'r1',triangle:'r2',home:'disabled'};
 assert.deepEqual(input.mapButtons(['cross','square','l2','triangle','home'],mapping),{buttons:['circle','r1'],triggers:[0,1]});
 assert.deepEqual(input.mapButtons(['square'],mapping),{buttons:['circle'],triggers:[0,0]});
});
test('radial deadzone has continuous output and diagonal is bounded',()=>{
 assert.deepEqual(input.analog(.02,.02,.06),[0,0]);
 assert.deepEqual(input.analog(1,0,.06),[1,0]);
 const v=input.analog(1,1,.06); assert.ok(Math.abs(Math.hypot(...v)-1)<1e-9);
 assert.ok(input.analog(.07,0,.06)[0]<.02);
});
test('invalid persisted mappings cannot escape allowed outputs',()=>{
 assert.deepEqual(input.mapButtons(['cross'],{cross:'arbitrary'}),{buttons:['cross'],triggers:[0,0]});
});
