"""SQLite persistence for the educational hospital simulation.
All rows are synthetic; no patient health information is accepted.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.getenv('DATABASE_PATH', '/data/hospital.db'))
UNITS = {'URG': 'Urgencias', 'UCI': 'Cuidados intensivos', 'HOSP': 'Hospitalización', 'LAB': 'Laboratorio', 'QX': 'Quirófanos', 'BIO': 'Ingeniería biomédica'}
BED_LAYOUT = [('URG', f'Urgencias {n:02d}') for n in range(1, 5)] + [('UCI', f'UCI {n:02d}') for n in range(1, 4)] + [('HOSP', f'Hospitalización {n:02d}') for n in range(1, 6)]
SYNTHETIC_NAMES = ['Paciente Alfa', 'Paciente Beta', 'Paciente Gamma', 'Paciente Delta', 'Paciente Épsilon', 'Paciente Zeta', 'Paciente Eta', 'Paciente Theta', 'Paciente Iota', 'Paciente Kappa', 'Paciente Lambda', 'Paciente Mu']
TESTS = {
    'Potasio': {'unit':'mmol/L', 'normal':4.2, 'critical':6.3},
    'Glucosa': {'unit':'mg/dL', 'normal':105, 'critical':48},
    'Hemoglobina': {'unit':'g/dL', 'normal':13.7, 'critical':6.5},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def token_hash(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@contextmanager
def connection(write=False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=20000')
    if write:
        conn.execute('BEGIN IMMEDIATE')
    try:
        yield conn
        if write: conn.commit()
    except Exception:
        if write: conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connection(write=True) as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS rooms(
          id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
          id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, room_id INTEGER,
          name TEXT NOT NULL, role TEXT NOT NULL, expires_at TEXT NOT NULL,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS beds(
          id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL, unit TEXT NOT NULL, label TEXT NOT NULL,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS patients(
          id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL, name TEXT NOT NULL, age INTEGER NOT NULL,
          bed_id INTEGER UNIQUE NOT NULL, state TEXT NOT NULL DEFAULT 'hospitalizado', created_at TEXT NOT NULL,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
          FOREIGN KEY(bed_id) REFERENCES beds(id));
        CREATE TABLE IF NOT EXISTS lab_orders(
          id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL, patient_id INTEGER NOT NULL,
          test TEXT NOT NULL, state TEXT NOT NULL, result_value REAL, result_unit TEXT,
          critical INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
          FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS devices(
          id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL, unit TEXT NOT NULL,
          name TEXT NOT NULL, type TEXT NOT NULL, state TEXT NOT NULL,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS alarms(
          id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL,
          kind TEXT NOT NULL, unit TEXT NOT NULL, priority TEXT NOT NULL,
          message TEXT NOT NULL, state TEXT NOT NULL, source_id INTEGER,
          created_at TEXT NOT NULL, acknowledged_at TEXT, acknowledged_by TEXT,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL,
          actor TEXT NOT NULL, role TEXT NOT NULL, type TEXT NOT NULL,
          message TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
        CREATE INDEX IF NOT EXISTS idx_events_room ON events(room_id, id DESC);
        CREATE INDEX IF NOT EXISTS idx_alarms_room ON alarms(room_id, state);
        ''')


def record(db, room_id, actor, role, kind, message, payload=None):
    db.execute('INSERT INTO events(room_id,actor,role,type,message,payload,created_at) VALUES(?,?,?,?,?,?,?)',
               (room_id,actor,role,kind,message,json.dumps(payload or {}, ensure_ascii=False),now()))


def seed_room(db, room_id: int):
    for unit,label in BED_LAYOUT:
        db.execute('INSERT INTO beds(room_id,unit,label) VALUES(?,?,?)',(room_id,unit,label))
    for unit,name,device_type in [
        ('UCI','Monitor multiparámetro M-101','Monitor'),
        ('UCI','Monitor multiparámetro M-102','Monitor'),
        ('UCI','Bomba de infusión B-201','Bomba'),
        ('URG','Desfibrilador D-101','Desfibrilador'),
        ('URG','Monitor multiparámetro M-103','Monitor'),
        ('HOSP','Bomba de infusión B-202','Bomba'),
        ('QX','Máquina de anestesia A-101','Anestesia'),
        ('LAB','Analizador de química L-101','Analizador'),
    ]:
        db.execute('INSERT INTO devices(room_id,unit,name,type,state) VALUES(?,?,?,?,?)',
                   (room_id,unit,name,device_type,'operativo'))
    for i, (unit,name,age) in enumerate([('URG','Paciente Alfa',42),('UCI','Paciente Beta',67),('HOSP','Paciente Gamma',29)]):
        bed=db.execute('SELECT id FROM beds WHERE room_id=? AND unit=? AND id NOT IN (SELECT bed_id FROM patients) ORDER BY id LIMIT 1',(room_id,unit)).fetchone()
        db.execute('INSERT INTO patients(room_id,name,age,bed_id,created_at) VALUES(?,?,?,?,?)',
                   (room_id,name,age,bed['id'],now()))
    record(db,room_id,'Sistema','SISTEMA','aula_iniciada','Aula creada con pacientes, camas y equipos ficticios.')


def create_room(title):
    with connection(write=True) as db:
        for _ in range(10):
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(9))
            if not db.execute('SELECT 1 FROM rooms WHERE code=?',(code,)).fetchone():
                cur=db.execute('INSERT INTO rooms(code,title,created_at) VALUES(?,?,?)',(code,title,now()))
                seed_room(db,cur.lastrowid)
                return {'id':cur.lastrowid,'code':code,'title':title}
    raise RuntimeError('No se pudo generar un código de aula único.')


def find_room(code):
    with connection() as db:
        row=db.execute('SELECT * FROM rooms WHERE code=?',(code.upper(),)).fetchone()
        return dict(row) if row else None


def register_session(room_id, name, role):
    token=secrets.token_urlsafe(40)
    expires=(datetime.now(timezone.utc)+timedelta(hours=12)).isoformat(timespec='seconds')
    with connection(write=True) as db:
        db.execute('INSERT INTO sessions(token_hash,room_id,name,role,expires_at) VALUES(?,?,?,?,?)',
                   (token_hash(token),room_id,name,role,expires))
    return token


def get_session(token):
    if not token or len(token)>256: return None
    with connection() as db:
        row=db.execute('SELECT * FROM sessions WHERE token_hash=?',(token_hash(token),)).fetchone()
        if not row: return None
        actor=dict(row)
        if actor['expires_at'] < now(): return None
        return actor


def list_rooms():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT id,code,title,created_at FROM rooms ORDER BY id DESC LIMIT 100')]


def room_state(room_id):
    with connection() as db:
        room=db.execute('SELECT * FROM rooms WHERE id=?',(room_id,)).fetchone()
        if not room: return None
        beds=[dict(r) for r in db.execute('''SELECT b.*,p.id AS patient_id,p.name AS patient_name
              FROM beds b LEFT JOIN patients p ON p.bed_id=b.id WHERE b.room_id=? ORDER BY b.id''',(room_id,))]
        patients=[dict(r) for r in db.execute('''SELECT p.*,b.unit,b.label AS bed_label FROM patients p
              JOIN beds b ON b.id=p.bed_id WHERE p.room_id=? ORDER BY p.id''',(room_id,))]
        devices=[dict(r) for r in db.execute('SELECT * FROM devices WHERE room_id=? ORDER BY id',(room_id,))]
        orders=[dict(r) for r in db.execute('''SELECT l.*,p.name AS patient_name FROM lab_orders l
              JOIN patients p ON p.id=l.patient_id WHERE l.room_id=? ORDER BY l.id DESC LIMIT 60''',(room_id,))]
        alarms=[dict(r) for r in db.execute('SELECT * FROM alarms WHERE room_id=? ORDER BY CASE state WHEN "active" THEN 0 ELSE 1 END,id DESC LIMIT 80',(room_id,))]
        events=[dict(r) for r in db.execute('SELECT * FROM events WHERE room_id=? ORDER BY id DESC LIMIT 90',(room_id,))]
        for e in events:
            try: e['payload']=json.loads(e['payload'])
            except Exception: e['payload']={}
        members=db.execute('SELECT role,COUNT(*) n FROM sessions WHERE room_id=? AND expires_at>? GROUP BY role',(room_id,now())).fetchall()
        occupied=sum(bool(b['patient_id']) for b in beds)
        acked=[a for a in alarms if a['acknowledged_at'] and a['created_at']]
        turnaround=[]
        for a in acked:
            try:
                seconds=(datetime.fromisoformat(a['acknowledged_at'])-datetime.fromisoformat(a['created_at'])).total_seconds()
                turnaround.append(max(0,seconds))
            except ValueError: pass
        return {
          'room':dict(room),'units':UNITS,'beds':beds,'patients':patients,'devices':devices,
          'orders':orders,'alarms':alarms,'events':events,'participants':{m['role']:m['n'] for m in members},
          'metrics':{
             'beds_total':len(beds),'beds_occupied':occupied,
             'occupancy_pct':round(occupied/len(beds)*100,1) if beds else 0,
             'devices_total':len(devices),'devices_operational':sum(d['state']=='operativo' for d in devices),
             'alarms_active':sum(a['state']=='active' for a in alarms),
             'lab_pending':sum(o['state']!='resulted' for o in orders),
             'mean_ack_seconds':round(sum(turnaround)/len(turnaround),1) if turnaround else None,
          }
        }


def export_events(room_id):
    with connection() as db:
        return [dict(r) for r in db.execute('''SELECT id,created_at,actor,role,type,message,payload
                 FROM events WHERE room_id=? ORDER BY id''',(room_id,))]


class ActionError(Exception):
    pass


def action(room_id, actor, role, kind, target_id=None, value=None):
    allowed={
      'admit':{'HIS','DOCENTE'},
      'lab_order':{'CLINICA','DOCENTE'},
      'sample_received':{'LIS','DOCENTE'},
      'lab_result':{'LIS','DOCENTE'},
      'device_status':{'BIOMED','DOCENTE'},
      'alarm_ack':{'CLINICA','BIOMED','DOCENTE'},
      'trigger_alarm':{'DOCENTE'},
      'reset_room':{'DOCENTE'},
    }
    if kind not in allowed or role not in allowed[kind]:
        raise ActionError('Este rol no está autorizado para realizar la acción.')
    with connection(write=True) as db:
        if kind=='admit':
            bed=db.execute('''SELECT b.*,p.id AS occupied FROM beds b LEFT JOIN patients p ON p.bed_id=b.id
                WHERE b.id=? AND b.room_id=?''',(target_id,room_id)).fetchone()
            if not bed: raise ActionError('Cama no encontrada en esta aula.')
            if bed['occupied']: raise ActionError('La cama ya está ocupada.')
            number=db.execute('SELECT COUNT(*) n FROM patients WHERE room_id=?',(room_id,)).fetchone()['n']
            if number>=len(SYNTHETIC_NAMES): raise ActionError('Se alcanzó el máximo de pacientes ficticios de esta aula.')
            name=SYNTHETIC_NAMES[number]
            cur=db.execute('INSERT INTO patients(room_id,name,age,bed_id,created_at) VALUES(?,?,?,?,?)',
                     (room_id,name,30+(number*7)%48,target_id,now()))
            record(db,room_id,actor,role,'admision',f'Admisión de {name} en {bed["label"]}.',
                   {'resourceType':'Encounter','status':'in-progress','subject':{'reference':f'Patient/{cur.lastrowid}'},'location':[{'location':{'display':bed['label']}}]})
        elif kind=='lab_order':
            patient=db.execute('SELECT * FROM patients WHERE id=? AND room_id=?',(target_id,room_id)).fetchone()
            if not patient: raise ActionError('Paciente no encontrado.')
            if value not in TESTS: raise ActionError('Prueba de laboratorio no válida.')
            cur=db.execute('INSERT INTO lab_orders(room_id,patient_id,test,state,created_at) VALUES(?,?,?,?,?)',
                           (room_id,target_id,value,'requested',now()))
            record(db,room_id,actor,role,'orden_laboratorio',f'Solicitud {value} para {patient["name"]}.',
                   {'resourceType':'ServiceRequest','id':f'LAB-{cur.lastrowid}','status':'active',
                    'intent':'order','subject':{'reference':f'Patient/{target_id}'},'code':{'text':value}})
        elif kind=='sample_received':
            order=db.execute('SELECT * FROM lab_orders WHERE id=? AND room_id=?',(target_id,room_id)).fetchone()
            if not order: raise ActionError('Orden no encontrada.')
            if order['state']!='requested': raise ActionError('Solo se puede recibir una muestra solicitada.')
            db.execute('UPDATE lab_orders SET state="received" WHERE id=?',(target_id,))
            record(db,room_id,actor,role,'muestra_recibida',f'LIS recibió la muestra de {order["test"]}, orden {target_id}.',
                   {'event':'specimen-received','order_id':target_id,'test':order['test']})
        elif kind=='lab_result':
            order=db.execute('SELECT * FROM lab_orders WHERE id=? AND room_id=?',(target_id,room_id)).fetchone()
            if not order: raise ActionError('Orden no encontrada.')
            if order['state']!='received': raise ActionError('Primero se debe registrar la recepción de la muestra.')
            if value not in ('normal','critical'): raise ActionError('Resultado no reconocido.')
            config=TESTS[order['test']]
            result=config[value]
            crit=int(value=='critical')
            db.execute('UPDATE lab_orders SET state="resulted",result_value=?,result_unit=?,critical=? WHERE id=?',
                       (result,config['unit'],crit,target_id))
            record(db,room_id,actor,role,'resultado_lis',f'Resultado {order["test"]}: {result} {config["unit"]} (simulado).',
                   {'resourceType':'Observation','status':'final','subject':{'reference':f'Patient/{order["patient_id"]}'},
                    'basedOn':[{'reference':f'ServiceRequest/LAB-{target_id}'}], 'code':{'text':order['test']},
                    'valueQuantity':{'value':result,'unit':config['unit']}})
            if crit:
                db.execute('INSERT INTO alarms(room_id,kind,unit,priority,message,state,source_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
                           (room_id,'clinical','LAB','alta',f'Valor crítico simulado: {order["test"]} {result} {config["unit"]} · orden {target_id}.','active',target_id,now()))
                record(db,room_id,'Motor de alertas','SISTEMA','alarma_clinica',
                       f'Nueva alerta por resultado crítico de laboratorio, orden {target_id}.')
        elif kind=='device_status':
            device=db.execute('SELECT * FROM devices WHERE id=? AND room_id=?',(target_id,room_id)).fetchone()
            if not device: raise ActionError('Equipo no encontrado.')
            if value not in ('en_falla','operativo'): raise ActionError('Estado no permitido.')
            if device['state']==value: raise ActionError('El equipo ya está en ese estado.')
            db.execute('UPDATE devices SET state=? WHERE id=?',(value,target_id))
            record(db,room_id,actor,role,'estado_equipo',f'{device["name"]}: {"falla simulada" if value=="en_falla" else "equipo operativo"}.',
                   {'resourceType':'Device','id':f'DEV-{target_id}','status':'inactive' if value=='en_falla' else 'active'})
            if value=='en_falla':
                db.execute('INSERT INTO alarms(room_id,kind,unit,priority,message,state,source_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
                           (room_id,'technical',device['unit'],'media',f'Falla técnica simulada: {device["name"]}.','active',target_id,now()))
            else:
                # An acknowledged alarm remains logged as an independent event.
                db.execute('UPDATE alarms SET state="resolved" WHERE room_id=? AND kind="technical" AND source_id=? AND state IN ("active","acknowledged")',(room_id,target_id))
        elif kind=='alarm_ack':
            alarm=db.execute('SELECT * FROM alarms WHERE id=? AND room_id=?',(target_id,room_id)).fetchone()
            if not alarm: raise ActionError('Alarma no encontrada.')
            if alarm['state']!='active': raise ActionError('La alarma no está activa.')
            if alarm['kind']=='clinical' and role=='BIOMED': raise ActionError('La ingeniería biomédica no confirma resultados clínicos.')
            if alarm['kind']=='technical' and role=='CLINICA':
                # Acknowledgement is permitted, while resolution requires biomédica.
                pass
            db.execute('UPDATE alarms SET state="acknowledged",acknowledged_at=?,acknowledged_by=? WHERE id=?',
                       (now(),actor,target_id))
            record(db,room_id,actor,role,'alarma_reconocida',f'Alarma {target_id} reconocida por {actor}. No implica resolución del incidente.')
        elif kind=='trigger_alarm':
            if value not in ('UCI','URG','HOSP'): raise ActionError('Unidad no válida para el escenario.')
            db.execute('INSERT INTO alarms(room_id,kind,unit,priority,message,state,created_at) VALUES(?,?,?,?,?,?,?)',
                       (room_id,'clinical',value,'alta',f'Descenso de SpO₂ simulado en {UNITS[value]}: 84 % (solo demostración).','active',now()))
            record(db,room_id,actor,role,'escenario',f'Escenario docente: alarma clínica simulada en {UNITS[value]}.')
        elif kind=='reset_room':
            if value!='CONFIRMAR': raise ActionError('Para reiniciar el aula es necesario confirmar.')
            for table in ('alarms','lab_orders','patients','devices','beds','events'):
                db.execute(f'DELETE FROM {table} WHERE room_id=?',(room_id,))
            seed_room(db,room_id)
            record(db,room_id,actor,role,'reinicio','El docente reinició los datos simulados del aula.')
    return {'ok':True}
