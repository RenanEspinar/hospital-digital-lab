"""Motor de simulación exclusivamente docente. Datos 100 % sintéticos.
Esquema retrocompatible con hospital-digital-lab v0.1 (añade tablas sin destruir datos).
"""
from __future__ import annotations
import json, os, secrets, random, sqlite3, hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH=Path(os.getenv('DATABASE_PATH','/data/hospital.db'))
UNITS={'URG':'Urgencias','UCI':'Cuidados intensivos','HOSP':'Hospitalización','LAB':'Laboratorio','QX':'Quirófanos','BIO':'Ingeniería biomédica','FAR':'Farmacia','IMG':'Diagnóstico por imagen'}
ROLES={'HIS','CLINICA','LIS','BIOMED','FARMACIA','IMAGENES'}
BED_LAYOUT=[('URG',f'URG-{i:02d}') for i in range(1,5)]+[('UCI',f'UCI-{i:02d}') for i in range(1,4)]+[('HOSP',f'HOSP-{i:02d}') for i in range(1,6)]
NAMES=[f'Paciente {i:03d}' for i in range(1,201)]
TESTS={'Potasio':('mmol/L',4.2,6.3),'Glucosa':('mg/dL',105,48),'Hemoglobina':('g/dL',13.7,6.5)}
MEDICATIONS={'Insumo A','Insumo B','Insumo C'}
IMAGING={'Radiografía simulada','Ecografía simulada','Tomografía simulada'}
SCENARIOS={
 'desaturacion':('Desaturación simulada','alta','UCI','CLINICA,BIOMED'),
 'falla_equipo':('Falla de equipamiento','alta','UCI','BIOMED,CLINICA'),
 'llegada_masiva':('Ingreso imprevisto','media','URG','HIS,CLINICA'),
 'resultado_critico':('Solicitud urgente de laboratorio','alta','LAB','LIS,CLINICA'),
 'desabastecimiento':('Demora en suministro simulado','media','FAR','FARMACIA,CLINICA'),
 'imagen_urgente':('Imagen diagnóstica pendiente','media','IMG','IMAGENES,CLINICA'),
}

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def timeplus(seconds):return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat(timespec='seconds')
def digest(s):return hashlib.sha256(s.encode()).hexdigest()

@contextmanager
def connection(write=False):
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    cx=sqlite3.connect(DB_PATH,timeout=20)
    cx.row_factory=sqlite3.Row
    cx.execute('PRAGMA foreign_keys=ON')
    cx.execute('PRAGMA busy_timeout=20000')
    if write:cx.execute('BEGIN IMMEDIATE')
    try:
        yield cx
        if write:cx.commit()
    except Exception:
        if write:cx.rollback()
        raise
    finally:cx.close()

def init_db():
    with connection() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY,code TEXT UNIQUE NOT NULL,title TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY,token_hash TEXT UNIQUE NOT NULL,room_id INTEGER,name TEXT NOT NULL,role TEXT NOT NULL,expires_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS beds(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,unit TEXT NOT NULL,label TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,name TEXT NOT NULL,age INTEGER NOT NULL,bed_id INTEGER UNIQUE NOT NULL,state TEXT NOT NULL DEFAULT 'hospitalizado',created_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,FOREIGN KEY(bed_id) REFERENCES beds(id));
        CREATE TABLE IF NOT EXISTS lab_orders(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,patient_id INTEGER NOT NULL,test TEXT NOT NULL,state TEXT NOT NULL,result_value REAL,result_unit TEXT,critical INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,unit TEXT NOT NULL,name TEXT NOT NULL,type TEXT NOT NULL,state TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS alarms(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,kind TEXT NOT NULL,unit TEXT NOT NULL,priority TEXT NOT NULL,message TEXT NOT NULL,state TEXT NOT NULL,source_id INTEGER,created_at TEXT NOT NULL,acknowledged_at TEXT,acknowledged_by TEXT,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,actor TEXT NOT NULL,role TEXT NOT NULL,type TEXT NOT NULL,message TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS simulation_settings(room_id INTEGER PRIMARY KEY,mode TEXT NOT NULL DEFAULT 'manual',interval_seconds INTEGER NOT NULL DEFAULT 120,difficulty TEXT NOT NULL DEFAULT 'normal',next_event_at TEXT,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,scenario TEXT NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL,unit TEXT NOT NULL,priority TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'active',created_at TEXT NOT NULL,due_at TEXT NOT NULL,resolved_at TEXT,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,incident_id INTEGER NOT NULL,role TEXT NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL,requirement TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,completed_at TEXT,completed_by TEXT,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS arrivals(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,name TEXT NOT NULL,unit TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'waiting',created_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS medication_orders(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,patient_id INTEGER NOT NULL,product TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'requested',created_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS imaging_orders(id INTEGER PRIMARY KEY,room_id INTEGER NOT NULL,patient_id INTEGER NOT NULL,study TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'requested',report TEXT,created_at TEXT NOT NULL,FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS idx_events_room ON events(room_id,id DESC);
        CREATE INDEX IF NOT EXISTS idx_incidents_room ON incidents(room_id,state);
        CREATE INDEX IF NOT EXISTS idx_tasks_room ON tasks(room_id,state);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
        ''')
    with connection(write=True) as db:
        db.execute("INSERT OR IGNORE INTO simulation_settings(room_id,mode,interval_seconds,difficulty) SELECT id,'manual',120,'normal' FROM rooms")

def record(db,room,actor,role,kind,message,payload=None):
    db.execute('INSERT INTO events(room_id,actor,role,type,message,payload,created_at) VALUES(?,?,?,?,?,?,?)',(room,actor,role,kind,message,json.dumps(payload or {},ensure_ascii=False),now()))

def seed_room(db,room):
    for unit,label in BED_LAYOUT:db.execute('INSERT INTO beds(room_id,unit,label) VALUES(?,?,?)',(room,unit,label))
    for unit,name,typ in [
        ('UCI','Monitor multiparámetro M-101','Monitor'),('UCI','Monitor multiparámetro M-102','Monitor'),('UCI','Bomba de infusión B-201','Bomba'),
        ('URG','Desfibrilador D-101','Desfibrilador'),('URG','Monitor M-103','Monitor'),('HOSP','Bomba de infusión B-202','Bomba'),
        ('QX','Máquina de anestesia A-101','Anestesia'),('LAB','Analizador de química L-101','Analizador'),('IMG','Tomógrafo T-101','Tomógrafo'),('FAR','Refrigerador farmacéutico R-101','Refrigerador')]:
        db.execute('INSERT INTO devices(room_id,unit,name,type,state) VALUES(?,?,?,?,?)',(room,unit,name,typ,'operativo'))
    for unit,name,age in [('URG','Paciente 001',42),('UCI','Paciente 002',67),('HOSP','Paciente 003',29)]:
        bed=db.execute('SELECT id FROM beds WHERE room_id=? AND unit=? AND id NOT IN (SELECT bed_id FROM patients WHERE room_id=?) LIMIT 1',(room,unit,room)).fetchone()
        db.execute('INSERT INTO patients(room_id,name,age,bed_id,created_at) VALUES(?,?,?,?,?)',(room,name,age,bed['id'],now()))
    record(db,room,'Sistema','SISTEMA','aula_iniciada','Hospital ficticio inicializado. Ninguna información representa pacientes reales.')

def create_room(title):
    with connection(write=True) as db:
        for _ in range(15):
            code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(9))
            if db.execute('SELECT 1 FROM rooms WHERE code=?',(code,)).fetchone():continue
            rid=db.execute('INSERT INTO rooms(code,title,created_at) VALUES(?,?,?)',(code,title,now())).lastrowid
            db.execute("INSERT INTO simulation_settings(room_id,mode,interval_seconds,difficulty) VALUES(?,'manual',120,'normal')",(rid,))
            seed_room(db,rid)
            return {'id':rid,'code':code,'title':title}
    raise RuntimeError('No se pudo crear código de aula.')

def find_room(code):
    with connection() as db:
        row=db.execute('SELECT * FROM rooms WHERE code=?',(code.upper(),)).fetchone();return dict(row) if row else None

def list_rooms():
    with connection() as db:return [dict(x) for x in db.execute('SELECT * FROM rooms ORDER BY id DESC LIMIT 100')]

def register_session(room,name,role):
    token=secrets.token_urlsafe(40)
    with connection(write=True) as db:db.execute('INSERT INTO sessions(token_hash,room_id,name,role,expires_at) VALUES(?,?,?,?,?)',(digest(token),room,name,role,timeplus(43200)))
    return token

def get_session(token):
    if not token or len(token)>256:return None
    with connection() as db:
        r=db.execute('SELECT * FROM sessions WHERE token_hash=?',(digest(token),)).fetchone()
        return dict(r) if r and r['expires_at']>now() else None

def rows(db,query,*args):return [dict(r) for r in db.execute(query,args)]

def room_state(room):
    with connection() as db:
        x=db.execute('SELECT * FROM rooms WHERE id=?',(room,)).fetchone()
        if not x:return None
        beds=rows(db,'SELECT b.*,p.id AS patient_id,p.name AS patient_name FROM beds b LEFT JOIN patients p ON p.bed_id=b.id WHERE b.room_id=? ORDER BY b.id',room)
        patients=rows(db,'SELECT p.*,b.unit,b.label AS bed_label FROM patients p JOIN beds b ON b.id=p.bed_id WHERE p.room_id=? ORDER BY p.id',room)
        devices=rows(db,'SELECT * FROM devices WHERE room_id=? ORDER BY id',room)
        alarms=rows(db,"SELECT * FROM alarms WHERE room_id=? ORDER BY CASE WHEN state='active' THEN 0 ELSE 1 END,id DESC LIMIT 100",room)
        lab=rows(db,'SELECT l.*,p.name AS patient_name FROM lab_orders l JOIN patients p ON l.patient_id=p.id WHERE l.room_id=? ORDER BY l.id DESC LIMIT 100',room)
        meds=rows(db,'SELECT m.*,p.name AS patient_name FROM medication_orders m JOIN patients p ON m.patient_id=p.id WHERE m.room_id=? ORDER BY m.id DESC LIMIT 100',room)
        imgs=rows(db,'SELECT m.*,p.name AS patient_name FROM imaging_orders m JOIN patients p ON m.patient_id=p.id WHERE m.room_id=? ORDER BY m.id DESC LIMIT 100',room)
        arrivals=rows(db,'SELECT * FROM arrivals WHERE room_id=? ORDER BY id DESC LIMIT 70',room)
        incidents=rows(db,"SELECT * FROM incidents WHERE room_id=? ORDER BY CASE WHEN state='active' THEN 0 ELSE 1 END,id DESC LIMIT 80",room)
        tasks=rows(db,"SELECT t.*,i.title AS incident_title FROM tasks t JOIN incidents i ON i.id=t.incident_id WHERE t.room_id=? ORDER BY CASE WHEN t.state='pending' THEN 0 ELSE 1 END,t.id DESC LIMIT 160",room)
        events=rows(db,'SELECT * FROM events WHERE room_id=? ORDER BY id DESC LIMIT 130',room)
        for e in events:
            try:e['payload']=json.loads(e['payload'])
            except ValueError:e['payload']={}
        participants=rows(db,'SELECT role,COUNT(*) AS n FROM sessions WHERE room_id=? AND expires_at>? GROUP BY role',room,now())
        settings=db.execute('SELECT * FROM simulation_settings WHERE room_id=?',(room,)).fetchone()
        ack_times=[];resolve_times=[]
        for a in alarms:
            if a['acknowledged_at']:
                try:ack_times.append(max(0,(datetime.fromisoformat(a['acknowledged_at'])-datetime.fromisoformat(a['created_at'])).total_seconds()))
                except ValueError:pass
        for inc in incidents:
            if inc['resolved_at']:
                try:resolve_times.append(max(0,(datetime.fromisoformat(inc['resolved_at'])-datetime.fromisoformat(inc['created_at'])).total_seconds()))
                except ValueError:pass
        active=sum(i['state']=='active' for i in incidents)
        pending=sum(t['state']=='pending' for t in tasks)
        return {'room':dict(x),'units':UNITS,'beds':beds,'patients':patients,'devices':devices,'alarms':alarms,
            'orders':lab,'med_orders':meds,'imaging_orders':imgs,'arrivals':arrivals,'incidents':incidents,'tasks':tasks,
            'events':events,'participants':{p['role']:p['n'] for p in participants},'settings':dict(settings) if settings else {'mode':'manual'},
            'metrics':{'beds_total':len(beds),'beds_occupied':sum(bool(b['patient_id']) for b in beds),
                'occupancy_pct':round(100*sum(bool(b['patient_id']) for b in beds)/len(beds),1) if beds else 0,
                'devices_total':len(devices),'devices_operational':sum(x['state']=='operativo' for x in devices),
                'alarms_active':sum(a['state']=='active' for a in alarms),'lab_pending':sum(o['state']!='resulted' for o in lab),
                'incidents_active':active,'tasks_pending':pending,
                'incidents_resolved':sum(i['state']=='resolved' for i in incidents),
                'mean_ack_seconds':round(sum(ack_times)/len(ack_times),1) if ack_times else None,
                'mean_resolution_seconds':round(sum(resolve_times)/len(resolve_times),1) if resolve_times else None}}

def export_events(room):
    with connection() as db:return rows(db,'SELECT id,created_at,actor,role,type,message,payload FROM events WHERE room_id=? ORDER BY id',room)

class ActionError(Exception):pass

def incident(db,room,scenario,title,description,unit,priority):
    i=db.execute('INSERT INTO incidents(room_id,scenario,title,description,unit,priority,state,created_at,due_at) VALUES(?,?,?,?,?,?,?, ?,?)',
        (room,scenario,title,description,unit,priority,'active',now(),timeplus(240 if priority=='alta' else 360))).lastrowid
    record(db,room,'Motor de simulación','SISTEMA','incidente_creado',f'{title} · {unit}',{'incident_id':i,'scenario':scenario,'priority':priority})
    return i

def task(db,room,i,role,title,description,requirement):
    db.execute('INSERT INTO tasks(room_id,incident_id,role,title,description,requirement,created_at) VALUES(?,?,?,?,?,?,?)',(room,i,role,title,description,requirement,now()))

def create_alarm(db,room,kind,unit,priority,message,source_id=None):
    return db.execute('INSERT INTO alarms(room_id,kind,unit,priority,message,state,source_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(room,kind,unit,priority,message,'active',source_id,now())).lastrowid

def spawn(db,room,scenario,actor='Sistema',role='SISTEMA'):
    if scenario not in SCENARIOS:raise ActionError('Escenario no reconocido.')
    active=db.execute("SELECT COUNT(*) FROM incidents WHERE room_id=? AND state='active'",(room,)).fetchone()[0]
    if active>=4:raise ActionError('Ya hay cuatro incidentes abiertos; resuelve los anteriores.')
    if scenario=='desaturacion':
        unit='UCI';device=db.execute("SELECT id FROM devices WHERE room_id=? AND unit='UCI' ORDER BY id LIMIT 1",(room,)).fetchone()
        i=incident(db,room,scenario,'Alerta de monitorización en UCI','Se registra una desaturación ficticia. Coordinar confirmación clínica y revisión del monitor.',unit,'alta')
        alarm=create_alarm(db,room,'clinical',unit,'alta','SpO₂ simulada 84 %. Ejercicio docente.')
        task(db,room,i,'CLINICA','Reconocer alerta de UCI','Reconocer la alarma en el panel y documentar la recepción.',f'alarm_ack:{alarm}')
        if device:task(db,room,i,'BIOMED','Verificar monitor de UCI','Ejecutar verificación técnica del monitor asociado al servicio.',f'device_check:{device[0]}')
    elif scenario=='falla_equipo':
        candidates=db.execute("SELECT * FROM devices WHERE room_id=? AND state='operativo' ORDER BY RANDOM() LIMIT 1",(room,)).fetchone()
        if not candidates:raise ActionError('No quedan equipos operativos para generar una falla.')
        db.execute("UPDATE devices SET state='en_falla' WHERE id=?",(candidates['id'],))
        i=incident(db,room,scenario,'Equipo fuera de servicio',f'{candidates["name"]} presenta una falla simulada. Requiere aviso clínico y recuperación técnica.',candidates['unit'],'alta')
        alarm=create_alarm(db,room,'technical',candidates['unit'],'alta',f'Equipo indisponible: {candidates["name"]}.',candidates['id'])
        task(db,room,i,'CLINICA','Reconocer indisponibilidad','Reconocer la alerta técnica para coordinar continuidad operativa.',f'alarm_ack:{alarm}')
        task(db,room,i,'BIOMED','Restituir dispositivo','Cambiar el equipo a operativo después de la intervención simulada.',f'device_operational:{candidates["id"]}')
    elif scenario=='llegada_masiva':
        waiting=db.execute("SELECT COUNT(*) FROM arrivals WHERE room_id=? AND state='waiting'",(room,)).fetchone()[0]
        if waiting>=5:raise ActionError('Hay demasiados pacientes sintéticos pendientes de admisión.')
        next_num=db.execute('SELECT COUNT(*) FROM arrivals WHERE room_id=?',(room,)).fetchone()[0]+100
        i=incident(db,room,scenario,'Paciente ficticio en sala de espera','Un nuevo ingreso requiere una cama libre en Urgencias u Hospitalización. La clínica debe registrar su recepción.', 'URG','media')
        arr=db.execute('INSERT INTO arrivals(room_id,name,unit,created_at) VALUES(?,?,?,?)',(room,f'Paciente {next_num:03d}','URG',now())).lastrowid
        task(db,room,i,'HIS','Asignar cama al paciente en espera','Elegir una cama disponible y completar la admisión desde HIS.',f'arrival_admitted:{arr}')
        task(db,room,i,'CLINICA','Registrar recepción clínica','Confirmar recepción del ingreso mediante la acción de la estación clínica.',f'arrival_received:{arr}')
    elif scenario=='resultado_critico':
        patient=db.execute('SELECT id FROM patients WHERE room_id=? ORDER BY RANDOM() LIMIT 1',(room,)).fetchone()
        if not patient:raise ActionError('No hay pacientes para solicitar exámenes.')
        i=incident(db,room,scenario,'Análisis prioritario','Laboratorio debe procesar una orden ficticia y Clínica reconocer la alerta generada por un resultado crítico.', 'LAB','alta')
        oid=db.execute("INSERT INTO lab_orders(room_id,patient_id,test,state,created_at) VALUES(?,?,?,'received',?)",(room,patient['id'],'Potasio',now())).lastrowid
        task(db,room,i,'LIS','Informar potasio simulado','Publicar resultado crítico en LIS para generar una notificación.',f'lab_critical:{oid}')
        task(db,room,i,'CLINICA','Reconocer resultado crítico','Después del resultado, reconocer la alerta clínica desde el panel.',f'critical_ack:{oid}')
    elif scenario=='desabastecimiento':
        patient=db.execute('SELECT id FROM patients WHERE room_id=? ORDER BY RANDOM() LIMIT 1',(room,)).fetchone()
        if not patient:raise ActionError('No existen pacientes.')
        i=incident(db,room,scenario,'Solicitud pendiente de Farmacia','Una orden de insumo ficticio queda pendiente. Clínica y Farmacia deben coordinar el suministro.', 'FAR','media')
        mid=db.execute("INSERT INTO medication_orders(room_id,patient_id,product,state,created_at) VALUES(?,?,?,'requested',?)",(room,patient['id'],'Insumo A',now())).lastrowid
        task(db,room,i,'FARMACIA','Dispensar suministro simulado','Registrar la dispensación del insumo ficticio.',f'med_dispensed:{mid}')
        task(db,room,i,'CLINICA','Confirmar entrega','Después de dispensación, confirmar recepción desde Clínica.',f'med_received:{mid}')
    elif scenario=='imagen_urgente':
        patient=db.execute('SELECT id FROM patients WHERE room_id=? ORDER BY RANDOM() LIMIT 1',(room,)).fetchone()
        if not patient:raise ActionError('No existen pacientes.')
        i=incident(db,room,scenario,'Estudio de imagen pendiente','Diagnóstico por imagen debe informar el examen simulado. Clínica revisa la comunicación.', 'IMG','media')
        oid=db.execute("INSERT INTO imaging_orders(room_id,patient_id,study,state,created_at) VALUES(?,?,?,'requested',?)",(room,patient['id'],'Radiografía simulada',now())).lastrowid
        task(db,room,i,'IMAGENES','Publicar informe de imagen','Registrar un informe ficticio desde Imagenología.',f'imaging_reported:{oid}')
        task(db,room,i,'CLINICA','Confirmar revisión del informe','Marcar que Clínica ha recibido el resultado simulado.',f'imaging_reviewed:{oid}')
    record(db,room,actor,role,'escenario',f'Se activó el escenario {SCENARIOS[scenario][0]}.',{'scenario':scenario,'incident_id':i})
    return i

def update_tasks(db,room,actor,role):
    pending=db.execute("SELECT * FROM tasks WHERE room_id=? AND state='pending'",(room,)).fetchall()
    for t in pending:
        typ,_,num=t['requirement'].partition(':')
        target=int(num)
        ok=False
        if typ=='alarm_ack':
            r=db.execute('SELECT acknowledged_at,acknowledged_by FROM alarms WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['acknowledged_at'] and db.execute("SELECT 1 FROM events WHERE room_id=? AND role IN (?, 'DOCENTE') AND type='alarma_reconocida' AND json_extract(payload,'$.alarm_id')=? AND created_at>=?",(room,t['role'],target,t['created_at'])).fetchone())
        elif typ=='critical_ack':
            r=db.execute("SELECT 1 FROM alarms WHERE room_id=? AND kind='clinical' AND source_id=? AND acknowledged_at IS NOT NULL",(room,target)).fetchone();ok=bool(r)
        elif typ=='device_operational':
            r=db.execute('SELECT state FROM devices WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state']=='operativo')
        elif typ=='device_check':
            r=db.execute("SELECT 1 FROM events WHERE room_id=? AND role IN ('BIOMED','DOCENTE') AND type='verificacion_equipo' AND json_extract(payload,'$.device_id')=? AND created_at>=?",(room,target,t['created_at'])).fetchone();ok=bool(r)
        elif typ=='arrival_admitted':
            r=db.execute('SELECT state FROM arrivals WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state']=='admitted')
        elif typ=='arrival_received':
            r=db.execute('SELECT state FROM arrivals WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state']=='received')
        elif typ=='lab_critical':
            r=db.execute('SELECT state,critical FROM lab_orders WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state']=='resulted' and r['critical'])
        elif typ=='med_dispensed':
            r=db.execute('SELECT state FROM medication_orders WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state'] in ('dispensed','received'))
        elif typ=='med_received':
            r=db.execute('SELECT state FROM medication_orders WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state']=='received')
        elif typ=='imaging_reported':
            r=db.execute('SELECT state FROM imaging_orders WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state'] in ('reported','reviewed'))
        elif typ=='imaging_reviewed':
            r=db.execute('SELECT state FROM imaging_orders WHERE id=? AND room_id=?',(target,room)).fetchone();ok=bool(r and r['state']=='reviewed')
        if ok:
            db.execute("UPDATE tasks SET state='completed',completed_at=?,completed_by=? WHERE id=?",(now(),actor,t['id']))
            record(db,room,actor,role,'tarea_completada',t['title'],{'task_id':t['id'],'incident_id':t['incident_id']})
    for i in db.execute("SELECT id,title FROM incidents WHERE room_id=? AND state='active'",(room,)).fetchall():
        n=db.execute("SELECT COUNT(*) FROM tasks WHERE incident_id=? AND state='pending'",(i['id'],)).fetchone()[0]
        if not n:
            db.execute("UPDATE incidents SET state='resolved',resolved_at=? WHERE id=?",(now(),i['id']))
            record(db,room,actor,role,'incidente_resuelto',f'Flujo completado: {i["title"]}. No implica resolución clínica real.',{'incident_id':i['id']})

def action(room,actor,role,kind,target_id=None,value=None):
    allowed={
    'admit':{'HIS','DOCENTE'},'admit_arrival':{'HIS','DOCENTE'},'discharge':{'HIS','DOCENTE'},'transfer':{'HIS','DOCENTE'},
    'lab_order':{'CLINICA','DOCENTE'},'sample_received':{'LIS','DOCENTE'},'lab_result':{'LIS','DOCENTE'},
    'med_order':{'CLINICA','DOCENTE'},'med_dispense':{'FARMACIA','DOCENTE'},'med_receive':{'CLINICA','DOCENTE'},
    'imaging_order':{'CLINICA','DOCENTE'},'imaging_result':{'IMAGENES','DOCENTE'},'imaging_review':{'CLINICA','DOCENTE'},
    'device_status':{'BIOMED','DOCENTE'},'device_check':{'BIOMED','DOCENTE'},'arrival_receive':{'CLINICA','DOCENTE'},
    'alarm_ack':{'CLINICA','BIOMED','DOCENTE'},'scenario_spawn':{'DOCENTE'},'simulation_config':{'DOCENTE'},'reset_room':{'DOCENTE'},
    'trigger_alarm':{'DOCENTE'},}
    if kind not in allowed or role not in allowed[kind]:raise ActionError('Tu rol no está autorizado para esta acción.')
    with connection(write=True) as db:
        def check(table,i):
            return db.execute(f'SELECT * FROM {table} WHERE id=? AND room_id=?',(i,room)).fetchone()
        def patient():
            p=check('patients',target_id)
            if not p:raise ActionError('Paciente ficticio no encontrado.')
            return p
        if kind in ('admit','admit_arrival'):
            arr=check('arrivals',target_id) if kind=='admit_arrival' else None
            if kind=='admit_arrival' and (not arr or arr['state']!='waiting'):raise ActionError('Ingreso pendiente no válido.')
            bid=int(value) if kind=='admit_arrival' and str(value).isdigit() else target_id
            bed=check('beds',bid)
            if not bed:raise ActionError('Cama no encontrada.')
            if db.execute('SELECT 1 FROM patients WHERE bed_id=?',(bid,)).fetchone():raise ActionError('La cama está ocupada.')
            if len(rows(db,'SELECT id FROM patients WHERE room_id=?',room))>=len(NAMES):raise ActionError('Se alcanzó el límite de pacientes sintéticos.')
            num=db.execute('SELECT COUNT(*) FROM patients WHERE room_id=?',(room,)).fetchone()[0]
            name=arr['name'] if arr else f'Paciente {num+1:03d}'
            db.execute('INSERT INTO patients(room_id,name,age,bed_id,created_at) VALUES(?,?,?,?,?)',(room,name,30+(num*7)%48,bid,now()))
            if arr:db.execute("UPDATE arrivals SET state='admitted' WHERE id=?",(target_id,))
            record(db,room,actor,role,'admision',f'{name} ingresó en {bed["label"]}.',{'resourceType':'Encounter','location':bed['label']})
        elif kind=='discharge':
            p=patient();db.execute('DELETE FROM patients WHERE id=?',(p['id'],))
            record(db,room,actor,role,'alta',f'{p["name"]} egresó del hospital simulado.')
        elif kind=='transfer':
            p=patient();bed=check('beds',int(value)) if str(value).isdigit() else None
            if not bed or db.execute('SELECT 1 FROM patients WHERE bed_id=?',(bed['id'],)).fetchone():raise ActionError('Selecciona una cama libre.')
            db.execute('UPDATE patients SET bed_id=? WHERE id=?',(bed['id'],p['id']))
            record(db,room,actor,role,'traslado',f'{p["name"]} fue trasladado a {bed["label"]}.')
        elif kind=='arrival_receive':
            arr=check('arrivals',target_id)
            if not arr or arr['state']!='admitted':raise ActionError('Primero HIS debe admitir al paciente.')
            db.execute("UPDATE arrivals SET state='received' WHERE id=?",(target_id,))
            record(db,room,actor,role,'recepcion_clinica',f'Recepción registrada para {arr["name"]}.')
        elif kind=='lab_order':
            p=patient()
            if value not in TESTS:raise ActionError('Análisis no permitido.')
            oid=db.execute("INSERT INTO lab_orders(room_id,patient_id,test,state,created_at) VALUES(?,?,?,'requested',?)",(room,p['id'],value,now())).lastrowid
            record(db,room,actor,role,'orden_laboratorio',f'{value} solicitado para {p["name"]}.',{'resourceType':'ServiceRequest','id':oid})
        elif kind=='sample_received':
            x=check('lab_orders',target_id)
            if not x or x['state']!='requested':raise ActionError('La orden debe estar solicitada.')
            db.execute("UPDATE lab_orders SET state='received' WHERE id=?",(target_id,))
            record(db,room,actor,role,'muestra_recibida',f'Muestra recibida para orden #{target_id}.')
        elif kind=='lab_result':
            x=check('lab_orders',target_id)
            if not x or x['state']!='received' or value not in ('normal','critical'):raise ActionError('Recibe la muestra primero y elige un resultado válido.')
            unit,normal,critical=TESTS[x['test']];result=normal if value=='normal' else critical;iscritical=int(value=='critical')
            db.execute("UPDATE lab_orders SET state='resulted',result_value=?,result_unit=?,critical=? WHERE id=?",(result,unit,iscritical,target_id))
            record(db,room,actor,role,'resultado_lis',f'{x["test"]}: {result} {unit} (simulado).',{'resourceType':'Observation','order_id':target_id,'critical':bool(iscritical)})
            if iscritical:create_alarm(db,room,'clinical','LAB','alta',f'Valor crítico simulado: {x["test"]} {result} {unit}. Orden #{target_id}.',target_id)
        elif kind=='med_order':
            p=patient()
            if value not in MEDICATIONS:raise ActionError('Producto ficticio no válido.')
            oid=db.execute('INSERT INTO medication_orders(room_id,patient_id,product,created_at) VALUES(?,?,?,?)',(room,p['id'],value,now())).lastrowid
            record(db,room,actor,role,'orden_farmacia',f'Solicitud de {value} para {p["name"]}.',{'id':oid})
        elif kind=='med_dispense':
            x=check('medication_orders',target_id)
            if not x or x['state']!='requested':raise ActionError('Orden no dispensable.')
            db.execute("UPDATE medication_orders SET state='dispensed' WHERE id=?",(target_id,));record(db,room,actor,role,'dispensacion',f'Insumo #{target_id} dispensado (simulado).')
        elif kind=='med_receive':
            x=check('medication_orders',target_id)
            if not x or x['state']!='dispensed':raise ActionError('Farmacia debe dispensar antes.')
            db.execute("UPDATE medication_orders SET state='received' WHERE id=?",(target_id,));record(db,room,actor,role,'recepcion_insumo',f'Clínica recibió el suministro #{target_id}.')
        elif kind=='imaging_order':
            p=patient()
            if value not in IMAGING:raise ActionError('Estudio no reconocido.')
            oid=db.execute('INSERT INTO imaging_orders(room_id,patient_id,study,created_at) VALUES(?,?,?,?)',(room,p['id'],value,now())).lastrowid
            record(db,room,actor,role,'orden_imagen',f'{value} solicitado para {p["name"]}.',{'id':oid})
        elif kind=='imaging_result':
            x=check('imaging_orders',target_id)
            if not x or x['state']!='requested' or value not in ('Informe A','Informe B'):raise ActionError('Estudio o informe inválido.')
            db.execute("UPDATE imaging_orders SET state='reported',report=? WHERE id=?",(value,target_id));record(db,room,actor,role,'informe_imagen',f'Imagen #{target_id} informada: {value} (ficticio).')
        elif kind=='imaging_review':
            x=check('imaging_orders',target_id)
            if not x or x['state']!='reported':raise ActionError('Todavía no hay informe disponible.')
            db.execute("UPDATE imaging_orders SET state='reviewed' WHERE id=?",(target_id,));record(db,room,actor,role,'revision_imagen',f'Clínica confirmó recepción de informe #{target_id}.')
        elif kind=='device_status':
            x=check('devices',target_id)
            if not x or value not in ('en_falla','operativo') or x['state']==value:raise ActionError('Transición de equipo no válida.')
            db.execute('UPDATE devices SET state=? WHERE id=?',(value,target_id))
            record(db,room,actor,role,'estado_equipo',f'{x["name"]}: {value}.')
            if value=='en_falla':create_alarm(db,room,'technical',x['unit'],'media',f'Falla técnica: {x["name"]}.',target_id)
            else:db.execute("UPDATE alarms SET state='resolved' WHERE room_id=? AND kind='technical' AND source_id=? AND state='acknowledged'",(room,target_id))
        elif kind=='device_check':
            x=check('devices',target_id)
            if not x:raise ActionError('Equipo inexistente.')
            record(db,room,actor,role,'verificacion_equipo',f'Verificación funcional didáctica: {x["name"]}.',{'device_id':target_id})
        elif kind=='alarm_ack':
            a=check('alarms',target_id)
            if not a or a['state']!='active':raise ActionError('Alarma no activa.')
            if a['kind']=='clinical' and role=='BIOMED':raise ActionError('Biomédica no reconoce alarmas clínicas.')
            if a['kind']=='technical' and role=='BIOMED' and db.execute("SELECT 1 FROM tasks WHERE room_id=? AND state='pending' AND role='CLINICA' AND requirement=?",(room,f'alarm_ack:{target_id}')).fetchone():raise ActionError('Esta alerta requiere primero reconocimiento por Clínica.')
            db.execute("UPDATE alarms SET state='acknowledged',acknowledged_at=?,acknowledged_by=? WHERE id=?",(now(),actor,target_id))
            record(db,room,actor,role,'alarma_reconocida',f'Alarma #{target_id} reconocida; no significa condición resuelta.',{'alarm_id':target_id})
            if a['kind']=='technical' and a['source_id']:
                x=check('devices',a['source_id'])
                if x and x['state']=='operativo':db.execute("UPDATE alarms SET state='resolved' WHERE id=?",(target_id,))
        elif kind in ('scenario_spawn','trigger_alarm'):
            scenario=value if kind=='scenario_spawn' else 'desaturacion'
            if kind=='trigger_alarm' and value not in ('UCI','URG','HOSP'):raise ActionError('Unidad inválida.')
            spawn(db,room,scenario,actor,role)
        elif kind=='simulation_config':
            try:cfg=json.loads(value)
            except (TypeError,ValueError):raise ActionError('Configuración inválida.')
            mode=cfg.get('mode');interval=cfg.get('interval_seconds');difficulty=cfg.get('difficulty')
            if mode not in ('manual','auto','paused') or type(interval) is not int or not 30<=interval<=900 or difficulty not in ('facil','normal','intenso'):
                raise ActionError('Configuración fuera de rango.')
            db.execute('UPDATE simulation_settings SET mode=?,interval_seconds=?,difficulty=?,next_event_at=? WHERE room_id=?',
                (mode,interval,difficulty,timeplus(interval) if mode=='auto' else None,room))
            record(db,room,actor,role,'configuracion',f'Motor: {mode}, intervalo {interval}s, dificultad {difficulty}.')
        elif kind=='reset_room':
            if value!='CONFIRMAR':raise ActionError('Confirmación requerida.')
            for tbl in ('tasks','incidents','arrivals','medication_orders','imaging_orders','alarms','lab_orders','patients','devices','beds','events'):
                db.execute(f'DELETE FROM {tbl} WHERE room_id=?',(room,))
            db.execute("UPDATE simulation_settings SET mode='manual',next_event_at=NULL WHERE room_id=?",(room,))
            seed_room(db,room)
            record(db,room,actor,role,'reinicio','Aula reiniciada por docente.')
        update_tasks(db,room,actor,role)
    return {'ok':True}

def auto_tick():
    """Cada llamada intenta un incidente por aula vencida, sin alterar aulas en modo manual."""
    affected=[]
    with connection(write=True) as db:
        settings=db.execute("SELECT * FROM simulation_settings WHERE mode='auto' AND next_event_at IS NOT NULL AND next_event_at<=?",(now(),)).fetchall()
        for s in settings:
            room=s['room_id']
            delay=s['interval_seconds']
            jitter=random.uniform(0.85,1.25)
            if s['difficulty']=='facil':jitter*=1.5
            if s['difficulty']=='intenso':jitter*=0.7
            db.execute('UPDATE simulation_settings SET next_event_at=? WHERE room_id=?',(timeplus(max(30,int(delay*jitter))),room))
            choices=list(SCENARIOS)
            random.shuffle(choices)
            for scenario in choices:
                try:
                    # Failed scenario attempt must not leave partial rows: use SAVEPOINT.
                    db.execute('SAVEPOINT scenario')
                    spawn(db,room,scenario)
                    db.execute('RELEASE SAVEPOINT scenario')
                    affected.append(room)
                    break
                except ActionError:
                    db.execute('ROLLBACK TO SAVEPOINT scenario')
                    db.execute('RELEASE SAVEPOINT scenario')
    return affected
