"""Regresión de aulas híbridas sobre SQLite real aislado por prueba."""
import json
import os
os.environ.setdefault('ADMIN_PASSWORD', 'PASSWORD_DOCENTE_SOLO_PRUEBAS_2026')
from app import bots, main, storage
from tests_helper import harness


def tick_all(room, rounds=20):
    """Adelanta solo los temporizadores sintéticos en la DB de pruebas."""
    for _ in range(rounds):
        with storage.connection(write=True) as cx:
            cx.execute("UPDATE role_staffing SET next_action_at='2000-01-01T00:00:00+00:00' WHERE mode='auto' AND room_id=?", (room,))
        bots.auto_staff_tick()


def test_three_students_autonomous_dependencies(tmp_path):
    with harness(tmp_path) as (c,a,code):
        room=storage.find_room(code)['id']
        config={'human_roles':['HIS','CLINICA','LIS'],'pace_seconds':10}
        a.act('simulation_staffing',value=json.dumps(config))
        s=a.state()
        assert [x['role'] for x in s['staffing'] if x['mode']=='auto']==['BIOMED','FARMACIA','IMAGENES']
        assert s['settings']['mode']=='manual'  # Bots y generador de incidentes independientes.
        assert c.post('/api/join',json={'code':code,'name':'Nuevo de Farmacia','role':'FARMACIA'}).status_code==409
        a.act('scenario_spawn',value='falla_equipo')
        tick_all(room,1)
        s=a.state()
        assert s['metrics']['incidents_active']==1  # La intervención clínica humana sigue pendiente.
        assert s['metrics']['devices_operational']==s['metrics']['devices_total']
        alarm=next(z for z in s['alarms'] if z['kind']=='technical' and z['state']=='active')
        a.act('alarm_ack',alarm['id'])
        assert a.state()['metrics']['incidents_active']==0
        a.act('scenario_spawn',value='desaturacion')
        tick_all(room,1)
        s=a.state()
        assert s['metrics']['tasks_pending']==1
        alarm=next(z for z in s['alarms'] if z['kind']=='clinical' and z['state']=='active')
        a.act('alarm_ack',alarm['id'])
        assert a.state()['metrics']['incidents_active']==0
        a.act('scenario_spawn',value='desabastecimiento')
        tick_all(room,1)
        s=a.state()
        assert s['med_orders'][0]['state']=='dispensed'
        assert s['metrics']['tasks_pending']==1
        a.act('med_receive',s['med_orders'][0]['id'])
        assert a.state()['metrics']['incidents_active']==0
        a.act('scenario_spawn',value='imagen_urgente')
        tick_all(room,1)
        s=a.state()
        assert s['imaging_orders'][0]['state']=='reported'
        assert s['metrics']['tasks_pending']==1
        a.act('imaging_review',s['imaging_orders'][0]['id'])
        assert a.state()['metrics']['incidents_active']==0
        events=a.state()['events']
        auto=[e for e in events if e['actor'].startswith('AUTO · ')]
        assert len(auto)>=4
        assert all(e['payload'].get('automated') is True for e in auto)
        audit=c.get('/api/export/'+code,headers=a.auth).text
        assert 'AUTO · ' in audit


def test_two_students_virtual_admissions(tmp_path):
    with harness(tmp_path) as (c,a,code):
        room=storage.find_room(code)['id']
        a.act('simulation_staffing',value=json.dumps({'human_roles':['CLINICA','LIS'],'pace_seconds':15}))
        a.act('scenario_spawn',value='llegada_masiva')
        tick_all(room,1)
        s=a.state()
        assert s['arrivals'][0]['state']=='admitted'
        assert s['metrics']['incidents_active']==1
        assert s['metrics']['tasks_pending']==1
        a.act('arrival_receive',s['arrivals'][0]['id'])
        assert a.state()['metrics']['incidents_active']==0
        # Un alumno en LIS NO es sustituido por el bot.
        a.act('scenario_spawn',value='resultado_critico')
        tick_all(room,5)
        s=a.state()
        assert s['metrics']['incidents_active']==1
        assert s['orders'][0]['state']=='received'
        a.act('lab_result',s['orders'][0]['id'],'critical')
        alarm=next(z for z in a.state()['alarms'] if z['kind']=='clinical' and z['state']=='active')
        a.act('alarm_ack',alarm['id'])
        assert a.state()['metrics']['incidents_active']==0


def test_four_students_and_paused_incident_generator(tmp_path):
    with harness(tmp_path) as (c,a,code):
        room=storage.find_room(code)['id']
        a.act('simulation_staffing',value=json.dumps({'human_roles':['HIS','CLINICA','LIS','BIOMED'],'pace_seconds':30}))
        a.act('simulation_config',value=json.dumps({'mode':'paused','interval_seconds':30,'difficulty':'normal'}))
        a.act('scenario_spawn',value='imagen_urgente')
        tick_all(room,1)
        s=a.state()
        assert s['imaging_orders'][0]['state']=='reported'
        assert s['settings']['mode']=='paused'
        assert s['metrics']['incidents_active']==1
        a.act('imaging_review',s['imaging_orders'][0]['id'])
        assert a.state()['metrics']['incidents_active']==0


def test_default_staffing_invalid_config_and_active_session_block(tmp_path):
    with harness(tmp_path) as (c,a,code):
        s=a.state()
        assert len(s['staffing'])==6 and all(x['mode']=='human' for x in s['staffing'])
        lis=c.post('/api/join',json={'code':code,'name':'Javier LIS','role':'LIS'}).json()['token']
        a.act('simulation_staffing',value='{"human_roles":[],"pace_seconds":15}',expected=400)
        assert all(x['mode']=='human' for x in a.state()['staffing'])
        a.act('simulation_staffing',value=json.dumps({'human_roles':['CLINICA'],'pace_seconds':10}))
        r=c.post('/api/action/'+code,headers={'Authorization':'Bearer '+lis},json={'kind':'sample_received','target_id':123})
        assert r.status_code==403
        # Otra aula queda sin bots.
        other=c.post('/api/rooms',headers=a.auth,json={'title':'Aula independiente'}).json()['code']
        other_state=c.get('/api/state/'+other,headers=a.auth).json()
        assert all(x['mode']=='human' for x in other_state['staffing'])
        assert all(x['mode']=='human' for x in a.state()['staffing'] if x['role']=='CLINICA')
        storage.init_db()  # Migración idempotente.
        assert len(a.state()['staffing'])==6


def test_virtual_general_queue_processing(tmp_path):
    with harness(tmp_path) as (c,a,code):
        room=storage.find_room(code)['id']
        a.act('simulation_staffing',value=json.dumps({'human_roles':['HIS','CLINICA','LIS'],'pace_seconds':10}))
        patient=a.state()['patients'][0]['id']
        a.act('med_order',patient,'Insumo A')
        a.act('imaging_order',patient,'Radiografía simulada')
        tick_all(room,2)
        s=a.state()
        assert s['med_orders'][0]['state']=='dispensed'
        assert s['imaging_orders'][0]['state']=='reported'
        assert s['metrics']['incidents_active']==0
