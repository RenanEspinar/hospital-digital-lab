"""Cobertura por ausencia, fichas de equipos y registros de práctica v0.3.1."""
import json
from datetime import datetime,timedelta,timezone
from app import storage, bots
from tests_helper import harness


def actor_token(client,code,role,name):
    r=client.post('/api/join',json={'code':code,'role':role,'name':name})
    assert r.status_code==200, r.text
    return r.json()['token']


def role_state(state,role):
    return next(x for x in state['staffing'] if x['role']==role)


def test_presence_and_auto_cover_then_student_rejoins(tmp_path):
    with harness(tmp_path) as (c,a,code):
        room=storage.find_room(code)['id']
        a.act('simulation_staffing',value=json.dumps({'human_roles':['CLINICA','LIS','BIOMED'],'pace_seconds':10}))
        token=actor_token(c,code,'LIS','Javier')
        student={'Authorization':'Bearer '+token}
        assert c.get('/api/state/'+code,headers=student).status_code==200
        state=a.state()
        assert state['participants']['LIS']==1
        assert any(x['name']=='Javier' and x['online'] for x in state['student_sessions'])
        a.act('coverage_config',value='on')
        with storage.connection(write=True) as db:
            past=(datetime.now(timezone.utc)-timedelta(seconds=125)).isoformat(timespec='seconds')
            db.execute('UPDATE sessions SET last_seen_at=? WHERE room_id=? AND role=?',(past,room,'LIS'))
            db.execute('UPDATE simulation_settings SET coverage_started_at=? WHERE room_id=?',(past,room))
        assert room in storage.absence_tick()
        state=a.state()
        assert role_state(state,'LIS')['mode']=='auto'
        assert role_state(state,'LIS')['auto_reason']=='absence'
        assert role_state(state,'FARMACIA')['auto_reason']==''  # Manual bot unaffected.
        assert any(e['type']=='cobertura_ausencia' for e in state['events'])
        # Al recuperar sesión, el alumno recupera su estación sin intervención docente.
        r=c.get('/api/state/'+code,headers=student)
        assert r.status_code==200
        assert role_state(a.state(),'LIS')['mode']=='human'
        assert any(e['type']=='cobertura_finalizada' for e in a.state()['events'])
        # Un bot manual nunca debe permitir recuperar control con credenciales antiguas.
        a.act('staffing_role',value=json.dumps({'role':'LIS','mode':'auto'}))
        assert c.post('/api/action/'+code,headers=student,json={'kind':'sample_received','target_id':1}).status_code==403
        assert c.post('/api/join',json={'code':code,'role':'LIS','name':'Otro estudiante'}).status_code==409
        a.act('staffing_role',value=json.dumps({'role':'LIS','mode':'human'}))
        assert role_state(a.state(),'LIS')['mode']=='human'


def test_teacher_manual_auto_and_disable_auto_coverage(tmp_path):
    with harness(tmp_path) as (c,a,code):
        room=storage.find_room(code)['id']
        a.act('staffing_role',value=json.dumps({'role':'IMAGENES','mode':'auto'}))
        a.act('coverage_config',value='on')
        with storage.connection(write=True) as db:
            past=(datetime.now(timezone.utc)-timedelta(seconds=130)).isoformat(timespec='seconds')
            db.execute('UPDATE simulation_settings SET coverage_started_at=? WHERE room_id=?',(past,room))
        storage.absence_tick()
        state=a.state()
        assert role_state(state,'IMAGENES')['mode']=='auto' and role_state(state,'IMAGENES')['auto_reason']==''
        assert role_state(state,'BIOMED')['auto_reason']=='absence'
        a.act('coverage_config',value='off')
        state=a.state()
        assert role_state(state,'IMAGENES')['mode']=='auto'
        assert role_state(state,'BIOMED')['mode']=='human'
        assert state['settings']['auto_cover_absences']==0


def test_equipment_realistic_fictional_records_and_permissions(tmp_path):
    with harness(tmp_path) as (c,a,code):
        initial=a.state()
        assert len(initial['devices'])==10
        equipment=initial['devices'][0]
        assert equipment['manufacturer']=='Aurelia MedTech'
        assert equipment['model']=='Vigia MX-8'
        assert equipment['asset_tag'].startswith('BIO-')
        bm={'Authorization':'Bearer '+actor_token(c,code,'BIOMED','Silvia')}
        lis={'Authorization':'Bearer '+actor_token(c,code,'LIS','Javier')}
        path='/api/action/'+code
        update={'manufacturer':'Fábrica Ficticia de Equipos','model':'Modelo SIM-3','serial_number':'FIC-2026-8888',
                'last_maintenance':'2026-11-01','next_maintenance':'2027-05-01','notes':'Verificación hipotética 2026.'}
        r=c.post(path,headers=bm,json={'kind':'device_update','target_id':equipment['id'],'value':json.dumps(update)})
        assert r.status_code==200,r.text
        assert next(d for d in a.state()['devices'] if d['id']==equipment['id'])['model']=='Modelo SIM-3'
        assert c.post(path,headers=lis,json={'kind':'device_update','target_id':equipment['id'],'value':json.dumps(update)}).status_code==400
        bad=dict(update,last_maintenance='2026-42-99')
        assert c.post(path,headers=bm,json={'kind':'device_update','target_id':equipment['id'],'value':json.dumps(bad)}).status_code==400
        new={'name':'Ventilador ficticio V-202','type':'Ventilador','unit':'UCI','manufacturer':'Cobalto Med','model':'Air SIM',
             'asset_tag':'BIO-999','risk_class':'Didáctico','notes':'No conectar a pacientes.'}
        assert c.post(path,headers=bm,json={'kind':'device_create','value':json.dumps(new)}).status_code==200
        assert len(a.state()['devices'])==11
        # Registrar medición sintética vinculada al activo y validar visibilidad en auditoría.
        entry={'subject':'Inspección del monitor','details':'Se registró prueba de simulación únicamente.',
               'measurement_value':98.2,'measurement_unit':'%','device_id':equipment['id']}
        assert c.post(path,headers=bm,json={'kind':'practice_entry','value':json.dumps(entry)}).status_code==200
        assert len(a.state()['practice_entries'])==1
        assert a.state()['practice_entries'][0]['measurement_value']==98.2
        assert a.state()['practice_entries'][0]['actor']=='Silvia'
        assert c.post(path,headers=lis,json={'kind':'practice_entry','value':json.dumps(entry)}).status_code==400
        entry.update(device_id=None)
        assert c.post(path,headers=lis,json={'kind':'practice_entry','value':json.dumps(entry)}).status_code==200
        assert len(a.state()['practice_entries'])==2
        assert 'Inspección del monitor' in c.get('/api/export/'+code,headers=a.auth).text
        a.act('reset_room',value='CONFIRMAR')
        assert not a.state()['practice_entries']
        assert len(a.state()['devices'])==10


def test_multiple_rooms_independent_assets_and_staff(tmp_path):
    with harness(tmp_path) as (c,a,code):
        r=c.post('/api/rooms',headers=a.auth,json={'title':'Otra aula independiente'}).json()
        a.act('staffing_role',value=json.dumps({'role':'BIOMED','mode':'auto'}))
        assert role_state(a.state(),'BIOMED')['mode']=='auto'
        other=c.get('/api/state/'+r['code'],headers=a.auth).json()
        assert role_state(other,'BIOMED')['mode']=='human'
        assert other['devices'][0]['serial_number']!=a.state()['devices'][0]['serial_number']
