import os
os.environ.setdefault('ADMIN_PASSWORD','PASSWORD_DOCENTE_SOLO_PRUEBAS_2026')
from fastapi.testclient import TestClient
from app import main,storage

PASSWORD='PASSWORD_DOCENTE_SOLO_PRUEBAS_2026'

def setup(tmp_path):
    storage.DB_PATH=tmp_path/'hospital.db'
    main.ADMIN_PASSWORD=PASSWORD
    main._failed.clear();main._actions.clear()
    return TestClient(main.app)

def auth(client):
    r=client.post('/api/admin/login',json={'password':PASSWORD});assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def create(client,admin,title='Hospital docente'):
    r=client.post('/api/rooms',json={'title':title},headers=admin);assert r.status_code==200,r.text
    return r.json()['code']

def join(client,code,role):
    r=client.post('/api/join',json={'code':code,'name':'Equipo '+role,'role':role});assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def state(client,code,auth):
    r=client.get('/api/state/'+code,headers=auth);assert r.status_code==200,r.text
    return r.json()

def act(client,code,auth,kind,target_id=None,value=None,status=200):
    r=client.post('/api/action/'+code,json={'kind':kind,'target_id':target_id,'value':value},headers=auth)
    assert r.status_code==status,(kind,r.status_code,r.text)
    return r

def scenario(client,code,admin,key):
    act(client,code,admin,'scenario_spawn',value=key)
    return state(client,code,admin)['incidents'][0]['id']

def test_login_room_and_permissions(tmp_path):
    with setup(tmp_path) as c:
        admin=auth(c);code=create(c,admin);his=join(c,code,'HIS');clin=join(c,code,'CLINICA')
        assert state(c,code,his)['metrics']['beds_total']==12
        assert len(state(c,code,his)['devices'])==10
        assert state(c,code,his)['settings']['mode']=='manual'
        assert c.get('/api/rooms',headers=his).status_code==403
        assert c.post('/api/rooms',headers=his,json={'title':'No puedo'}).status_code==403
        act(c,code,his,'scenario_spawn',value='desaturacion',status=400)
        act(c,code,his,'lab_order',value='Potasio',status=400)
        code2=create(c,admin,'Otra aula')
        assert c.get('/api/state/'+code2,headers=clin).status_code==403
        assert c.post('/api/action/'+code2,headers=his,json={'kind':'admit'}).status_code==403

def test_emergency_coordination_and_audit(tmp_path):
    with setup(tmp_path) as c:
        admin=auth(c);code=create(c,admin);clin=join(c,code,'CLINICA');bio=join(c,code,'BIOMED')
        iid=scenario(c,code,admin,'desaturacion')
        s=state(c,code,admin);assert s['metrics']['incidents_active']==1
        assert s['metrics']['tasks_pending']==2
        alarm=next(a for a in s['alarms'] if a['state']=='active')
        dev=next(d for d in s['devices'] if d['unit']=='UCI')
        act(c,code,bio,'alarm_ack',alarm['id'],status=400)
        act(c,code,clin,'alarm_ack',alarm['id'])
        assert state(c,code,admin)['metrics']['tasks_pending']==1
        act(c,code,bio,'device_check',dev['id'])
        s=state(c,code,admin)
        assert s['metrics']['incidents_active']==0
        assert s['metrics']['incidents_resolved']==1
        assert {x['state'] for x in s['tasks'] if x['incident_id']==iid}=={'completed'}
        assert c.get('/api/export/'+code,headers=admin).status_code==200
        assert c.get('/api/export/'+code,headers=clin).status_code==403

def test_biomedical_failure(tmp_path):
    with setup(tmp_path) as c:
        admin=auth(c);code=create(c,admin);bio=join(c,code,'BIOMED');clin=join(c,code,'CLINICA')
        scenario(c,code,admin,'falla_equipo');s=state(c,code,admin)
        device=next(d for d in s['devices'] if d['state']=='en_falla');a=next(a for a in s['alarms'] if a['kind']=='technical' and a['state']=='active')
        act(c,code,bio,'device_status',device['id'],'operativo')
        # La recuperación NO sustituye el reconocimiento por Clínica.
        s=state(c,code,admin)
        assert s['metrics']['incidents_active']==1
        act(c,code,clin,'alarm_ack',a['id'])
        s=state(c,code,admin)
        assert s['metrics']['incidents_active']==0
        assert s['metrics']['devices_operational']==s['metrics']['devices_total']

def test_patient_admission_clinical_reception(tmp_path):
    with setup(tmp_path) as c:
        a=auth(c);code=create(c,a);his=join(c,code,'HIS');clin=join(c,code,'CLINICA')
        scenario(c,code,a,'llegada_masiva');s=state(c,code,a)
        arr=next(v for v in s['arrivals'] if v['state']=='waiting');bed=next(v for v in s['beds'] if v['patient_id'] is None)
        act(c,code,clin,'arrival_receive',arr['id'],status=400)
        act(c,code,his,'admit_arrival',arr['id'],str(bed['id']))
        s=state(c,code,a);assert s['metrics']['tasks_pending']==1
        assert any(p['name']==arr['name'] for p in s['patients'])
        act(c,code,clin,'arrival_receive',arr['id'])
        assert state(c,code,a)['metrics']['incidents_active']==0
        patient=next(p for p in state(c,code,a)['patients'] if p['name']==arr['name'])
        act(c,code,his,'discharge',patient['id'])
        assert state(c,code,a)['metrics']['beds_occupied']==3

def test_critical_lab_path(tmp_path):
    with setup(tmp_path) as c:
        a=auth(c);code=create(c,a);lis=join(c,code,'LIS');clin=join(c,code,'CLINICA')
        scenario(c,code,a,'resultado_critico');s=state(c,code,a)
        order=next(o for o in s['orders'] if o['state']=='received')
        act(c,code,lis,'lab_result',order['id'],'critical')
        s=state(c,code,a);assert s['metrics']['tasks_pending']==1
        alarm=next(z for z in s['alarms'] if z['kind']=='clinical' and z['source_id']==order['id'])
        act(c,code,clin,'alarm_ack',alarm['id'])
        assert state(c,code,a)['metrics']['incidents_active']==0

def test_farmacia_y_imagenes(tmp_path):
    with setup(tmp_path) as c:
        a=auth(c);code=create(c,a);far=join(c,code,'FARMACIA');img=join(c,code,'IMAGENES');clin=join(c,code,'CLINICA')
        scenario(c,code,a,'desabastecimiento');s=state(c,code,a);o=s['med_orders'][0]
        act(c,code,far,'med_dispense',o['id'])
        act(c,code,clin,'med_receive',o['id'])
        assert state(c,code,a)['metrics']['incidents_active']==0
        scenario(c,code,a,'imagen_urgente');o=state(c,code,a)['imaging_orders'][0]
        act(c,code,img,'imaging_result',o['id'],'Informe A')
        act(c,code,clin,'imaging_review',o['id'])
        assert state(c,code,a)['metrics']['incidents_active']==0

def test_auto_engine_and_pause(tmp_path):
    with setup(tmp_path) as c:
        a=auth(c);code=create(c,a);room=storage.find_room(code)
        act(c,code,a,'simulation_config',value='{"mode":"auto","interval_seconds":30,"difficulty":"normal"}')
        with storage.connection(write=True) as db:
            db.execute('UPDATE simulation_settings SET next_event_at=? WHERE room_id=?',('2000-01-01T00:00:00+00:00',room['id']))
        assert room['id'] in storage.auto_tick()
        assert state(c,code,a)['metrics']['incidents_active']==1
        act(c,code,a,'simulation_config',value='{"mode":"paused","interval_seconds":30,"difficulty":"normal"}')
        assert storage.auto_tick()==[]
        assert state(c,code,a)['settings']['next_event_at'] is None

def test_reset_and_legacy_compatibility(tmp_path):
    with setup(tmp_path) as c:
        a=auth(c);code=create(c,a)
        scenario(c,code,a,'llegada_masiva')
        assert state(c,code,a)['arrivals']
        act(c,code,a,'reset_room',value='CONFIRMAR')
        s=state(c,code,a)
        assert s['metrics']['beds_occupied']==3 and s['metrics']['incidents_active']==0
        assert s['settings']['mode']=='manual'
        storage.init_db()  # migration repeatedly safe
        assert state(c,code,a)['metrics']['beds_total']==12

def test_websocket_and_assets(tmp_path):
    with setup(tmp_path) as c:
        a=auth(c);code=create(c,a)
        tok=join(c,code,'HIS')['Authorization'].split()[-1]
        with c.websocket_connect('/ws/'+code,headers={'origin':'http://testserver'}) as ws:
            ws.send_json({'type':'auth','token':tok})
            assert ws.receive_json()['type']=='connected'
            scenario(c,code,a,'llegada_masiva')
            assert ws.receive_json()['type']=='refresh'
        assert c.get('/healthz').json()['version']=='0.2.2'
        assert c.get('/static/app.js').status_code==200
        assert c.get('/static/styles.css').status_code==200
        assert c.get('/static/no.js').status_code==404
