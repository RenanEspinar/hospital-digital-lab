from contextlib import contextmanager
from fastapi.testclient import TestClient
from app import main,storage
PASSWORD='PASSWORD_DOCENTE_SOLO_PRUEBAS_2026'

class Actor:
    def __init__(self,c,code,token):
        self.c,self.code,self.auth=c,code,{'Authorization':'Bearer '+token}
    def act(self,kind,target=None,value=None,expected=200):
        r=self.c.post('/api/action/'+self.code,headers=self.auth,json={'kind':kind,'target_id':target,'value':value})
        assert r.status_code==expected,(kind,r.status_code,r.text)
        return r.json() if expected==200 else r
    def state(self):
        r=self.c.get('/api/state/'+self.code,headers=self.auth)
        assert r.status_code==200,r.text
        return r.json()

@contextmanager
def harness(tmp_path):
    storage.DB_PATH=tmp_path/'test-hybrid.db'
    main.ADMIN_PASSWORD=PASSWORD
    main._failed.clear();main._actions.clear()
    with TestClient(main.app) as c:
        r=c.post('/api/admin/login',json={'password':PASSWORD})
        assert r.status_code==200,r.text
        token=r.json()['token']
        auth={'Authorization':'Bearer '+token}
        r=c.post('/api/rooms',headers=auth,json={'title':'Hospital híbrido pruebas'})
        assert r.status_code==200,r.text
        code=r.json()['code']
        yield c,Actor(c,code,token),code
