'use strict';
const $=id=>document.getElementById(id);
const saved=(()=>{try{return JSON.parse(sessionStorage.getItem('hospitalLabSession')||'null')}catch{return null}})();
const model={session:saved, roomCode:saved?.room?.code||null, data:null, selectedUnit:'URG', socket:null, refreshTimer:null, rooms:[], loading:false, audio:false, audioContext:null, seenAlarmIds:null};
const ROLE_NAMES={DOCENTE:'Docente',HIS:'Admisiones · HIS',CLINICA:'Enfermería · Clínica',LIS:'Laboratorio · LIS',BIOMED:'Ingeniería biomédica'};
const stateText={requested:'Solicitada',received:'Muestra recibida',resulted:'Informada',operative:'Operativo',operativo:'Operativo',en_falla:'En falla',active:'Activa',acknowledged:'Reconocida',resolved:'Resuelta'};
function element(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n}
function clear(n){n.replaceChildren()}
function toast(msg,error=false){const box=$('toast');box.textContent=msg;box.className='toast'+(error?' error':'');setTimeout(()=>{if(box.textContent===msg)box.classList.add('hidden')},4500)}
function errorMessage(e){return e?.message||'No se pudo completar la operación.'}
async function api(path, method='GET',body=null){
  const opts={method,headers:{'Accept':'application/json'}};
  if(model.session?.token)opts.headers.Authorization='Bearer '+model.session.token;
  if(body){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}
  const response=await fetch(path,opts);
  let data;try{data=await response.json()}catch{data={}}
  if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:`Error HTTP ${response.status}`);
  return data;
}
function sessionSet(s){model.session=s;sessionStorage.setItem('hospitalLabSession',JSON.stringify(s))}
function logout(){const old=model.socket;model.socket=null;if(old)old.close();if(model.refreshTimer)clearInterval(model.refreshTimer);sessionStorage.removeItem('hospitalLabSession');model.session=null;model.roomCode=null;model.data=null;$('app').classList.add('hidden');$('welcome').classList.remove('hidden');$('connection-status').textContent='SIN CONEXIÓN'}
function switchTab(which){const st=which==='student';$('student-form').classList.toggle('hidden',!st);$('teacher-form').classList.toggle('hidden',st);$('student-tab').classList.toggle('active',st);$('teacher-tab').classList.toggle('active',!st);$('login-error').textContent=''}
async function enterStudent(ev){ev.preventDefault();$('login-error').textContent='';const fd=new FormData(ev.currentTarget);try{const s=await api('/api/join','POST',{code:String(fd.get('code')).trim().toUpperCase(),name:String(fd.get('name')).trim(),role:fd.get('role')});sessionSet(s);await openSession()}catch(e){$('login-error').textContent=errorMessage(e)}}
async function enterTeacher(ev){ev.preventDefault();$('login-error').textContent='';const fd=new FormData(ev.currentTarget);try{const s=await api('/api/admin/login','POST',{password:fd.get('password')});sessionSet(s);$('teacher-form').reset();await openSession()}catch(e){$('login-error').textContent=errorMessage(e)}}
async function openSession(){
  $('welcome').classList.add('hidden');$('app').classList.remove('hidden');
  $('role-label').textContent=ROLE_NAMES[model.session.role];$('user-label').textContent=model.session.name;
  $('teacher-management').classList.toggle('hidden',model.session.role!=='DOCENTE');
  if(model.session.role==='DOCENTE'){
    await loadRooms();
    if(model.session.room?.code)model.roomCode=model.session.room.code;
    else if(!model.roomCode&&model.rooms.length)model.roomCode=model.rooms[0].code;
  }else model.roomCode=model.session.room.code;
  await openRoom();
}
async function loadRooms(){model.rooms=await api('/api/rooms');const sel=$('rooms-select');clear(sel);for(const r of model.rooms){const opt=element('option','',`${r.title} (${r.code})`);opt.value=r.code;sel.append(opt)}if(model.roomCode)sel.value=model.roomCode}
async function createRoom(ev){ev.preventDefault();const fd=new FormData(ev.currentTarget);try{const room=await api('/api/rooms','POST',{title:String(fd.get('title')).trim()});model.roomCode=room.code;await loadRooms();await openRoom();ev.currentTarget.reset();toast('Aula creada. Comparte el código '+room.code)}catch(e){toast(errorMessage(e),true)}}
async function openRoom(){
  if(model.socket){model.socket.close();model.socket=null}
  if(model.refreshTimer)clearInterval(model.refreshTimer);
  $('waiting-room').classList.toggle('hidden',!!model.roomCode);$('simulation').classList.toggle('hidden',!model.roomCode);
  $('room-title').textContent='Hospital digital';$('room-code').textContent=model.roomCode||'—';
  if(!model.roomCode)return;
  if(model.session.role==='DOCENTE')$('rooms-select').value=model.roomCode;
  model.seenAlarmIds=null;
  await refresh();
  connectSocket();
  model.refreshTimer=setInterval(()=>{if(!document.hidden)refresh().catch(()=>{})},12000);
}
async function refresh(){if(!model.roomCode||model.loading)return;model.loading=true;try{model.data=await api('/api/state/'+encodeURIComponent(model.roomCode));checkAudio(model.data.alarms);render();$('connection-status').textContent='CONECTADO';$('room-title').textContent=model.data.room.title}catch(e){$('connection-status').textContent='ERROR';toast(errorMessage(e),true);if(errorMessage(e).includes('Sesión vencida'))logout()}finally{model.loading=false}}
function connectSocket(){if(!model.roomCode)return;const scheme=location.protocol==='https:'?'wss:':'ws:';const url=scheme+'//'+location.host+'/ws/'+encodeURIComponent(model.roomCode);const ws=new WebSocket(url);model.socket=ws;ws.onopen=()=>ws.send(JSON.stringify({type:'auth',token:model.session.token}));ws.onmessage=ev=>{try{const payload=JSON.parse(ev.data);if(payload.type==='refresh')refresh()}catch{}};ws.onclose=()=>{$('connection-status').textContent='RECONECTANDO';if(model.session&&model.socket===ws)setTimeout(()=>{if(model.session&&model.socket===ws)connectSocket()},3500)};ws.onerror=()=>{ws.close()}}
function enableAudio(){
 try{
  const AudioCtx=window.AudioContext||window.webkitAudioContext;
  if(!AudioCtx){toast('Este navegador no permite alarmas sonoras.',true);return}
  if(!model.audioContext)model.audioContext=new AudioCtx();
  model.audioContext.resume();model.audio=true;$('enable-audio').textContent='Sonido activado';
  toast('Las alarmas simuladas nuevas tendrán un aviso breve.');
 }catch(e){toast('No fue posible activar audio.',true)}
}
function shortBeep(){
 if(!model.audio||!model.audioContext)return;
 try{
   const ctx=model.audioContext,osc=ctx.createOscillator(),gain=ctx.createGain();
   osc.type='sine';osc.frequency.value=730;gain.gain.value=0.0001;
   osc.connect(gain);gain.connect(ctx.destination);
   const start=ctx.currentTime;gain.gain.exponentialRampToValueAtTime(0.085,start+0.02);
   gain.gain.exponentialRampToValueAtTime(0.0001,start+0.32);
   osc.start(start);osc.stop(start+0.33);
 }catch(e){}
}
function checkAudio(alarms){
 const ids=new Set(alarms.filter(a=>a.state==='active').map(a=>a.id));
 if(model.seenAlarmIds===null){model.seenAlarmIds=ids;return}
 if([...ids].some(id=>!model.seenAlarmIds.has(id)))shortBeep();
 model.seenAlarmIds=ids;
}
function displayNumber(v){return typeof v==='number'?v:'—'}
function render(){const d=model.data,m=d.metrics;let ocup=`${m.beds_occupied}/${m.beds_total}`;$('metric-occupancy').textContent=m.occupancy_pct+' %';$('metric-beds').textContent=ocup+' camas';$('metric-devices').textContent=m.devices_operational+'/'+m.devices_total;$('metric-alarms').textContent=m.alarms_active;$('metric-lab').textContent=m.lab_pending;$('metric-ack').textContent=m.mean_ack_seconds===null?'—':m.mean_ack_seconds+' s';$('room-code').textContent=d.room.code;
 for(const unit of Object.keys(d.units)){const beds=d.beds.filter(x=>x.unit===unit);const n=beds.filter(x=>x.patient_id).length;const label=beds.length?`${n}/${beds.length} camas`:(unit==='LAB'?'LIS':unit==='BIO'?'ING.':'QX');for(const el of document.querySelectorAll(`[data-map="${unit}"]`))el.textContent=label}
 for(const el of document.querySelectorAll('.map-unit'))el.classList.toggle('selected',el.dataset.unit===model.selectedUnit);
 renderUnit();renderActions();renderAlarms();renderEvents();drawSyntheticECG();}
function renderUnit(){const d=model.data,unit=model.selectedUnit;$('unit-name').textContent=d.units[unit];const box=$('unit-contents');clear(box);const beds=d.beds.filter(x=>x.unit===unit), devices=d.devices.filter(x=>x.unit===unit),alarms=d.alarms.filter(x=>x.unit===unit&&x.state==='active');
 if(!beds.length&&!devices.length)box.append(element('div','empty','No hay camas ni equipos asignados a esta unidad.'));
 for(const b of beds){const row=element('div','unit-row');row.append(element('span','',b.label));row.append(element('b',b.patient_id?'good':'',b.patient_name||'Disponible'));box.append(row)}
 for(const dv of devices){const row=element('div','unit-row');row.append(element('span','',dv.name));row.append(element('b',dv.state==='operativo'?'good':'bad',stateText[dv.state]||dv.state));box.append(row)}
 for(const a of alarms){const row=element('div','unit-row');row.append(element('span','',`Alarma #${a.id}`));row.append(element('b','bad',a.priority.toUpperCase()));box.append(row)}
}
function actionPanel(title,description,inner){const box=element('div','action-box');box.append(element('h3','',title));if(description)box.append(element('p','',description));const content=element('div','action-fields');for(const el of inner)content.append(el);box.append(content);return box}
function chooser(options,id,placeholder){const select=element('select');select.id=id;if(!options.length){const opt=element('option','','No hay opciones');opt.value='';select.append(opt);select.disabled=true}else for(const [v,t] of options){const opt=element('option','',t);opt.value=v;select.append(opt)}return select}
function btn(label,kind,extra){const b=element('button','primary',label);b.type='button';b.dataset.kind=kind;if(extra)b.dataset.value=extra;return b}
function insert(root,panel){root.append(panel)}
function renderActions(){const box=$('action-forms');clear(box);const role=model.session.role,d=model.data,is=what=>role==='DOCENTE'||role===what;
 $('role-caption').textContent=role==='DOCENTE'?'Acceso de demostración a todas las estaciones':ROLE_NAMES[role];
 if(is('HIS')){
   const free=d.beds.filter(b=>!b.patient_id).map(b=>[b.id,`${b.label} · libre`]);
   insert(box,actionPanel('HIS · Nueva admisión','Registra un paciente completamente ficticio en una cama disponible.',[chooser(free,'bed-select'),btn('Admitir paciente sintético','admit')]));
 }
 if(is('CLINICA')){
   const patients=d.patients.map(p=>[p.id,`${p.name} · ${p.bed_label}`]);
   const test=chooser([['Potasio','Potasio (K+)'],['Glucosa','Glucosa'],['Hemoglobina','Hemoglobina']],'test-select');
   insert(box,actionPanel('Área clínica · Orden de laboratorio','Genera una solicitud que aparecerá en el LIS.',[chooser(patients,'patient-select'),test,btn('Enviar solicitud al LIS','lab_order')]));
 }
 if(is('LIS')){
   const pending=d.orders.filter(o=>o.state==='requested').map(o=>[o.id,`#${o.id} · ${o.patient_name} · ${o.test}`]);
   insert(box,actionPanel('LIS · Recepción de muestra','Primero registra la llegada de la muestra.',[chooser(pending,'sample-select'),btn('Recibir muestra','sample_received')]));
   const received=d.orders.filter(o=>o.state==='received').map(o=>[o.id,`#${o.id} · ${o.patient_name} · ${o.test}`]);
   insert(box,actionPanel('LIS · Resultado analítico','Valores predefinidos. Un resultado crítico activará una alarma clínica.',[chooser(received,'result-select'),chooser([['normal','Normal (simulado)'],['critical','Crítico (simulado)']],'result-kind'),btn('Publicar resultado','lab_result')]));
 }
 if(is('BIOMED')){
   insert(box,actionPanel('Ingeniería biomédica · Equipos','Cambia el estado de un dispositivo y observa la alarma técnica.',[chooser(d.devices.map(q=>[q.id,q.name+' · '+stateText[q.state]]),'device-select'),chooser([['en_falla','Reportar falla'],['operativo','Restituir a operativo']],'device-status'),btn('Registrar estado del equipo','device_status')]));
 }
 if(is('CLINICA')||is('BIOMED')){
   const alarms=d.alarms.filter(a=>a.state==='active' && (role==='DOCENTE'||(role==='BIOMED'?a.kind==='technical':true))).map(a=>[a.id,`#${a.id} · ${a.kind==='clinical'?'Clínica':'Técnica'} · ${a.unit}`]);
   insert(box,actionPanel('Reconocer alarmas','Reconocer no equivale a solucionar el problema.',[chooser(alarms,'ack-select'),btn('Reconocer alarma','alarm_ack')]));
 }
 if(role==='DOCENTE'){
   insert(box,actionPanel('Simular evento clínico','Activa una alarma de SpO₂ ficticia para ilustrar la coordinación entre roles.',[chooser([['UCI','UCI'],['URG','Urgencias'],['HOSP','Hospitalización']],'teacher-unit'),btn('Generar escenario','trigger_alarm')]));
   const reset=btn('Reiniciar datos de esta aula','reset_room');reset.className='outline danger-action';
   insert(box,actionPanel('Restaurar simulación','Borra eventos y resultados del aula actual. No elimina la sala ni a los estudiantes.',[reset]));
 }
}
function renderAlarms(){const box=$('alarm-list');clear(box);const alarms=model.data.alarms;if(!alarms.length){box.append(element('p','empty','No hay alarmas registradas.'));return}for(const a of alarms.slice(0,25)){const r=element('div','record');const head=element('div','record-header');head.append(element('strong','',`${a.kind==='clinical'?'CLÍNICA':'TÉCNICA'} · ${a.unit} · #${a.id}`),element('span','status '+a.state,stateText[a.state]||a.state));r.append(head,element('p','',a.message));r.append(element('small','',a.acknowledged_by?`Reconoció: ${a.acknowledged_by}`:'Prioridad '+a.priority));box.append(r)}}
function renderEvents(){const box=$('event-list');clear(box);const events=model.data.events;if(!events.length){box.append(element('p','empty','Todavía no hay eventos.'));return}for(const e of events.slice(0,25)){const r=element('div','record');const head=element('div','record-header');head.append(element('strong','',e.type.replaceAll('_',' ').toUpperCase()),element('small','',e.created_at.replace('T',' ').slice(0,19)+' UTC'));r.append(head,element('p','',e.message));r.append(element('small','',e.actor+' · '+e.role));if(e.payload&&Object.keys(e.payload).length){const details=element('details');details.append(element('summary','','Ver mensaje didáctico'));const pre=element('pre','',JSON.stringify(e.payload,null,2));details.append(pre);r.append(details)}box.append(r)}}
async function perform(kind){let target_id=null,value=null;const read=id=>$(id)?.value;
 if(kind==='admit')target_id=Number(read('bed-select'));
 if(kind==='lab_order'){target_id=Number(read('patient-select'));value=read('test-select')}
 if(kind==='sample_received')target_id=Number(read('sample-select'));
 if(kind==='lab_result'){target_id=Number(read('result-select'));value=read('result-kind')}
 if(kind==='device_status'){target_id=Number(read('device-select'));value=read('device-status')}
 if(kind==='alarm_ack')target_id=Number(read('ack-select'));
 if(kind==='trigger_alarm')value=read('teacher-unit');
 if(kind==='reset_room'){if(!confirm('¿Reiniciar todos los pacientes, alarmas y eventos de esta aula?'))return;value='CONFIRMAR'}
 if(target_id!==null&&(!Number.isInteger(target_id)||target_id<=0)){toast('No hay un registro disponible para la acción.',true);return}
 try{await api('/api/action/'+encodeURIComponent(model.roomCode),'POST',{kind,target_id,value});toast('Acción registrada y compartida con el aula.');await refresh()}catch(e){toast(errorMessage(e),true)}
}
async function exportCSV(){try{const res=await fetch('/api/export/'+encodeURIComponent(model.roomCode),{headers:{Authorization:'Bearer '+model.session.token}});if(!res.ok)throw Error('No se pudo exportar');const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='hospital-'+model.roomCode+'-auditoria.csv';a.click();URL.revokeObjectURL(url)}catch(e){toast(errorMessage(e),true)}}
function drawSyntheticECG(){
 const canvas=$('ecg-canvas');if(!canvas||!model.data)return;
 const ctx=canvas.getContext('2d');if(!ctx)return;
 const w=canvas.width,h=canvas.height;
 ctx.fillStyle='#142c34';ctx.fillRect(0,0,w,h);
 ctx.strokeStyle='#21434a';ctx.lineWidth=1;
 for(let x=0;x<w;x+=26){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}
 for(let y=0;y<h;y+=22){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
 const phase=Date.now()/55;
 ctx.beginPath();ctx.strokeStyle='#5beba2';ctx.lineWidth=2;
 for(let x=0;x<w;x++){
  const v=((x+phase)%105)/105;
  const gauss=(mu,width,amp)=>amp*Math.exp(-Math.pow((v-mu)/width,2));
  const y=h*0.55-(gauss(0.18,.035,5)-gauss(0.41,.018,9)+gauss(0.44,.009,37)-gauss(0.47,.018,13)+gauss(0.70,.09,8));
  if(x===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
 }
 ctx.stroke();
 const isCritical=model.data.alarms.some(a=>a.kind==='clinical'&&a.state==='active'&&a.unit===model.selectedUnit);
 $('monitor-unit').textContent=model.data.units[model.selectedUnit].toUpperCase();
 $('monitor-spo2').textContent=isCritical?'84':'98';
 $('monitor-hr').textContent=isCritical?'112':'78';
 canvas.closest('.monitor-card').classList.toggle('critical',isCritical);
}

function init(){
 setInterval(drawSyntheticECG,180);
 $('student-tab').addEventListener('click',()=>switchTab('student'));$('teacher-tab').addEventListener('click',()=>switchTab('teacher'));
 $('student-form').addEventListener('submit',enterStudent);$('teacher-form').addEventListener('submit',enterTeacher);$('logout').addEventListener('click',logout);
 $('create-room-form').addEventListener('submit',createRoom);
 $('rooms-select').addEventListener('change',async ev=>{model.roomCode=ev.target.value;await openRoom()});
 $('export-events').addEventListener('click',exportCSV);$('enable-audio').addEventListener('click',enableAudio);
 $('copy-code').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(model.roomCode);toast('Código copiado.')}catch{toast('Código: '+model.roomCode)}});
 document.querySelectorAll('.map-unit').forEach(el=>{el.addEventListener('click',()=>{model.selectedUnit=el.dataset.unit;if(model.data)render()});el.setAttribute('tabindex','0');el.setAttribute('role','button');el.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();el.click()}})});
 $('action-forms').addEventListener('click',ev=>{const b=ev.target.closest('button[data-kind]');if(b)perform(b.dataset.kind)});
 if(model.session)openSession().catch(e=>{toast(errorMessage(e),true);logout()});
}
init();
