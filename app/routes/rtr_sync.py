from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.core.cfg_rbac import require_perfil
from app.services import svc_promocion
import uuid
import json

router = APIRouter()


class SyncSubirItem(BaseModel):
    entidad: str
    entidad_id: str
    operacion: str = "create"
    payload: dict


@router.post("/promover")
def promover(
    db: Session = Depends(get_db),
    asesor: dict = Depends(require_perfil("supervisor", "administrador")),
):
    """Promueve las solicitudes pendientes al nucleo bancario (solo supervisor/admin)."""
    return svc_promocion.promover(db)


@router.get("/outbox")
def outbox(
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Estado de la cola de sincronizacion al core."""
    rows = db.execute(
        text(
            """SELECT entidad, operacion, estado, core_ref, intentos, ultimo_error,
                      created_at, procesado_at
               FROM sync_outbox ORDER BY created_at DESC LIMIT 50"""
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/subir")
def subir(
    data: list[SyncSubirItem],
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Recibe datos offline desde la app movil y los encola en sync_outbox."""
    insertados = 0
    for item in data:
        existe = db.execute(
            text("SELECT id FROM sync_outbox WHERE entidad_id = :eid AND entidad = :ent AND estado = 'pendiente'"),
            {"eid": item.entidad_id, "ent": item.entidad},
        ).first()
        if existe:
            continue
        db.execute(
            text("""INSERT INTO sync_outbox (id, entidad, entidad_id, operacion, payload, estado)
                     VALUES (:id, :ent, :eid, :op, CAST(:payload AS jsonb), 'pendiente')"""),
            {"id": str(uuid.uuid4()), "ent": item.entidad, "eid": item.entidad_id,
             "op": item.operacion, "payload": json.dumps(item.payload)},
        )
        insertados += 1
    db.commit()
    return {"ok": True, "insertados": insertados}


@router.get("/descargar")
def descargar(
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Devuelve datos actualizados para sincronizacion offline."""
    clientes = db.execute(
        text("""SELECT id, numero_documento, nombres, apellidos, telefono, direccion,
                       tipo_negocio, nombre_negocio, lat, lng, calificacion_sbs
                FROM clientes ORDER BY updated_at DESC LIMIT 100""")
    ).mappings().all()

    creditos = db.execute(
        text("""SELECT cr.id, cr.cod_cuenta_credito, cr.cliente_id, cr.producto,
                       cr.monto_desembolsado, cr.saldo_total, cr.dias_mora, cr.estado,
                       cr.cuotas_total, cr.cuotas_pagadas
                FROM cr_creditos cr
                JOIN cartera_diaria cd ON cd.cliente_id = cr.cliente_id
                WHERE cd.asesor_id = :asesor AND cd.fecha_asignacion = CURRENT_DATE
                ORDER BY cr.fecha_desembolso DESC"""),
        {"asesor": asesor["asesor_id"]},
    ).mappings().all()

    return {
        "clientes": [dict(r) for r in clientes],
        "creditos": [dict(r) for r in creditos],
        "timestamp": None,
    }
