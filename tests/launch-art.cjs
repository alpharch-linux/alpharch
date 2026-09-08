const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
// Exercise asynchronous import races and disposal without a GPU or network.
// Only the module loader is replaced; the production controller runs intact.
const code=fs.readFileSync(require('node:path').join(__dirname,'../share/launch-art.js'),'utf8').replace("import('/launch-scene.js')",'loadScene()');
function element(){const listeners={},classes=new Set();return {open:false,dataset:{},attributes:{},listeners,disabled:false,textContent:'',classList:{contains:v=>classes.has(v),add:v=>classes.add(v),remove:v=>classes.delete(v)},setAttribute(k,v){this.attributes[k]=v},addEventListener(k,fn){(listeners[k]??=[]).push(fn)},emit(k){for(const fn of listeners[k]||[])fn({})}};}
function harness(saved){
  const dialog=element(),host=element(),toggle=element(),body=element(),document=element(),window=element(),reduced=element();
  reduced.matches=false;document.hidden=false;document.body=body;document.getElementById=id=>({starterDialog:dialog,launchArt:host,launchMotion:toggle}[id]);
  const observers=new Map(),imports=[];let created=0,disposed=0,stored=saved;
  const module={createLaunchScene(){created++;let dead=false;return {dispose(){assert(!dead,'a scene is disposed only once');dead=true;disposed++;}};}};
  const context={document,window,matchMedia:()=>reduced,localStorage:{getItem:()=>stored,setItem:(k,v)=>{stored=v}},MutationObserver:class{constructor(fn){this.fn=fn}observe(target){observers.set(target,this.fn)}},loadScene:()=>new Promise((resolve,reject)=>imports.push({resolve,reject}))};
  vm.runInNewContext(code,context);
  return {dialog,host,toggle,body,document,window,reduced,imports,module,open(value=true){dialog.open=value;observers.get(dialog)()},bodyChanged(){observers.get(body)()},counts:()=>({created,disposed}),stored:()=>stored};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  const h=harness();assert.equal(h.imports.length,0,'closed chooser loads no graphics');
  h.open();assert.equal(h.imports.length,1);h.open(false);h.imports[0].resolve(h.module);await settle();assert.deepEqual(h.counts(),{created:0,disposed:0},'late load cannot create a hidden scene');
  h.open();h.imports.at(-1).resolve(h.module);await settle();assert.deepEqual(h.counts(),{created:1,disposed:0});
  h.toggle.emit('click');assert.equal(h.stored(),'off');assert.deepEqual(h.counts(),{created:1,disposed:1});assert.equal(h.host.classList.contains('has-scene'),false);
  h.toggle.emit('click');h.imports.at(-1).resolve(h.module);await settle();h.document.hidden=true;h.document.emit('visibilitychange');assert.deepEqual(h.counts(),{created:2,disposed:2});
  h.document.hidden=false;h.document.emit('visibilitychange');h.imports.at(-1).resolve(h.module);await settle();h.reduced.matches=true;h.reduced.emit('change');assert.equal(h.toggle.disabled,true);assert.deepEqual(h.counts(),{created:3,disposed:3});
  h.reduced.matches=false;h.reduced.emit('change');h.imports.at(-1).resolve(h.module);await settle();h.window.emit('alpharch:desk-opened');assert.deepEqual(h.counts(),{created:4,disposed:4},'native launch stops art even when chooser stays open');
  const importsBefore=h.imports.length;h.document.emit('visibilitychange');assert.equal(h.imports.length,importsBefore,'a launched desk cannot restart background art');
  h.open(false);h.open();h.imports.at(-1).resolve(h.module);await settle();h.body.classList.add('no-motion');h.bodyChanged();assert.deepEqual(h.counts(),{created:5,disposed:5},'global interface motion off disposes art');
  h.body.classList.remove('no-motion');h.bodyChanged();h.imports.at(-1).reject(Error('offline module missing'));await settle();assert.equal(h.host.dataset.scene,'unavailable');assert.equal(h.host.classList.contains('has-scene'),false,'load failure preserves static fallback');
  const disabled=harness('off');disabled.open();assert.equal(disabled.imports.length,0,'saved off preference avoids importing the library');
  console.log('Opening art: lazy load, close/import race, preference persistence, hidden tab, reduced motion, native launch, global motion and failure fallback passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
