// Build with tools/build-launch-art.sh. This scene is decorative; it never
// consumes market data or delays the desk. Three.js is bundled for offline use.
import {Scene,PerspectiveCamera,WebGLRenderer,Group,Shape,Path,ExtrudeGeometry,PMREMGenerator,
  Mesh,MeshPhysicalMaterial,HemisphereLight,DirectionalLight,PointLight,TubeGeometry,CatmullRomCurve3,Vector3,
  ACESFilmicToneMapping,SRGBColorSpace} from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

export function createLaunchScene(host,onLost){
  const renderer=new WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));
  renderer.outputColorSpace=SRGBColorSpace;renderer.toneMapping=ACESFilmicToneMapping;
  renderer.toneMappingExposure=1;renderer.setClearColor(0x000000,0);
  const canvas=renderer.domElement;canvas.setAttribute('aria-hidden','true');
  const scene=new Scene(),camera=new PerspectiveCamera(33,1,.1,60);camera.position.set(0,0,11.5);
  const mark=new Group();scene.add(mark);
  const studio=new RoomEnvironment(),pmrem=new PMREMGenerator(renderer),environment=pmrem.fromScene(studio,.04);
  scene.environment=environment.texture;scene.environmentIntensity=1.1;studio.dispose();pmrem.dispose();
  const cream=new MeshPhysicalMaterial({color:0xece6d3,metalness:.9,roughness:.22,clearcoat:.6,clearcoatRoughness:.2});
  const amber=new MeshPhysicalMaterial({color:0xc77c48,metalness:.85,roughness:.25,clearcoat:.7});
  const side=new MeshPhysicalMaterial({color:0x64808d,metalness:.8,roughness:.28});
  const geometries=[];
  // The brand's waveform, circular alpha and hooked stem, in the original
  // logo proportions. Polygons form a solid cut-metal edge instead of a tube.
  function polygon(points){const s=new Shape();points.forEach(([x,y],i)=>i?s.lineTo((x-50)/12,(50-y)/12):s.moveTo((x-50)/12,(50-y)/12));s.closePath();return s;}
  function add(shape,material){const geometry=new ExtrudeGeometry(shape,{depth:.5,bevelEnabled:true,bevelSegments:3,steps:1,bevelSize:.045,bevelThickness:.045,curveSegments:64});geometries.push(geometry);const mesh=new Mesh(geometry,[material,side]);mesh.position.z=-.25+mark.children.length*.06;mark.add(mesh);}
  add(polygon([[1,51],[7,51],[17,30],[25,52],[30,35],[39,52],[31,57],[32,54],[26,79],[17,53],[13,61],[1,61]]),cream);
  const ring=new Shape();ring.absarc(.5,-1/3,27/12,0,Math.PI*2,false);
  const hole=new Path();hole.absarc(.5,-1/3,17/12,0,Math.PI*2,true);ring.holes.push(hole);add(ring,cream);
  const hook=new Shape();hook.moveTo(23/12,16/12);hook.lineTo(33/12,16/12);hook.lineTo(33/12,-6/12);
  hook.quadraticCurveTo(33/12,-19/12,46/12,-19/12);hook.lineTo(46/12,-29/12);
  hook.quadraticCurveTo(23/12,-29/12,23/12,-6/12);hook.closePath();add(hook,amber);
  // Copper filaments echo the After Hours wallpaper. They are a physical
  // backdrop to the mark, not a decorative market chart or invented data.
  for(let i=0;i<20;i++){
    const offset=(i-9.5)*.125;
    const curve=new CatmullRomCurve3([new Vector3(-9,-2+offset,-1),new Vector3(-3,-1.7+offset,-.9),new Vector3(2,-.65+offset,-1),new Vector3(6,2+offset,-1.4),new Vector3(9,3+offset,-1.8)]);
    const geometry=new TubeGeometry(curve,48,.009,5,false);geometries.push(geometry);scene.add(new Mesh(geometry,i%4===0?side:amber));
  }
  scene.add(new HemisphereLight(0xd7e8ff,0x221325,.8));
  const key=new DirectionalLight(0xffefcd,2);key.position.set(-3,5,6);scene.add(key);
  const cyan=new PointLight(0x66ffd5,75,20);cyan.position.set(-5,-1,3);scene.add(cyan);
  const pink=new PointLight(0xff609e,75,20);pink.position.set(5,1,2);scene.add(pink);
  const rim=new DirectionalLight(0xa7bcff,3);rim.position.set(0,-4,-2);scene.add(rim);
  let frame=0,disposed=false,last=0,start=0,pointerX=0,pointerY=0;
  function size(){const box=host.getBoundingClientRect();if(!box.width||!box.height)return;renderer.setSize(box.width,box.height,false);camera.aspect=box.width/box.height;camera.position.z=Math.max(11.5,17/camera.aspect);camera.updateProjectionMatrix();}
  function move(event){const box=host.getBoundingClientRect();pointerX=(event.clientX-box.left)/box.width-.5;pointerY=(event.clientY-box.top)/box.height-.5;}
  function leave(){pointerX=0;pointerY=0;}
  function tick(now){
    if(disposed)return;frame=requestAnimationFrame(tick);if(now-last<1000/30)return;last=now;if(!start)start=now;
    const t=(now-start)/1000;
    mark.rotation.y+=(-.3+pointerX*.25+Math.sin(t*.35)*.035-mark.rotation.y)*.07;
    mark.rotation.x+=(.09+pointerY*.15-mark.rotation.x)*.07;
    mark.rotation.z=-.055;mark.position.y=Math.sin(t*.6)*.035;
    renderer.render(scene,camera);
  }
  const resize=new ResizeObserver(size);
  function lost(event){event.preventDefault();onLost();}
  function dispose(){
    if(disposed)return;disposed=true;cancelAnimationFrame(frame);resize.disconnect();
    host.removeEventListener('pointermove',move);host.removeEventListener('pointerleave',leave);canvas.removeEventListener('webglcontextlost',lost);
    for(const g of geometries)g.dispose();for(const material of [cream,amber,side])material.dispose();
    environment.dispose();renderer.dispose();renderer.forceContextLoss();canvas.remove();
  }
  try{
    host.append(canvas);resize.observe(host);host.addEventListener('pointermove',move);host.addEventListener('pointerleave',leave);canvas.addEventListener('webglcontextlost',lost);
    size();frame=requestAnimationFrame(tick);
  }catch(error){dispose();throw error;}
  return {dispose};
}
