import os
from pathlib import Path

os.environ.setdefault('ADMIN_PASSWORD','CLAVE_DE_PRUEBAS_NO_REAL_2026')
from fastapi.testclient import TestClient
from app import main, storage


def setup_test(tmp_path):
    storage.DB_PATH=tmp_path/'hospital-test.db'
    main.ADMIN_PASSWORD='CLAVE_DE_PRUEBAS_NO_REAL_2026'
    main._failures.clear()
    main._events_rate.clear()
    return TestClient(main.app)


def teacher(client):
    r=client.post('/api/admin/login',json={'password':'CLAVE_DE_PRUEBAS_NO_REAL_2026'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}


def join(client,code,role):
    r=client.post('/api/join',json={'code':code,'name':'Grupo de prueba '+role,'role':role})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']},r.json()['token']


def state(client,code,auth):
    r=client.get('/api/state/'+code,headers=auth)
    assert r.status_code==200,r.text
    return r.json()


def action(client,code,auth,kind,target_id=None,value=None,status=200):
    r=client.post('/api/action/'+code,headers=auth,json={'kind':kind,'target_id':target_id,'value':value})
    assert r.status_code==status,(r.status_code,r.text)
    return r


def test_his_to_lis_alert_workflow(tmp_path):
    with setup_test(tmp_path) as client:
        th=teacher(client)
        create=client.post('/api/rooms',headers=th,json={'title':'Clase 5 A'});assert create.status_code==200
        code=create.json()['code']
        his,_=join(client,code,'HIS');clin,_=join(client,code,'CLINICA');lis,_=join(client,code,'LIS');bio,_=join(client,code,'BIOMED')
        initial=state(client,code,th)
        assert len(initial['patients'])==3
        free=next(b['id'] for b in initial['beds'] if not b['patient_id'])
        action(client,code,his,'admit',free)
        post_admit=state(client,code,clin)
        assert len(post_admit['patients'])==4
        patient=post_admit['patients'][-1]
        action(client,code,clin,'lab_order',patient['id'],'Potasio')
        s=state(client,code,lis);order=s['orders'][0]
        assert order['state']=='requested'
        action(client,code,lis,'sample_received',order['id'])
        action(client,code,lis,'lab_result',order['id'],'critical')
        s=state(client,code,th)
        assert s['metrics']['alarms_active']==1
        assert s['orders'][0]['result_value']==6.3
        alarm=s['alarms'][0]
        action(client,code,bio,'alarm_ack',alarm['id'],status=400) # clinical alert, wrong role
        action(client,code,clin,'alarm_ack',alarm['id'])
        assert state(client,code,th)['metrics']['alarms_active']==0
        device=s['devices'][0]
        action(client,code,bio,'device_status',device['id'],'en_falla')
        assert state(client,code,clin)['metrics']['devices_operational']==len(s['devices'])-1
        action(client,code,bio,'device_status',device['id'],'operativo')
        assert state(client,code,th)['metrics']['devices_operational']==len(s['devices'])
        export=client.get('/api/export/'+code,headers=th)
        assert export.status_code==200 and 'resultado_lis' in export.text
        assert client.get('/api/export/'+code,headers=his).status_code==403


def test_isolation_and_permissions(tmp_path):
    with setup_test(tmp_path) as client:
        th=teacher(client)
        first=client.post('/api/rooms',headers=th,json={'title':'Clase 5 Aula 1'}).json()['code']
        second=client.post('/api/rooms',headers=th,json={'title':'Clase 5 Aula 2'}).json()['code']
        a,_=join(client,first,'HIS')
        b,_=join(client,second,'LIS')
        assert client.get('/api/state/'+second,headers=a).status_code==403
        assert client.post('/api/action/'+second,headers=a,json={'kind':'reset_room','value':'CONFIRMAR'}).status_code==403
        assert client.post('/api/rooms',headers=a,json={'title':'Ataque'}).status_code==403
        assert client.get('/api/rooms',headers=b).status_code==403
        free=next(x['id'] for x in state(client,first,th)['beds'] if x['patient_id'] is None)
        action(client,first,a,'admit',free)
        assert len(state(client,first,th)['patients'])==4
        assert len(state(client,second,th)['patients'])==3
        action(client,first,th,'trigger_alarm',value='UCI')
        assert state(client,first,th)['metrics']['alarms_active']==1
        assert state(client,second,th)['metrics']['alarms_active']==0
        action(client,first,th,'reset_room',value='CONFIRMAR')
        assert len(state(client,first,th)['patients'])==3


def test_websockets_receive_room_refresh(tmp_path):
    with setup_test(tmp_path) as client:
        th=teacher(client)
        code=client.post('/api/rooms',headers=th,json={'title':'Clase en vivo'}).json()['code']
        auth,token=join(client,code,'HIS')
        with client.websocket_connect('/ws/'+code,headers={'origin':'http://testserver'}) as ws:
            ws.send_json({'type':'auth','token':token})
            assert ws.receive_json()['type']=='connected'
            first=state(client,code,th)
            free=next(x['id'] for x in first['beds'] if not x['patient_id'])
            action(client,code,auth,'admit',free)
            assert ws.receive_json()['type']=='refresh'


def test_no_real_patient_fields(tmp_path):
    with setup_test(tmp_path) as client:
        th=teacher(client)
        room=client.post('/api/rooms',headers=th,json={'title':'Ejemplo'}).json()
        code=room['code']; his,_=join(client,code,'HIS')
        free=next(b['id'] for b in state(client,code,th)['beds'] if not b['patient_id'])
        r=client.post('/api/action/'+code,headers=his,json={'kind':'admit','target_id':free,'value':'Nombre real de paciente'})
        assert r.status_code==200
        assert all('Nombre real' not in p['name'] for p in state(client,code,th)['patients'])


def test_health(tmp_path):
    with setup_test(tmp_path) as client:
        assert client.get('/healthz').json()['status']=='ok'
        assert 'HOSPITAL DIGITAL' in client.get('/').text
        assert client.get('/static/app.js').status_code==200
        assert client.get('/static/styles.css').status_code==200
        assert client.get('/static/unknown.js').status_code==404
