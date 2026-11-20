"""Agentes hospitalarios ficticios: ejecutan únicamente acciones propias de roles auto.
No proporcionan decisiones clínicas ni controlan dispositivos reales.
"""
from __future__ import annotations
import random
from . import storage as db

LABELS={
    'HIS':'HIS', 'CLINICA':'Clínica', 'LIS':'LIS',
    'BIOMED':'Biomédica', 'FARMACIA':'Farmacia', 'IMAGENES':'Imagenología'
}

def choose_job(room,role):
    """Una acción por turno; tareas de incidentes antes que trabajo ordinario."""
    with db.connection() as cx:
        tasks=cx.execute("""SELECT t.* FROM tasks t JOIN incidents i ON i.id=t.incident_id
            WHERE t.room_id=? AND t.role=? AND t.state='pending' AND i.state='active'
            ORDER BY CASE i.priority WHEN 'alta' THEN 0 ELSE 1 END,t.id""",(room,role)).fetchall()

        def row(sql,*args):
            return cx.execute(sql,args).fetchone()

        for t in tasks:
            typ,sep,num=t['requirement'].partition(':')
            if not sep or not num.isdigit():continue
            ident=int(num)
            if typ=='alarm_ack':
                alarm=row("SELECT kind,state FROM alarms WHERE room_id=? AND id=?",room,ident)
                if alarm and alarm['state']=='active':return ('alarm_ack',ident,None)
            elif typ=='critical_ack':
                alarm=row("SELECT id FROM alarms WHERE room_id=? AND kind='clinical' AND source_id=? AND state='active' ORDER BY id DESC LIMIT 1",room,ident)
                if alarm:return ('alarm_ack',alarm['id'],None)
            elif typ=='device_operational':
                dev=row("SELECT state FROM devices WHERE room_id=? AND id=?",room,ident)
                if dev and dev['state']=='en_falla':return ('device_status',ident,'operativo')
            elif typ=='device_check':return ('device_check',ident,None)
            elif typ=='arrival_admitted':
                arr=row("SELECT state FROM arrivals WHERE room_id=? AND id=?",room,ident)
                bed=row("""SELECT b.id FROM beds b LEFT JOIN patients p ON p.bed_id=b.id
                    WHERE b.room_id=? AND p.id IS NULL
                    ORDER BY CASE b.unit WHEN 'URG' THEN 0 WHEN 'HOSP' THEN 1 ELSE 2 END,b.id LIMIT 1""",room)
                if arr and arr['state']=='waiting' and bed:return ('admit_arrival',ident,str(bed['id']))
            elif typ=='arrival_received':
                arr=row("SELECT state FROM arrivals WHERE room_id=? AND id=?",room,ident)
                if arr and arr['state']=='admitted':return ('arrival_receive',ident,None)
            elif typ=='lab_critical':
                order=row("SELECT state FROM lab_orders WHERE room_id=? AND id=?",room,ident)
                if order:
                    if order['state']=='requested':return ('sample_received',ident,None)
                    if order['state']=='received':return ('lab_result',ident,'critical')
            elif typ=='med_dispensed':
                order=row("SELECT state FROM medication_orders WHERE room_id=? AND id=?",room,ident)
                if order and order['state']=='requested':return ('med_dispense',ident,None)
            elif typ=='med_received':
                order=row("SELECT state FROM medication_orders WHERE room_id=? AND id=?",room,ident)
                if order and order['state']=='dispensed':return ('med_receive',ident,None)
            elif typ=='imaging_reported':
                order=row("SELECT state FROM imaging_orders WHERE room_id=? AND id=?",room,ident)
                if order and order['state']=='requested':return ('imaging_result',ident,'Informe A')
            elif typ=='imaging_reviewed':
                order=row("SELECT state FROM imaging_orders WHERE room_id=? AND id=?",room,ident)
                if order and order['state']=='reported':return ('imaging_review',ident,None)

        # Cola general: las estaciones virtuales también procesan solicitudes ordinarias.
        if role=='LIS':
            order=row("SELECT id FROM lab_orders WHERE room_id=? AND state='requested' ORDER BY id LIMIT 1",room)
            if order:return ('sample_received',order['id'],None)
            order=row("SELECT l.id FROM lab_orders l WHERE l.room_id=? AND l.state='received' AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.room_id=l.room_id AND t.state='pending' AND t.requirement='lab_critical:' || l.id) ORDER BY l.id LIMIT 1",room)
            if order:return ('lab_result',order['id'],'normal')
        elif role=='CLINICA':
            for table,states,action in [
                ('arrivals','admitted','arrival_receive'),
                ('medication_orders','dispensed','med_receive'),
                ('imaging_orders','reported','imaging_review')]:
                order=row(f"SELECT id FROM {table} WHERE room_id=? AND state=? ORDER BY id LIMIT 1",room,states)
                if order:return (action,order['id'],None)
            alarm=row("SELECT id FROM alarms WHERE room_id=? AND state='active' ORDER BY CASE priority WHEN 'alta' THEN 0 ELSE 1 END,id LIMIT 1",room)
            if alarm:return ('alarm_ack',alarm['id'],None)
        elif role=='FARMACIA':
            order=row("SELECT id FROM medication_orders WHERE room_id=? AND state='requested' ORDER BY id LIMIT 1",room)
            if order:return ('med_dispense',order['id'],None)
        elif role=='IMAGENES':
            order=row("SELECT id FROM imaging_orders WHERE room_id=? AND state='requested' ORDER BY id LIMIT 1",room)
            if order:return ('imaging_result',order['id'],'Informe A')
        elif role=='BIOMED':
            dev=row("SELECT id FROM devices WHERE room_id=? AND state='en_falla' ORDER BY id LIMIT 1",room)
            if dev:return ('device_status',dev['id'],'operativo')
        elif role=='HIS':
            arr=row("SELECT id FROM arrivals WHERE room_id=? AND state='waiting' ORDER BY id LIMIT 1",room)
            bed=row("""SELECT b.id FROM beds b LEFT JOIN patients p ON p.bed_id=b.id
                WHERE b.room_id=? AND p.id IS NULL ORDER BY b.id LIMIT 1""",room)
            if arr and bed:return ('admit_arrival',arr['id'],str(bed['id']))
    return None


def auto_staff_tick():
    """Puede ejecutarse aunque el generador de incidentes esté en modo manual/pausado."""
    with db.connection() as cx:
        slots=[dict(x) for x in cx.execute("""SELECT * FROM role_staffing
            WHERE mode='auto' AND next_action_at IS NOT NULL AND next_action_at<=?
            ORDER BY next_action_at LIMIT 50""",(db.now(),))]
    changed=set()
    for slot in slots:
        room,role=slot['room_id'],slot['role']
        if not db.is_automated_role(room,role):continue
        job=choose_job(room,role)
        if job:
            try:
                db.action(room,'AUTO · '+LABELS[role],role,*job)
                changed.add(room)
            except (db.ActionError,ValueError):
                # Una transición concurrente puede invalidar el siguiente paso.
                pass
        pace=slot['pace_seconds']
        delay=max(5,round(pace*random.uniform(0.8,1.35)))
        with db.connection(write=True) as cx:
            cx.execute("UPDATE role_staffing SET next_action_at=? WHERE room_id=? AND role=? AND mode='auto'",
                       (db.timeplus(delay),room,role))
    return list(changed)
