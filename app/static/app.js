'use strict';
const $=id=>document.getElementById(id);
const ROLE={DOCENTE:['Dirección de simulación','DO','Control del hospital, escenarios, eventos, indicadores y exportación.'],HIS:['Admisiones / HIS','HI','Admite ingresos, asigna camas, traslada y registra altas de pacientes ficticios.'],CLINICA:['Clínica y enfermería','CL','Solicita estudios y suministros, reconoce alertas y confirma recepciones.'],LIS:['Laboratorio / LIS','LI','Recibe solicitudes de laboratorio y publica resultados sintéticos.'],BIOMED:['Ingeniería biomédica','BM','Verifica el equipamiento, declara averías y restaura su disponibilidad.'],FARMACIA:['Farmacia hospitalaria','FA','Dispensa insumos ficticios, coordinando con el equipo clínico.'],IMAGENES:['Diagnóstico por imagen','IM','Gestiona estudios ficticios y comunica informes a clínica.']};
const GUIDE={
DOCENTE:[['Dirige un hospital virtual','Crea un aula, copia su código y distribúyelo entre los estudiantes con sus roles.','Los alumnos nunca necesitan la contraseña docente.'],['Configura el hospital híbrido','Selecciona los roles humanos (2, 3, 4 o 6 estudiantes) y guarda los agentes virtuales. Después elige el modo de incidentes y dificultad.','En modo automático aparecen incidentes con varias tareas y dependencias entre equipos.'],['Observa decisiones y tiempos','Vigila incidentes abiertos, tareas, alarmas, camas y disponibilidad. Intervén con eventos manuales cuando lo necesites.','Los incidentes concluyen solo cuando se cumplen las acciones registradas.'],['Evalúa con trazabilidad','Exporta la auditoría CSV y analiza tiempos de reconocimiento, coordinación y resolución del ejercicio.','No confundir reconocer una alarma con resolver un estado clínico.']],
HIS:[['Tu estación es Admisiones','Controlas la asignación de camas y el censo de pacientes sintéticos.','Revisa la sección Pacientes y camas antes de actuar.'],['Responde a ingresos imprevistos','Cuando aparece un ingreso, selecciona el paciente de la sala de espera y asígnale una cama libre.','La ocupación hospitalaria se actualizará automáticamente.'],['Coordina con Clínica','Después de tu admisión, Clínica confirma que recibió al paciente. Ambos pasos completan la tarea.','Tu acción queda registrada con nombre y fecha.'],['Gestiona el flujo del hospital','Puedes transferir pacientes a otra cama o registrar un alta ficticia.','Una cama ocupada nunca puede asignarse a otro paciente.']],
CLINICA:[['Tu estación es Clínica','Solicitas laboratorio, imagenología y suministros ficticios. También reconoces alertas clínicas.','No introduzcas información clínica real.'],['Reconoce alarmas','Cuando ocurre una emergencia, identifica la unidad y reconoce la alarma correspondiente.','Reconocer significa que recibiste el aviso; no que el paciente esté recuperado.'],['Coordina entregas y resultados','Después del HIS confirma el ingreso; después de Farmacia confirma el suministro; después de Imagen, revisa el informe.','Las tareas del incidente cambian automáticamente cuando completas las acciones.'],['Genera órdenes simuladas','Puedes crear análisis de laboratorio, estudios de imagen y órdenes de insumos para pacientes sintéticos.','El sistema conserva la trazabilidad entre solicitud y respuesta.']],
LIS:[['Tu estación es el LIS','El laboratorio recibe solicitudes realizadas desde Clínica.','Revisa las órdenes solicitadas y los incidentes prioritarios.'],['Recibe las muestras','Una orden nueva debe pasar primero al estado «Muestra recibida».','Este paso puede ocurrir también en el escenario de laboratorio crítico preconfigurado.'],['Publica resultados','Elige resultado normal o crítico de acuerdo al ejercicio.','Los valores son didácticos, no rangos clínicos universales.'],['Comunica valores críticos','El sistema crea una alarma al publicar un resultado crítico. Clínica debe reconocerla.','El incidente se cierra cuando ambas tareas quedan completadas.']],
BIOMED:[['Tu estación es Biomédica','Administras estado y verificación de equipos ficticios distribuidos por las áreas.','La disponibilidad se calcula con el inventario simulado.'],['Responde a fallas','Ante una avería identifica el dispositivo y registra su recuperación a operativo.','El incidente técnico también puede requerir reconocimiento desde Clínica.'],['Verifica antes de concluir','El escenario de desaturación requiere una comprobación técnica del monitor.','Una verificación didáctica no reemplaza pruebas de seguridad o metrología real.'],['Revisa los indicadores','Analiza cuántos dispositivos permanecen operativos y qué incidentes afectan servicios.','Los estados de equipo se reflejan en la vista de inventario.']],
FARMACIA:[['Tu estación es Farmacia','Gestionas suministros ficticios, no medicamentos de pacientes reales.','Todas las órdenes usan productos genéricos de simulación.'],['Identifica solicitudes','Busca las órdenes emitidas por Clínica y los incidentes asociados.','Prioriza las solicitudes vinculadas a incidentes abiertos.'],['Confirma dispensación','Selecciona una orden pendiente y ejecuta «Dispensar».','La orden pasa a estado dispensada y el equipo clínico la ve en tiempo real.'],['Cierra el circuito','Clínica registra la recepción del suministro después de tu dispensación.','Ambos pasos completan el flujo de coordinación.']],
IMAGENES:[['Tu estación es Imagenología','Procesas solicitudes ficticias de radiografía, ecografía y tomografía.','Este entorno no procesa imágenes DICOM reales.'],['Localiza los estudios','Selecciona una solicitud pendiente en tu cola.','Un incidente puede generar automáticamente una orden prioritaria.'],['Informa el estudio','Publica un «Informe A» o «Informe B», ambos ficticios y no diagnósticos.','Clínica recibe la notificación de informe pendiente de revisión.'],['Cierra la comunicación','La confirmación de lectura por Clínica completa el flujo del incidente.','Toda la secuencia queda auditada.']]};
const STATUS={waiting:'En espera',admitted:'Admitido',received:'Recibido',requested:'Solicitado',resulted:'Informado',dispensed:'Dispensado',reported:'Informado',reviewed:'Revisado',pending:'Pendiente',completed:'Completada',active:'Abierto',resolved:'Resuelto',acknowledged:'Reconocida',operativo:'Operativo',en_falla:'En falla'};
const M={session:null,code:null,data:null,rooms:[],socket:null,refreshInterval:null,pingInterval:null,busy:false,ward:'URG',view:'overview',step:0,staffDirty:false,deviceEditId:null,deviceEditorLoaded:null,seen:new Set(),audio:false,audioContext:null};
try{const s=JSON.parse(sessionStorage.getItem('hdlsession')||'null');if(s)M.session=s}catch{}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n}
function clear(x){x.replaceChildren()}
function toast(msg,isError=false){const n=$('toast');n.textContent=msg;n.className='toast'+(isError?' error':'');clearTimeout(toast._timer);toast._timer=setTimeout(()=>n.classList.add('hidden'),9000)}
async function api(path,method='GET',data){const headers={'Accept':'application/json'};if(M.session?.token)headers['Authorization']='Bearer '+M.session.token;if(data!==undefined)headers['Content-Type']='application/json';let r;try{r=await fetch(path,{method,headers,body:data===undefined?undefined:JSON.stringify(data)})}catch{throw Error('Servidor no disponible. Comprueba la conexión.')}const res=await r.json().catch(()=>({}));if(!r.ok)throw Error(typeof res.detail==='string'?res.detail:'Error del servidor '+r.status);return res}
function signin(type){$('student-form').classList.toggle('hidden',type!=='student');$('teacher-form').classList.toggle('hidden',type!=='teacher');$('tab-student').classList.toggle('active',type==='student');$('tab-teacher').classList.toggle('active',type==='teacher');$('form-error').textContent=''}
async function join(ev){ev.preventDefault();$('form-error').textContent='';const f=new FormData(ev.currentTarget);try{const s=await api('/api/join','POST',{code:String(f.get('code')).trim().toUpperCase(),name:String(f.get('name')).trim(),role:f.get('role')});await session(s)}catch(e){$('form-error').textContent=e.message}}
async function teacher(ev){ev.preventDefault();$('form-error').textContent='';const f=new FormData(ev.currentTarget);try{const s=await api('/api/admin/login','POST',{password:f.get('password')});$('teacher-form').reset();await session(s)}catch(e){$('form-error').textContent=e.message}}
async function session(s){M.session=s;sessionStorage.setItem('hdlsession',JSON.stringify(s));M.code=s.room?.code||null;await openSession(true)}
async function openSession(first=false){$('welcome').classList.add('hidden');$('workspace').classList.remove('hidden');const role=M.session.role,info=ROLE[role];$('identity-role').textContent=info[0];$('identity-user').textContent=M.session.name;$('role-avatar').textContent=info[1];$('station-title').textContent=info[0];$('station-tag').textContent=role;$('station-description').textContent=info[2];$('teacher-panel').classList.toggle('hidden',role!=='DOCENTE');$('welcome-line').textContent=info[2];if(role==='DOCENTE'){await loadRooms();if(!M.code&&M.rooms.length)M.code=M.rooms[0].code}await openRoom();if(first){const key='hdltutorial-v02-'+role;if(!sessionStorage.getItem(key))showTutorial()}}
async function loadRooms(){M.rooms=await api('/api/rooms');const s=$('room-select');clear(s);M.rooms.forEach(r=>{const o=el('option','',`${r.title} · ${r.code}`);o.value=r.code;s.append(o)});if(M.code&&M.rooms.some(r=>r.code===M.code))s.value=M.code}
async function createRoom(ev){ev.preventDefault();const f=new FormData(ev.currentTarget);try{const r=await api('/api/rooms','POST',{title:String(f.get('title')).trim()});M.code=r.code;await loadRooms();await openRoom();$('new-room').reset();toast('Aula creada. Código de acceso: '+r.code)}catch(e){toast(e.message,true)}}
async function openRoom(){if(M.socket){M.socket.close();M.socket=null}if(M.refreshInterval){clearInterval(M.refreshInterval);M.refreshInterval=null}if(M.pingInterval){clearInterval(M.pingInterval);M.pingInterval=null}M.staffDirty=false;M.deviceEditId=null;M.deviceEditorLoaded=null;if(!M.code){$('no-rooms').classList.remove('hidden');$('dashboard').classList.add('hidden');$('room-title').textContent='Crea tu primera aula';return}$('no-rooms').classList.add('hidden');$('dashboard').classList.remove('hidden');await refresh();connect();M.refreshInterval=setInterval(refresh,12000);M.pingInterval=setInterval(()=>{if(M.socket?.readyState===WebSocket.OPEN)M.socket.send('ping')},15000)}
function connect(){const ws=new WebSocket((location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'/ws/'+encodeURIComponent(M.code));M.socket=ws;ws.onopen=()=>ws.send(JSON.stringify({type:'auth',token:M.session.token}));ws.onmessage=ev=>{try{if(JSON.parse(ev.data).type==='refresh')refresh()}catch{}};ws.onclose=()=>{if(M.socket===ws&&M.session){$('connection-label').textContent='RECONECTANDO';setTimeout(()=>{if(M.socket===ws&&M.session)connect()},3500)}};ws.onerror=()=>ws.close()}
async function refresh(){if(!M.code||M.busy)return;M.busy=true;try{const d=await api('/api/state/'+encodeURIComponent(M.code));notify(d);M.data=d;render();$('connection-label').textContent='EN LÍNEA'}catch(e){$('connection-label').textContent='SIN CONEXIÓN';if(e.message.includes('Sesión vencida'))logout();else toast(e.message,true)}finally{M.busy=false}}
function notify(d){const active=d.incidents.filter(i=>i.state==='active').map(i=>i.id);if(M.data){const newItems=d.incidents.filter(i=>i.state==='active'&&!M.seen.has(i.id));if(newItems.length){toast('Nuevo incidente: '+newItems[0].title);if(M.audio)beep()}}M.seen=new Set([...M.seen,...active])}
function logout(){M.socket?.close();M.socket=null;if(M.refreshInterval)clearInterval(M.refreshInterval);M.refreshInterval=null;if(M.pingInterval)clearInterval(M.pingInterval);M.pingInterval=null;sessionStorage.removeItem('hdlsession');M.session=null;M.data=null;M.code=null;$('workspace').classList.add('hidden');$('welcome').classList.remove('hidden');$('connection-label').textContent='ENTORNO DOCENTE'}
function showTutorial(){M.step=0;$('tutorial').classList.remove('hidden');renderTutorial()}
function closeTutorial(){sessionStorage.setItem('hdltutorial-v02-'+M.session.role,'1');$('tutorial').classList.add('hidden')}
function renderTutorial(){const slides=GUIDE[M.session.role],s=slides[M.step];$('tutorial-icon').textContent=String(M.step+1).padStart(2,'0');$('tutorial-title').textContent=s[0];$('tutorial-text').textContent=s[1];$('tutorial-example').textContent=s[2];$('tutorial-progress').textContent=(M.step+1)+' / '+slides.length;$('tutorial-back').disabled=M.step===0;$('tutorial-next').textContent=M.step===slides.length-1?'Comenzar simulación ✓':'Siguiente →';clear($('step-track'));slides.forEach((_,i)=>$('step-track').append(el('span',i<=M.step?'active':'')))}
function changeView(view){M.view=view;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===view));for(const [k,id] of Object.entries({overview:'dashboard',incidents:'incidents-view',patients:'patients-view',devices:'devices-view',audit:'audit-view'}))$(id).classList.toggle('hidden',k!==view);if(M.data)render()}
function fmt(iso){if(!iso)return '—';return new Date(iso).toLocaleString('es-BO',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}
function badge(text,cls=''){return el('span','chip '+cls,text)}
function messageEmpty(root,msg){root.append(el('div','empty-list',msg))}
function render(){if(!M.data)return;const d=M.data,m=d.metrics;$('room-title').textContent=d.room.title;$('room-code').textContent=d.room.code;$('room-subtitle').textContent=M.session.role==='DOCENTE'?'CENTRO DE CONTROL DOCENTE':'HOSPITAL VIRTUAL / '+ROLE[M.session.role][0].toUpperCase();$('metric-occupancy').textContent=m.occupancy_pct+' %';$('metric-occupation-detail').textContent=m.beds_occupied+' de '+m.beds_total+' camas';$('metric-devices').textContent=m.devices_operational+' / '+m.devices_total;$('metric-incidents').textContent=m.incidents_active;$('metric-done').textContent=m.incidents_resolved+' cerrados';$('metric-tasks').textContent=m.tasks_pending;$('metric-ack').textContent=m.mean_ack_seconds===null?'—':m.mean_ack_seconds+' s';$('metric-labs').textContent=m.lab_pending;$('nav-count').textContent=m.incidents_active;
 renderTeacher();renderMap();renderIncidents();renderStation();renderTasks();renderPatients();renderDevices();renderAudit();renderPracticeEntries();renderPracticeFields()}
function renderTeacher(){if(M.session.role!=='DOCENTE')return;const s=M.data.settings;$('room-select').value=M.code;$('simulation-mode').value=s.mode;$('simulation-difficulty').value=s.difficulty;$('simulation-interval').value=String(s.interval_seconds);if(!$('simulation-interval').value)$('simulation-interval').value='120';$('engine-state').textContent=s.mode==='auto'?'Automático · próximo evento: '+fmt(s.next_event_at):s.mode==='paused'?'Motor pausado · sin eventos automáticos':'Motor manual · eventos por docente';renderStaffing();renderPresence()}

const HUMAN_ROLES=['HIS','CLINICA','LIS','BIOMED','FARMACIA','IMAGENES'];
const STAFF_PRESETS={2:['CLINICA','LIS'],3:['CLINICA','BIOMED','LIS'],4:['HIS','CLINICA','LIS','BIOMED'],6:HUMAN_ROLES};
function staffingSelected(){return [...document.querySelectorAll('.staff-human:checked')].map(x=>x.value)}
function previewStaffing(){const n=staffingSelected().length;$('staffing-summary').textContent=n+' humanos · '+(6-n)+' virtuales'+(M.staffDirty?' · sin guardar':'')}
function renderStaffing(){
 if(M.staffDirty)return;
 const rows=M.data.staffing||[];
 const root=$('staffing-roles');clear(root);
 for(const role of HUMAN_ROLES){
  const data=rows.find(x=>x.role===role);
  const label=el('label','staff-role');const checkbox=el('input');checkbox.type='checkbox';checkbox.className='staff-human';checkbox.value=role;checkbox.checked=!data||data.mode==='human';
  label.append(checkbox,el('span','',ROLE[role][0]));label.append(el('small','',checkbox.checked?'Estudiante':'Agente virtual'));
  checkbox.onchange=()=>{M.staffDirty=true;label.lastChild.textContent=checkbox.checked?'Estudiante':'Agente virtual';previewStaffing()};
  root.append(label);
 }
 $('staffing-pace').value=String(rows[0]?.pace_seconds||15);previewStaffing();
}
function presetStaffing(count){const enabled=new Set(STAFF_PRESETS[count]||HUMAN_ROLES);document.querySelectorAll('.staff-human').forEach(c=>{c.checked=enabled.has(c.value);c.parentElement.lastChild.textContent=c.checked?'Estudiante':'Agente virtual'});M.staffDirty=true;previewStaffing()}
async function saveStaffing(){
 const human_roles=staffingSelected();
 if(!human_roles.length){toast('Selecciona al menos un área humana.',true);return}
 if(!M.code){toast('Primero crea un aula.',true);return}
 try{
  await api('/api/action/'+encodeURIComponent(M.code),'POST',{kind:'simulation_staffing',value:JSON.stringify({human_roles,pace_seconds:Number($('staffing-pace').value)})});
  M.staffDirty=false;await refresh();toast('Personal asignado: '+human_roles.length+' áreas humanas y '+(6-human_roles.length)+' virtuales.');
 }catch(e){toast(e.message,true)}
}

function renderPresence(){
 const root=$('presence-roles');clear(root);
 const staff=M.data.staffing||[],people=M.data.student_sessions||[];
 const on=people.filter(p=>p.online);
 $('presence-summary').textContent=on.length+' estudiante(s) activo(s)';
 if(document.activeElement!==$('coverage-auto'))$('coverage-auto').checked=Boolean(M.data.settings.auto_cover_absences);
 for(const role of HUMAN_ROLES){
  const slot=staff.find(x=>x.role===role)||{mode:'human'};
  const found=people.filter(p=>p.role===role);
  const active=found.filter(p=>p.online),offline=found.filter(p=>!p.online);
  const row=el('div','presence-role');const body=el('div','presence-details');
  body.append(el('strong','',ROLE[role][0]));
  const status=slot.mode==='auto'?(slot.auto_reason==='absence'?'SUPLENCIA POR AUSENCIA':'BOT PERMANENTE'):(active.length?'CONECTADO':'SIN ESTUDIANTES ACTIVOS');
  const small=el('small','',status);small.classList.add(slot.mode==='auto'?'present-bot':active.length?'present-online':'present-offline');body.append(small);
  const names=found.length?active.map(p=>p.name+' · en línea').concat(offline.slice(0,2).map(p=>p.name+' · sin actividad')).join(' / '):'Sin estudiantes registrados';
  body.append(el('span','',names));row.append(body);
  const btn=el('button','btn '+(slot.mode==='auto'?'light':'primary'),slot.mode==='auto'?'Devolver a estudiante':'Automatizar');
  btn.type='button';btn.onclick=async()=>{
   if(M.staffDirty){toast('Guarda o descarta primero la distribución general.',true);return}
   btn.disabled=true;
   await run('staffing_role',null,JSON.stringify({role,mode:slot.mode==='auto'?'human':'auto'}));
  };
  row.append(btn);root.append(row);
 }
}
async function saveCoverage(){
 const enabled=$('coverage-auto').checked;
 await run('coverage_config',null,enabled?'on':'off');
}

function renderMap(){const d=M.data;clear($('ward-map'));Object.entries(d.units).forEach(([unit,name])=>{const beds=d.beds.filter(b=>b.unit===unit);const devices=d.devices.filter(b=>b.unit===unit);const alarm=d.alarms.filter(a=>a.unit===unit&&a.state==='active').length;const w=el('button','ward'+(unit===M.ward?' active':''));w.type='button';w.append(el('span','ward-top',unit));w.append(el('strong','',name));w.append(el('small',alarm?'● '+alarm+' alerta(s)':beds.length?`${beds.filter(b=>b.patient_id).length}/${beds.length} camas`:devices.length+' dispositivos'));if(alarm)w.lastChild.classList.add('alerting');w.addEventListener('click',()=>{M.ward=unit;renderMap()});$('ward-map').append(w)});const unit=M.ward,box=$('ward-detail');clear(box);const head=el('div','ward-detail-head');head.append(el('span','',d.units[unit]),badge(unit));box.append(head);const list=el('div','ward-detail-list');const beds=d.beds.filter(b=>b.unit===unit);const dv=d.devices.filter(b=>b.unit===unit);const alarms=d.alarms.filter(a=>a.unit===unit&&a.state==='active');for(const b of beds){const row=el('div','unit-entry');row.append(el('span','',b.label),el('b',b.patient_id?'':'good',b.patient_name||'Libre'));list.append(row)}for(const x of dv){const row=el('div','unit-entry');row.append(el('span','',x.name),el('b',x.state==='operativo'?'good':'bad',STATUS[x.state]));list.append(row)}for(const a of alarms){const row=el('div','unit-entry');row.append(el('span','','Alarma #'+a.id),el('b','bad','ACTIVA'));list.append(row)}if(!list.children.length)messageEmpty(list,'Sin activos registrados en esta unidad.');box.append(list)}
function incidentCard(i,compact){const t=M.data.tasks.filter(x=>x.incident_id===i.id);const box=el('div','incident-card '+(i.priority==='alta'?'high':'medium')+(i.state==='active'&&i.due_at<new Date().toISOString()?' overdue':''));const head=el('div','incident-row');head.append(el('strong','',i.title),badge(i.state==='resolved'?'Completado':i.priority==='alta'?'PRIORIDAD ALTA':'PRIORIDAD MEDIA',i.state==='resolved'?'good':i.priority==='alta'?'high':'medium'));box.append(head);box.append(el('p','',i.description));const meta=el('div','incident-meta');meta.append(el('span','',M.data.units[i.unit]||i.unit),el('span','','· '+fmt(i.created_at)),el('span','','· '+t.filter(x=>x.state==='completed').length+'/'+t.length+' tareas'));box.append(meta);if(!compact){const list=el('div','task-list');t.forEach(x=>{const row=el('div','task-row'+(x.state==='completed'?' done':''));row.append(el('span','dot'));const body=el('div');body.append(el('b','',x.role+(M.data.staffing?.some(s=>s.role===x.role&&s.mode==='auto')?' [AUTO]':'')+' · '+x.title),el('small','',x.description+' · '+(x.state==='completed'?'Completada':'Pendiente')));row.append(body);list.append(row)});box.append(list)}return box}
function renderIncidents(){const d=M.data;clear($('incident-summary'));clear($('incident-list'));let active=d.incidents.filter(i=>i.state==='active');for(const i of active.slice(0,3))$('incident-summary').append(incidentCard(i,true));if(!active.length)messageEmpty($('incident-summary'),'Sin incidentes abiertos. El docente puede generar uno o iniciar el motor automático.');for(const i of d.incidents)$('incident-list').append(incidentCard(i,false));if(!d.incidents.length)messageEmpty($('incident-list'),'Todavía no hay incidentes.');const root=$('alarm-list');clear(root);for(const a of d.alarms){const r=el('div','list-line');const left=el('div');left.append(el('b','',`#${a.id} · ${a.kind==='clinical'?'Clínica':'Técnica'} · ${a.unit}`),el('span','',a.message));r.append(left,badge(STATUS[a.state]||a.state,a.state==='active'?'high':'good'));root.append(r)}if(!d.alarms.length)messageEmpty(root,'No hay alarmas registradas.')}
function makeSelect(id,items,placeholder){const s=el('select');s.id=id;if(!items.length){const opt=el('option','',placeholder||'No hay opciones');opt.value='';s.append(opt);s.disabled=true}else for(const [value,text] of items){const o=el('option','',text);o.value=String(value);s.append(o)}return s}
function actionBox(title,description,fields,kind,options={}){const b=el('div','action-box');b.append(el('h3','',title),el('p','',description));const row=el('div','action-field'+(fields.length===1?' two':''));fields.forEach(f=>{const label=el('label','',f.label);label.append(makeSelect(f.id,f.options,f.empty));row.append(label)});const button=el('button','btn primary',options.button||'Registrar');button.type='button';button.disabled=fields.some(f=>!f.options.length);button.onclick=async()=>{let target=null,val=options.fixedValue??null;if(options.fixedTarget!==undefined)target=options.fixedTarget;if(options.target)target=Number($(options.target).value);if(options.value)val=$(options.value).value;await run(kind,target,val)};row.append(button);b.append(row);return b}
const opt=(arr,fn)=>arr.map(fn);const short=(n)=>String(n).slice(0,55);
function renderStation(){const d=M.data,role=M.session.role,box=$('station-actions');clear(box);if(role!=='DOCENTE'&&d.staffing?.some(s=>s.role===role&&s.mode==='auto')){messageEmpty(box,'Esta área pasó a personal automático. Consulta al docente para reasignarla.');return;}const p=opt(d.patients,x=>[x.id,`${x.name} · ${x.bed_label}`]);const beds=opt(d.beds.filter(x=>!x.patient_id),x=>[x.id,x.label]);const devices=opt(d.devices,x=>[x.id,x.name+' · '+x.unit]);const freeArr=opt(d.arrivals.filter(x=>x.state==='waiting'),x=>[x.id,x.name]);const add=(...a)=>box.append(actionBox(...a));
 if(role==='HIS'||role==='DOCENTE'){
  add('Ingreso desde sala de espera','Asigna una cama libre al paciente nuevo.',[{id:'arrival-select',label:'Ingreso pendiente',options:freeArr},{id:'arrival-bed',label:'Cama disponible',options:beds}],'admit_arrival',{target:'arrival-select',value:'arrival-bed',button:'Admitir'});
  add('Admisión programada','Agrega un paciente ficticio a una cama libre.',[{id:'bed-select',label:'Cama disponible',options:beds}],'admit',{target:'bed-select',button:'Registrar'});
  add('Traslado de cama','Cambia la ubicación de un paciente.',[{id:'transfer-patient',label:'Paciente',options:p},{id:'transfer-bed',label:'Nueva cama libre',options:beds}],'transfer',{target:'transfer-patient',value:'transfer-bed',button:'Trasladar'});
  add('Alta del paciente','Libera la cama y completa el egreso sintético.',[{id:'discharge-patient',label:'Paciente',options:p}],'discharge',{target:'discharge-patient',button:'Registrar alta'});
 }
 if(role==='CLINICA'||role==='DOCENTE'){
  add('Recibir ingreso','Confirma clínicamente una admisión realizada por HIS.',[{id:'receive-arrival',label:'Ingreso admitido',options:opt(d.arrivals.filter(x=>x.state==='admitted'),x=>[x.id,x.name])}],'arrival_receive',{target:'receive-arrival',button:'Confirmar'});
  add('Orden de laboratorio','Envía una solicitud al LIS.',[{id:'lab-patient',label:'Paciente',options:p},{id:'lab-test',label:'Prueba',options:['Potasio','Glucosa','Hemoglobina'].map(x=>[x,x])}],'lab_order',{target:'lab-patient',value:'lab-test',button:'Solicitar'});
  add('Pedido a Farmacia','Solicita un suministro genérico de simulación.',[{id:'med-patient',label:'Paciente',options:p},{id:'med-product',label:'Insumo ficticio',options:['Insumo A','Insumo B','Insumo C'].map(x=>[x,x])}],'med_order',{target:'med-patient',value:'med-product',button:'Solicitar'});
  add('Solicitar estudio de imagen','Emite una orden al área de imagenología.',[{id:'img-patient',label:'Paciente',options:p},{id:'img-study',label:'Estudio ficticio',options:['Radiografía simulada','Ecografía simulada','Tomografía simulada'].map(x=>[x,x])}],'imaging_order',{target:'img-patient',value:'img-study',button:'Solicitar'});
  add('Confirmar suministro','El suministro debe estar dispensado primero.',[{id:'med-receive',label:'Orden lista',options:opt(d.med_orders.filter(x=>x.state==='dispensed'),x=>[x.id,`#${x.id} · ${x.patient_name} · ${x.product}`])}],'med_receive',{target:'med-receive',button:'Recibido'});
  add('Revisar informe de imagen','Confirma que el informe ficticio fue recibido.',[{id:'img-review',label:'Informe disponible',options:opt(d.imaging_orders.filter(x=>x.state==='reported'),x=>[x.id,`#${x.id} · ${x.patient_name}`])}],'imaging_review',{target:'img-review',button:'Revisado'});
 }
 if(role==='LIS'||role==='DOCENTE'){
  add('Recibir muestra','Selecciona una orden nueva de Clínica.',[{id:'lab-receive',label:'Orden solicitada',options:opt(d.orders.filter(x=>x.state==='requested'),x=>[x.id,`#${x.id} · ${x.patient_name} · ${x.test}`])}],'sample_received',{target:'lab-receive',button:'Recibir muestra'});
  add('Publicar resultado','El resultado crítico genera alerta clínica.',[{id:'lab-result',label:'Muestra recibida',options:opt(d.orders.filter(x=>x.state==='received'),x=>[x.id,`#${x.id} · ${x.patient_name} · ${x.test}`])},{id:'result-type',label:'Resultado didáctico',options:[['normal','Normal'],['critical','Crítico']]}],'lab_result',{target:'lab-result',value:'result-type',button:'Publicar'});
 }
 if(role==='BIOMED'||role==='DOCENTE'){
  add('Verificar dispositivo','Registra una comprobación didáctica funcional.',[{id:'device-check',label:'Dispositivo',options:devices}],'device_check',{target:'device-check',button:'Verificar'});
  add('Avería o recuperación','Modifica el estado técnico del dispositivo.',[{id:'device-target',label:'Equipo',options:devices},{id:'device-state',label:'Nuevo estado',options:[['en_falla','En falla'],['operativo','Operativo']]}],'device_status',{target:'device-target',value:'device-state',button:'Actualizar'});
 }
 if(role==='FARMACIA'||role==='DOCENTE'){
  add('Dispensar suministro','Procesa una orden clínica pendiente.',[{id:'med-dispense',label:'Solicitud',options:opt(d.med_orders.filter(x=>x.state==='requested'),x=>[x.id,`#${x.id} · ${x.patient_name} · ${x.product}`])}],'med_dispense',{target:'med-dispense',button:'Dispensar'});
 }
 if(role==='IMAGENES'||role==='DOCENTE'){
  add('Publicar informe','Los informes son etiquetas didácticas no diagnósticas.',[{id:'img-result',label:'Estudio pendiente',options:opt(d.imaging_orders.filter(x=>x.state==='requested'),x=>[x.id,`#${x.id} · ${x.patient_name} · ${short(x.study)}`])},{id:'img-report',label:'Informe simulado',options:[['Informe A','Informe A'],['Informe B','Informe B']]}],'imaging_result',{target:'img-result',value:'img-report',button:'Publicar'});
 }
 if(role==='CLINICA'||role==='BIOMED'||role==='DOCENTE'){
  const active=d.alarms.filter(a=>a.state==='active'&&(role!=='BIOMED'||a.kind==='technical'));
  add('Reconocer alerta','Este paso confirma recepción; no significa resolución clínica.',[{id:'ack-alarm',label:'Alarma activa',options:opt(active,a=>[a.id,`#${a.id} · ${a.kind==='clinical'?'Clínica':'Técnica'} · ${a.unit}`])}],'alarm_ack',{target:'ack-alarm',button:'Reconocer'});
 }
}
function renderTasks(){const root=$('my-tasks');clear(root);const r=M.session.role;const tasks=M.data.tasks.filter(t=>t.state==='pending'&&(r==='DOCENTE'||t.role===r));$('my-task-count').textContent=tasks.length+' pendientes';for(const t of tasks){const line=el('div','task-row');line.append(el('span','dot'));const b=el('div');b.append(el('b','',t.title),el('small','',t.description),el('small','',t.incident_title));line.append(b);root.append(line)}if(!tasks.length)messageEmpty(root,'No tienes tareas de incidentes pendientes. Puedes practicar con tu estación.')}
function renderPatients(){clear($('patient-list'));clear($('arrival-list'));for(const p of M.data.patients){const row=el('div','list-line');const info=el('div');info.append(el('b','',p.name),el('span','',p.age+' años · '+p.bed_label+' · '+M.data.units[p.unit]));row.append(info,badge('Hospitalizado','good'));$('patient-list').append(row)}for(const a of M.data.arrivals){const row=el('div','list-line');const info=el('div');info.append(el('b','',a.name),el('span','',fmt(a.created_at)));row.append(info,badge(STATUS[a.state]||a.state,a.state==='waiting'?'high':'good'));$('arrival-list').append(row)}if(!M.data.arrivals.length)messageEmpty($('arrival-list'),'No hay nuevos ingresos en espera.')}
function renderDevices(){
 const root=$('device-list');clear(root);
 for(const x of M.data.devices){
  const row=el('div','list-line device-item');const info=el('div');
  info.append(el('b','',x.name),el('span','',(x.manufacturer||'Fabricante ficticio')+' · '+(x.model||'Modelo no registrado')),
   el('span','',M.data.units[x.unit]+' · '+x.type+' · '+(x.asset_tag||'Sin inventario')));
  const right=el('div','device-actions');right.append(badge(STATUS[x.state]||x.state,x.state==='en_falla'?'high':'good'));
  const btn=el('button','btn light','Ver ficha');btn.type='button';btn.onclick=()=>{M.deviceEditId=x.id;M.deviceEditorLoaded=null;renderDeviceEditor(true);$('device-editor').scrollIntoView({behavior:'smooth',block:'nearest'})};
  right.append(btn);row.append(info,right);root.append(row)
 }
 if(!M.data.devices.length)messageEmpty(root,'Aún no hay equipos en este hospital.');
 renderDeviceEditor();
}
function deviceInput(name,label,value,formType='text',options=null){
 const wrapper=el('label','',label);
 let control;
 if(name==='notes'||name==='specifications'){
  control=el('textarea');control.rows=3;
 }else if(options){
  control=el('select');for(const [key,text] of options){const opt=el('option','',text);opt.value=key;control.append(opt)}
 }else{control=el('input');control.type=formType}
 control.name=name;control.value=value||'';if(name==='name'||name==='type')control.required=true;
 control.maxLength=({name:100,type:45,manufacturer:80,model:80,serial_number:60,asset_tag:60,risk_class:40,specifications:350,notes:500})[name]||100;
 wrapper.append(control);return wrapper;
}
function renderDeviceEditor(force=false){
 const root=$('device-editor'),canEdit=['BIOMED','DOCENTE'].includes(M.session.role);
 if(!M.data.devices.length&&!canEdit){clear(root);messageEmpty(root,'Sin equipos.');return}
 if(M.deviceEditId===null&&M.data.devices.length)M.deviceEditId=M.data.devices[0].id;
 const dev=M.data.devices.find(d=>d.id===M.deviceEditId),editingNew=M.deviceEditId==='new';
 const key=String(M.deviceEditId);
 if(!force&&M.deviceEditorLoaded===key&&root.children.length)return; // Preservar lo que se escribe entre refrescos.
 M.deviceEditorLoaded=key;clear(root);
 const bar=el('div','device-head');bar.append(el('h3','',editingNew?'Nuevo equipo ficticio':dev?.name||'Equipo no seleccionado'));
 if(canEdit){const create=el('button','btn light','+ Registrar equipo');create.type='button';create.onclick=()=>{M.deviceEditId='new';M.deviceEditorLoaded=null;renderDeviceEditor(true)};bar.append(create)}
 root.append(bar);
 if(!canEdit){
  if(!dev)return;
  const data=[['Fabricante ficticio',dev.manufacturer],['Modelo',dev.model],['Serie',dev.serial_number],['Activo',dev.asset_tag],['Riesgo',dev.risk_class],['Último mantenimiento',dev.last_maintenance],['Próximo mantenimiento',dev.next_maintenance],['Especificaciones de simulación',dev.specifications],['Notas',dev.notes]];
  const detail=el('dl','device-readonly');data.forEach(([label,value])=>{detail.append(el('dt','',label),el('dd','',value||'—'))});root.append(detail);return;
 }
 const form=el('form','device-form');form.id='device-form';
 const grid=el('div','device-form-grid');
 const fields=[['name','Nombre del equipo'],['type','Tipo'],['unit','Servicio'],['manufacturer','Fabricante ficticio'],['model','Modelo ficticio'],['serial_number','Número de serie'],['asset_tag','Código patrimonial'],['risk_class','Clasificación de riesgo didáctica'],['last_maintenance','Mantenimiento anterior'],['next_maintenance','Próximo mantenimiento'],['specifications','Características técnicas simuladas'],['notes','Observaciones']];
 for(const [field,label] of fields){
  const vals=field==='unit'?Object.entries(M.data.units):null;
  const widget=deviceInput(field,label,dev?.[field]||'',field.endsWith('maintenance')?'date':'text',vals);
  if(['notes','specifications'].includes(field))widget.classList.add('wide');grid.append(widget);
 }
 form.append(grid);
 const buttons=el('div','device-form-actions');
 const save=el('button','btn primary',editingNew?'Crear activo':'Guardar ficha técnica');save.type='submit';buttons.append(save);form.append(buttons);
 form.onsubmit=async ev=>{
  ev.preventDefault();const data=Object.fromEntries(new FormData(form));if(!data.name.trim()||!data.type.trim()){toast('Nombre y tipo son obligatorios.',true);return}
  const kind=editingNew?'device_create':'device_update';
  save.disabled=true;
  try{await api('/api/action/'+encodeURIComponent(M.code),'POST',{kind,target_id:editingNew?null:dev.id,value:JSON.stringify(data)});
   M.deviceEditId=null;M.deviceEditorLoaded=null;toast(editingNew?'Equipo ficticio creado.':'Ficha técnica actualizada.');await refresh();
  }catch(e){toast(e.message,true)}finally{save.disabled=false}
 };
 root.append(form);
}
function renderPracticeFields(){
 const label=$('practice-device-label'),s=$('practice-device');
 label.classList.toggle('hidden',!['BIOMED','DOCENTE'].includes(M.session.role));
 const selected=s.value,items=M.data.devices;
 if([...s.options].length!==items.length+1||items.some((d,i)=>s.options[i+1]?.value!==String(d.id))){
  clear(s);const none=el('option','','Sin equipo');none.value='';s.append(none);
  items.forEach(d=>{const option=el('option','',d.name+' · '+(d.asset_tag||d.unit));option.value=String(d.id);s.append(option)});
  s.value=selected;
 }
}
async function submitPractice(ev){
 ev.preventDefault();const form=ev.currentTarget,fd=new FormData(form);
 const raw=String(fd.get('measurement')||'').trim();const num=raw?Number(raw):null;
 if(raw&&!Number.isFinite(num)){toast('Medición numérica inválida.',true);return}
 const id=String(fd.get('device')||'');const payload={subject:String(fd.get('subject')||'').trim(),details:String(fd.get('details')||'').trim(),measurement_value:num,measurement_unit:String(fd.get('unit')||'').trim(),device_id:id?Number(id):null};
 const submit=form.querySelector('[type="submit"]');submit.disabled=true;
 try{await api('/api/action/'+encodeURIComponent(M.code),'POST',{kind:'practice_entry',value:JSON.stringify(payload)});form.reset();toast('Observación registrada en la bitácora.');await refresh()}
 catch(e){toast(e.message,true)}finally{submit.disabled=false}
}
function renderPracticeEntries(){
 const root=$('practice-list');clear(root);
 for(const r of M.data.practice_entries||[]){
  const row=el('div','audit-item');row.append(el('small','',fmt(r.created_at)+' · '+r.actor+' · '+r.role),el('b','',r.subject),el('p','',r.details));
  if(r.measurement_value!==null)row.append(el('small','',r.measurement_value+' '+(r.measurement_unit||'')+(r.device_id?' · Equipo #'+r.device_id:'')));
  root.append(row)
 }
 if(!root.children.length)messageEmpty(root,'Sin registros libres todavía.');
}
function drawSyntheticWave(){
 const canvas=$('ecg');if(!canvas)return;const ctx=canvas.getContext('2d');if(!ctx)return;const w=canvas.width,h=canvas.height;const critical=Boolean(M.data?.incidents.some(x=>x.state==='active'&&x.scenario==='desaturacion'));$('monitor-hr').textContent=critical?'105':'78';$('monitor-oxygen').textContent=critical?'84':'98';$('monitor-oxygen').classList.toggle('critical',critical);$('monitor-state').textContent=critical?'ESCENARIO ACTIVO':'DATOS SINTÉTICOS';$('monitor-state').classList.toggle('danger-text',critical);ctx.clearRect(0,0,w,h);ctx.strokeStyle='#254650';ctx.lineWidth=.6;for(let x=0;x<w;x+=26){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}for(let y=0;y<h;y+=24){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}ctx.strokeStyle=critical?'#f47e84':'#57e2b4';ctx.lineWidth=2;ctx.beginPath();let phase=Date.now()/30;for(let x=0;x<w;x++){let v=((x+phase)%109)/109;const gauss=(mu,sigma,amp)=>amp*Math.exp(-Math.pow((v-mu)/sigma,2));let y=h*.56-gauss(.16,.05,6)+gauss(.38,.02,9)-gauss(.42,.011,33)+gauss(.45,.025,14)-gauss(.67,.08,7);if(x===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();
}
function renderAudit(){const root=$('audit-list');clear(root);for(const e of M.data.events){const row=el('div','audit-item');row.append(el('small','',fmt(e.created_at)+' · '+e.actor+' · '+e.role),el('b','',e.type.replaceAll('_',' ').toUpperCase()),el('p','',e.message));root.append(row)}if(!M.data.events.length)messageEmpty(root,'Sin actividad registrada.')}
async function run(kind,target_id=null,value=null){try{await api('/api/action/'+encodeURIComponent(M.code),'POST',{kind,target_id,value});toast('Acción registrada correctamente.');await refresh()}catch(e){toast(e.message,true)}}
async function config(){const settings={mode:$('simulation-mode').value,difficulty:$('simulation-difficulty').value,interval_seconds:Number($('simulation-interval').value)};await run('simulation_config',null,JSON.stringify(settings))}
async function scenario(ev){const button=ev.target.closest('[data-scenario]');if(!button)return;await run('scenario_spawn',null,button.dataset.scenario)}
async function reset(){if(!confirm('¿Reiniciar todos los datos y los incidentes de ESTA aula? No se podrán recuperar sin respaldo.'))return;if(!confirm('Confirma una segunda vez: se eliminará la auditoría del aula seleccionada.'))return;await run('reset_room',null,'CONFIRMAR')}
function downloadCSV(){fetch('/api/export/'+encodeURIComponent(M.code),{headers:{Authorization:'Bearer '+M.session.token}}).then(r=>{if(!r.ok)throw Error('No se pudo exportar');return r.blob()}).then(blob=>{const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='hospital-'+M.code+'-auditoria.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500)}).catch(e=>toast(e.message,true))}
function enableAudio(){if(M.audio){M.audio=false;$('enable-audio').textContent='Activar sonido';return}try{const C=window.AudioContext||window.webkitAudioContext;M.audioContext=new C();M.audioContext.resume();M.audio=true;$('enable-audio').textContent='Silenciar';toast('Avisos breves habilitados.')}catch{toast('El navegador no admite audio.',true)}}
function beep(){if(!M.audioContext)return;const ctx=M.audioContext;try{const o=ctx.createOscillator(),g=ctx.createGain();o.type='sine';o.frequency.value=600;g.gain.value=.0001;o.connect(g);g.connect(ctx.destination);const t=ctx.currentTime;g.gain.exponentialRampToValueAtTime(.07,t+.02);g.gain.exponentialRampToValueAtTime(.0001,t+.16);o.start(t);o.stop(t+.18)}catch{}}
function init(){
 setInterval(drawSyntheticWave,120);
 $('tab-student').onclick=()=>signin('student');$('tab-teacher').onclick=()=>signin('teacher');$('student-form').onsubmit=join;$('teacher-form').onsubmit=teacher;$('new-room').onsubmit=createRoom;$('logout').onclick=logout;$('logout-top').onclick=logout;$('tutorial-open-top').onclick=showTutorial;$('tutorial-open').onclick=showTutorial;$('tutorial-close').onclick=closeTutorial;$('tutorial-back').onclick=()=>{M.step=Math.max(0,M.step-1);renderTutorial()};$('tutorial-next').onclick=()=>{if(M.step>=GUIDE[M.session.role].length-1)closeTutorial();else{M.step++;renderTutorial()}};
 $('room-select').onchange=async ev=>{M.code=ev.target.value;await openRoom()};$('save-simulation').onclick=config;$('save-staffing').onclick=saveStaffing;$('coverage-save').onclick=saveCoverage;$('practice-form').onsubmit=submitPractice;$('staffing-pace').onchange=()=>{M.staffDirty=true;previewStaffing()};document.querySelectorAll('[data-staff-preset]').forEach(b=>b.onclick=()=>presetStaffing(Number(b.dataset.staffPreset)));$('scenario-actions').onclick=scenario;$('reset-room').onclick=reset;$('export-csv').onclick=downloadCSV;$('enable-audio').onclick=enableAudio;$('refresh-data').onclick=refresh;$('copy-code').onclick=async()=>{try{await navigator.clipboard.writeText(M.code);toast('Código copiado.')}catch{toast('Código: '+M.code)}};
 document.querySelectorAll('[data-view]').forEach(n=>n.onclick=()=>changeView(n.dataset.view));document.querySelectorAll('[data-goto]').forEach(n=>n.onclick=()=>changeView(n.dataset.goto));
 if(M.session)openSession().catch(e=>{toast(e.message,true);logout()});
}
init();
