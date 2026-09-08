const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const themes=require('../share/chart-themes.js');
const custom={mode:'custom',base:'light',colors:{background:'#f8eedf',buy:'#136843',sell:'#ad2e5a'}};
assert(themes.valid(undefined));
assert(themes.valid(custom));
for(const bad of [null,[],{mode:'auto'},{mode:'dark',colors:{background:'url(x)'}},{mode:'dark',colors:{script:'#123456'}},{mode:'dark',base:'auto'}])assert(!themes.valid(bad));
const resolved=themes.resolve(custom,{buy:'#112233',sell:'#445566'});
assert.equal(resolved.background,'#f8eedf');assert.equal(resolved.buy,'#136843');
for(const mode of ['dark','light']){
  const colors=themes.resolve({mode});
  assert(themes.contrast(colors.background,colors.text)>=4.5);
  assert(themes.contrast(colors.background,colors.muted)>=4.5);
  for(const key of ['buy','sell'])assert(themes.contrast(colors[key],themes.ink(colors[key]))>=4.5);
}
const snapshot=themes.snapshot(resolved),preset={schema:1,name:'Warm paper',theme:snapshot};
assert(themes.presetValid(preset));
assert.deepEqual(themes.resolve(snapshot,{buy:'#ffffff',sell:'#000000'},{buy:'#000000'}),resolved,'saved colors survive later global palette edits');
assert.deepEqual(JSON.parse(JSON.stringify(preset)),preset);
assert(!themes.presetValid({...preset,name:' '}));

// A desktop theme event may update window styles, never stored chart settings,
// indicators, drawings, quotes, or subscription selection.
const ui=fs.readFileSync(require('node:path').join(__dirname,'../share/theme-ui.js'),'utf8');
const stored={appearance:{chrome:'omarchy'},charts:[{chartTheme:custom,drawings:[{color:'#abcd12'}],studies:[{id:'rsi',color:'#de3456'}]}]};
const before=JSON.stringify(stored),styles={},sent=[],body={classList:{toggle(){}},style:{setProperty:(key,value)=>styles[key]=value}};
const socket={readyState:1,send:value=>sent.push(JSON.parse(value))};
const window={addEventListener(){}};
const context={window,ChartThemes:themes,appearance:()=>stored.appearance,state:stored,document:{body,getElementById:()=>null},$(){return {setAttribute(){}}},liveSocket:socket};
vm.runInNewContext(ui,context);
assert.equal(sent.length,1);assert.equal(sent[0].omarchyTheme.watch,true);
window.ThemeUI.receive({available:true,name:'Test',colors:{background:'#ffffff',foreground:'#222222',accent:'#71512a'}});
assert.equal(styles['--chrome-bg'],'#ffffff');assert.equal(JSON.stringify(stored),before);
window.ThemeUI.sync();assert.equal(sent.length,1,'unchanged subscriptions are not repeated');
stored.appearance.chrome='alpharch';window.ThemeUI.sync();assert.equal(sent.at(-1).omarchyTheme.watch,false);
console.log('Chart themes: readable defaults, strict import validation, fixed saved colors and Omarchy/chart isolation passed.');
