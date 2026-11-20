"""API de Hospital Digital Lab v0.3: solo simulación, no uso clínico."""
from __future__ import annotations
import asyncio,csv,io,os,secrets,time
from collections import defaultdict,deque
from contextlib import asynccontextmanager,suppress
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI,HTTPException,Request,WebSocket,WebSocketDisconnect,Depends
from fastapi.responses import FileResponse,Response
from pydantic import BaseModel,Field
from . import storage as db
from . import bots

ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD','')
STATIC=Path(__file__).parent/'static'
_failed=defaultdict(deque);_actions=defaultdict(deque)

def limited(bucket,key,max_count,seconds):
    q=bucket[key];t=time.monotonic()
    while q and t-q[0]>seconds:q.popleft()
    if len(q)>=max_count:return False
    q.append(t);return True

class Sockets:
    def __init__(self):self.clients=defaultdict(set)
    async def send(self,room):
        for ws in list(self.clients[room]):
            try:await ws.send_json({'type':'refresh'})
            except Exception:self.clients[room].discard(ws)
connections=Sockets()

async def auto_loop():
    while True:
        await asyncio.sleep(5)
        try:
            generated=await asyncio.to_thread(db.auto_tick)
            processed=await asyncio.to_thread(bots.auto_staff_tick)
            for rid in set(generated+processed):await connections.send(rid)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception('Fallo del motor: %s',e)

@asynccontextmanager
async def lifespan(app):
    if len(ADMIN_PASSWORD)<12 or ADMIN_PASSWORD in ('cambiar_esta_clave','CHANGE_ME_12345','CAMBIAR_A_CONTRASENA_SEGURA'):
        raise RuntimeError('Configura una contraseña docente fuerte en .env.')
    db.init_db()
    work=asyncio.create_task(auto_loop())
    try:yield
    finally:
        work.cancel()
        with suppress(asyncio.CancelledError):await work

app=FastAPI(title='Hospital Digital Lab',version='0.3.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

@app.middleware('http')
async def security(request:Request,call_next):
    resp=await call_next(request)
    resp.headers['Cache-Control']='no-store'
    resp.headers['X-Content-Type-Options']='nosniff'
    resp.headers['X-Frame-Options']='DENY'
    resp.headers['Referrer-Policy']='no-referrer'
    resp.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self' ws: wss:; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return resp

@app.get('/')
def index():return FileResponse(STATIC/'index.html')
@app.get('/static/{name}')
def static(name:str):
    if name not in ('app.js','styles.css'):raise HTTPException(404)
    return FileResponse(STATIC/name)
@app.get('/healthz')
def health():return {'status':'ok','application':'hospital-digital-lab','version':'0.3.0'}

class Login(BaseModel):password:str=Field(min_length=1,max_length=200)
class Join(BaseModel):
    code:str=Field(min_length=8,max_length=12)
    name:str=Field(min_length=2,max_length=60)
    role:str
class NewRoom(BaseModel):title:str=Field(min_length=3,max_length=90)
class Action(BaseModel):
    kind:str=Field(max_length=60)
    target_id:int|None=None
    value:str|None=Field(default=None,max_length=600)

def authenticate(req:Request):
    bearer=req.headers.get('Authorization','')
    if not bearer.startswith('Bearer '):raise HTTPException(401,'Inicia sesión.')
    session=db.get_session(bearer[7:])
    if not session:raise HTTPException(401,'Sesión vencida o inválida.')
    return session

def check_room(session,code):
    room=db.find_room(code)
    if not room:raise HTTPException(404,'Aula inexistente.')
    if session['role']!='DOCENTE' and session['room_id']!=room['id']:raise HTTPException(403,'No perteneces a esta aula.')
    return room

@app.post('/api/admin/login')
def login(p:Login,req:Request):
    ip=req.client.host if req.client else 'unknown'
    if not limited(_failed,'admin:'+ip,10,300):raise HTTPException(429,'Demasiados intentos.')
    if not secrets.compare_digest(p.password,ADMIN_PASSWORD):raise HTTPException(401,'Contraseña incorrecta.')
    return {'token':db.register_session(None,'Docente','DOCENTE'),'role':'DOCENTE','name':'Docente','expires_hours':12}
@app.post('/api/join')
def join(p:Join,req:Request):
    ip=req.client.host if req.client else 'unknown'
    if not limited(_failed,'join:'+ip,120,300):raise HTTPException(429,'Demasiados intentos.')
    if p.role not in db.ROLES:raise HTTPException(400,'Rol no válido.')
    room=db.find_room(p.code.strip().upper())
    if not room:raise HTTPException(404,'Código de aula incorrecto.')
    if db.is_automated_role(room['id'],p.role):raise HTTPException(409,'Esta área está asignada a un agente automático. Selecciona un rol humano o pide al docente que cambie la configuración.')
    name=p.name.strip()
    if len(name)<2 or any(ord(c)<32 for c in name):raise HTTPException(400,'Nombre no válido.')
    return {'token':db.register_session(room['id'],name,p.role),'role':p.role,'name':name,'room':room,'expires_hours':12}
@app.post('/api/rooms')
def create(p:NewRoom,s=Depends(authenticate)):
    if s['role']!='DOCENTE':raise HTTPException(403)
    return db.create_room(p.title.strip())
@app.get('/api/rooms')
def rooms(s=Depends(authenticate)):
    if s['role']!='DOCENTE':raise HTTPException(403)
    return db.list_rooms()
@app.get('/api/state/{code}')
def state(code:str,s=Depends(authenticate)):
    room=check_room(s,code)
    return db.room_state(room['id'])
@app.post('/api/action/{code}')
async def action(code:str,p:Action,s=Depends(authenticate)):
    room=check_room(s,code)
    if s['role']!='DOCENTE' and db.is_automated_role(room['id'],s['role']):raise HTTPException(403,'Esta estación está ahora automatizada. Consulta al docente.')
    if not limited(_actions,str(s['id']),60,60):raise HTTPException(429,'Demasiadas acciones.')
    try:output=await asyncio.to_thread(db.action,room['id'],s['name'],s['role'],p.kind,p.target_id,p.value)
    except (db.ActionError,ValueError) as e:raise HTTPException(400,str(e))
    await connections.send(room['id'])
    return output
@app.get('/api/export/{code}')
def export(code:str,s=Depends(authenticate)):
    room=check_room(s,code)
    if s['role']!='DOCENTE':raise HTTPException(403)
    records=db.export_events(room['id'])
    for row in records:
        for col in ('actor','message','payload'):
            val=str(row[col]);row[col]="'"+val if val.lstrip().startswith(('=','+','-','@')) else val
    f=io.StringIO();writer=csv.DictWriter(f,fieldnames=['id','created_at','actor','role','type','message','payload']);writer.writeheader();writer.writerows(records)
    return Response(f.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="hospital-{code}-auditoria.csv"'})
@app.websocket('/ws/{code}')
async def socket(ws:WebSocket,code:str):
    origin=ws.headers.get('origin')
    if origin and urlparse(origin).netloc.lower()!=ws.headers.get('host','').lower():
        await ws.close(code=1008);return
    await ws.accept()
    try:hello=await asyncio.wait_for(ws.receive_json(),timeout=6)
    except Exception:
        await ws.close(code=1008);return
    if not isinstance(hello,dict) or hello.get('type')!='auth':
        await ws.close(code=1008);return
    session=db.get_session(hello.get('token',''))
    room=db.find_room(code)
    if not session or not room or (session['role']!='DOCENTE' and session['room_id']!=room['id']):
        await ws.close(code=1008);return
    connections.clients[room['id']].add(ws)
    try:
        await ws.send_json({'type':'connected'})
        while True:
            msg=await ws.receive_text()
            if msg=='ping':await ws.send_json({'type':'pong'})
    except WebSocketDisconnect:pass
    finally:connections.clients[room['id']].discard(ws)
