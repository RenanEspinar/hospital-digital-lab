"""Hospital Digital Lab — educational, synthetic-data only."""
from __future__ import annotations

import asyncio
import csv
import io
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from . import storage as db

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD','')
ROLES = {'HIS','CLINICA','LIS','BIOMED'}
STATIC = Path(__file__).parent / 'static'
_failures: dict[str,deque] = defaultdict(deque)
_events_rate: dict[str,deque] = defaultdict(deque)

@asynccontextmanager
async def lifespan(app):
    if len(ADMIN_PASSWORD)<12 or ADMIN_PASSWORD in {'cambiar_esta_clave','CHANGE_ME_12345'}:
        raise RuntimeError('ADMIN_PASSWORD debe tener al menos 12 caracteres y no ser la clave de ejemplo.')
    db.init_db()
    yield

app=FastAPI(title='Hospital Digital Lab', version='0.1.0', lifespan=lifespan,
            docs_url=None, redoc_url=None, openapi_url=None)

@app.middleware('http')
async def no_cache_security(request:Request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self' ws: wss:; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response

@app.get('/')
def index():
    return FileResponse(STATIC/'index.html')

@app.get('/static/{filename}')
def asset(filename:str):
    if filename not in {'app.js','styles.css'}: raise HTTPException(404)
    return FileResponse(STATIC/filename)

@app.get('/healthz')
def health():
    return {'status':'ok','application':'hospital-digital-lab'}

class LoginPayload(BaseModel):
    password: str = Field(min_length=1, max_length=200)

class JoinPayload(BaseModel):
    code: str = Field(min_length=8, max_length=12)
    name: str = Field(min_length=2,max_length=60)
    role: str

class NewRoom(BaseModel):
    title: str = Field(min_length=3,max_length=90)

class ActionRequest(BaseModel):
    kind: str
    target_id: int | None = None
    value: str | None = Field(default=None, max_length=60)


def authenticate(request:Request):
    header=request.headers.get('Authorization','')
    if not header.startswith('Bearer '): raise HTTPException(401,'Inicia sesión.')
    session=db.get_session(header[7:])
    if not session: raise HTTPException(401,'Sesión vencida o inválida.')
    return session


def authorize_room(session,code):
    room=db.find_room(code)
    if not room: raise HTTPException(404,'Aula no encontrada.')
    if session['role']!='DOCENTE' and session['room_id']!=room['id']:
        raise HTTPException(403,'No tienes acceso a esta aula.')
    return room


def limit(bucket,key,max_count,seconds):
    q=bucket[key]; t=time.monotonic()
    while q and t-q[0]>seconds:q.popleft()
    if len(q)>=max_count: return False
    q.append(t); return True

@app.post('/api/admin/login')
def teacher_login(payload:LoginPayload,request:Request):
    ip=request.client.host if request.client else 'unknown'
    if not limit(_failures,ip,10,300): raise HTTPException(429,'Demasiados intentos, inténtalo después.')
    if not secrets.compare_digest(payload.password,ADMIN_PASSWORD):
        raise HTTPException(401,'Contraseña incorrecta.')
    token=db.register_session(None,'Docente','DOCENTE')
    return {'token':token,'role':'DOCENTE','name':'Docente','expires_hours':12}

@app.post('/api/rooms')
def new_room(payload:NewRoom,session=Depends(authenticate)):
    if session['role']!='DOCENTE': raise HTTPException(403,'Solo el docente puede crear aulas.')
    return db.create_room(payload.title.strip())

@app.get('/api/rooms')
def rooms(session=Depends(authenticate)):
    if session['role']!='DOCENTE': raise HTTPException(403)
    return db.list_rooms()

@app.post('/api/join')
def join(payload:JoinPayload,request:Request):
    ip=request.client.host if request.client else 'unknown'
    if not limit(_failures,'join:'+ip,180,300): raise HTTPException(429,'Demasiados intentos.')
    if payload.role not in ROLES: raise HTTPException(400,'Rol no válido.')
    room=db.find_room(payload.code.strip().upper())
    if not room: raise HTTPException(404,'Código de aula incorrecto.')
    name=payload.name.strip()
    if len(name)<2 or any(ord(c)<32 for c in name): raise HTTPException(400,'Nombre no válido.')
    token=db.register_session(room['id'],name,payload.role)
    return {'token':token,'role':payload.role,'name':name,'room':room,'expires_hours':12}

@app.get('/api/state/{code}')
def state(code:str,session=Depends(authenticate)):
    room=authorize_room(session,code)
    return db.room_state(room['id'])

class RoomSockets:
    def __init__(self): self.clients=defaultdict(set)
    async def broadcast(self,room_id):
        for ws in list(self.clients[room_id]):
            try: await ws.send_json({'type':'refresh'})
            except Exception: self.clients[room_id].discard(ws)

connections=RoomSockets()

@app.post('/api/action/{code}')
async def take_action(code:str,payload:ActionRequest,session=Depends(authenticate)):
    room=authorize_room(session,code)
    if not limit(_events_rate,str(session['id']),45,60):
        raise HTTPException(429,'Demasiadas acciones, intenta de nuevo en un minuto.')
    try:
        output=db.action(room['id'],session['name'],session['role'],payload.kind,payload.target_id,payload.value)
    except db.ActionError as e:
        raise HTTPException(400,str(e))
    await connections.broadcast(room['id'])
    return output

@app.get('/api/export/{code}')
def export_csv(code:str,session=Depends(authenticate)):
    room=authorize_room(session,code)
    if session['role']!='DOCENTE':raise HTTPException(403)
    rows=db.export_events(room['id'])
    # Prevent spreadsheet-formula execution when exporting free-form participant names.
    for record in rows:
        for field in ('actor','message','payload'):
            value=str(record[field])
            if value.lstrip().startswith(('=','+','-','@')):
                record[field]="'"+value
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=['id','created_at','actor','role','type','message','payload'])
    writer.writeheader();writer.writerows(rows)
    return Response(output.getvalue(),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':f'attachment; filename="hospital-{code}-auditoria.csv"'})

@app.websocket('/ws/{code}')
async def websocket_room(ws:WebSocket,code:str):
    origin=ws.headers.get('origin')
    if origin and urlparse(origin).netloc.lower()!=ws.headers.get('host','').lower():
        await ws.close(code=1008); return
    await ws.accept()
    try:
        # Authenticate in the first WS message, not in its URL (proxy logs must not see tokens).
        hello=await asyncio.wait_for(ws.receive_json(), timeout=6)
    except Exception:
        await ws.close(code=1008); return
    if not isinstance(hello,dict) or hello.get('type')!='auth':
        await ws.close(code=1008); return
    session=db.get_session(hello.get('token',''))
    room=db.find_room(code)
    if not session or not room or (session['role']!='DOCENTE' and session['room_id']!=room['id']):
        await ws.close(code=1008); return
    connections.clients[room['id']].add(ws)
    try:
        await ws.send_json({'type':'connected'})
        while True:
            msg=await ws.receive_text()
            if msg=='ping': await ws.send_json({'type':'pong'})
    except WebSocketDisconnect:
        pass
    finally:
        connections.clients[room['id']].discard(ws)
