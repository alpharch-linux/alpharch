/* A small, lazy controller: closing the chooser, switching tabs, disabling
 * motion or launching a native desk releases the entire 3D scene. */
(() => {
  'use strict';
  const dialog=document.getElementById('starterDialog'),host=document.getElementById('launchArt');
  const toggle=document.getElementById('launchMotion'),reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const preference='alpharch.launch-motion.v1';
  let enabled=true,scene=null,generation=0,launched=false;
  try { enabled=localStorage.getItem(preference)!=='off'; } catch { /* Static storage environments still work. */ }
  function wanted(){return enabled&&!reduced.matches&&!document.hidden&&dialog.open&&!document.body.classList.contains('no-motion')&&!launched;}
  function stop(){generation++;scene?.dispose();scene=null;host.classList.remove('has-scene');}
  async function sync(){
    const globalOff=document.body.classList.contains('no-motion');
    toggle.setAttribute('aria-pressed',String(enabled&&!reduced.matches&&!globalOff));
    toggle.textContent=reduced.matches?'Motion reduced':enabled&&!globalOff?'Motion on':'Motion off';
    toggle.disabled=reduced.matches||globalOff;
    toggle.title=reduced.matches?'Reduced motion is enabled on this device.':globalOff?'Interface motion is off in Appearance.':'Animate the opening logo';
    stop(); if(!wanted())return;
    const token=generation;
    try {
      const module=await import('/launch-scene.js');
      if(token!==generation||!wanted())return;
      scene=module.createLaunchScene(host,()=>{stop();host.dataset.scene='unavailable';});
      host.classList.add('has-scene');host.dataset.scene='ready';
    } catch { stop();host.dataset.scene='unavailable'; }
  }
  toggle.addEventListener('click',()=>{enabled=!enabled;try{localStorage.setItem(preference,enabled?'on':'off');}catch{}sync();});
  document.addEventListener('visibilitychange',sync);
  reduced.addEventListener('change',sync);
  new MutationObserver(()=>{launched=false;sync();}).observe(dialog,{attributes:true,attributeFilter:['open']});
  new MutationObserver(sync).observe(document.body,{attributes:true,attributeFilter:['class']});
  window.addEventListener('alpharch:desk-opened',()=>{launched=true;stop();});
  window.addEventListener('pagehide',stop);
  sync();
})();
