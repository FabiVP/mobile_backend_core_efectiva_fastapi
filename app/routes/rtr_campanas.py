from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.core.cfg_rbac import require_perfil
import uuid

router = APIRouter()


class CampanaOut(BaseModel):
    id: str
    cliente_id: str
    cliente_nombre: str
    tipo: Optional[str] = None
    monto_ofertado: float
    fecha_vencimiento: Optional[str] = None
    dias_restantes: int


class CampanaCreateIn(BaseModel):
    cliente_dni: str
    asesor_codigo: str
    tipo: str = "renovacion"
    monto_ofertado: float
    fecha_vencimiento: str


@router.get("", response_model=list[CampanaOut])
def listar(
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Campanas activas del asesor, mas proximas a vencer primero (HU-16/RF-40)."""
    rows = db.execute(
        text(
            """
            SELECT ca.id, ca.cliente_id, ca.tipo, ca.monto_ofertado,
                   ca.fecha_vencimiento, c.nombres, c.apellidos
            FROM campanas_activas ca
            JOIN clientes c ON c.id = ca.cliente_id
            WHERE ca.asesor_id = :asesor AND ca.activa = TRUE
              AND (ca.fecha_vencimiento IS NULL OR ca.fecha_vencimiento >= :hoy)
            ORDER BY ca.fecha_vencimiento ASC NULLS LAST
            """
        ),
        {"asesor": asesor["asesor_id"], "hoy": date.today()},
    ).mappings().all()
    hoy = date.today()
    return [
        CampanaOut(
            id=str(r["id"]),
            cliente_id=str(r["cliente_id"]),
            cliente_nombre=f"{r['nombres']} {r['apellidos']}",
            tipo=r["tipo"],
            monto_ofertado=float(r["monto_ofertado"] or 0),
            fecha_vencimiento=r["fecha_vencimiento"].isoformat()
            if r["fecha_vencimiento"]
            else None,
            dias_restantes=(r["fecha_vencimiento"] - hoy).days
            if r["fecha_vencimiento"]
            else 0,
        )
        for r in rows
    ]


@router.post("")
def crear(
    data: CampanaCreateIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(require_perfil("supervisor", "administrador")),
):
    """Crea una nueva campana (solo supervisor/admin)."""
    cliente = db.execute(
        text("SELECT id FROM clientes WHERE numero_documento = :doc"),
        {"doc": data.cliente_dni},
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    asesor_row = db.execute(
        text("SELECT id FROM asesores WHERE codigo_empleado = :cod"),
        {"cod": data.asesor_codigo},
    ).first()
    if not asesor_row:
        raise HTTPException(status_code=404, detail="Asesor no encontrado")

    try:
        fv = date.fromisoformat(data.fecha_vencimiento)
    except ValueError:
        raise HTTPException(status_code=400, detail="fecha_vencimiento debe ser YYYY-MM-DD")

    campana_id = str(uuid.uuid4())
    db.execute(
        text("""INSERT INTO campanas_activas (id, asesor_id, cliente_id, tipo, monto_ofertado, fecha_vencimiento)
                 VALUES (:id, :asesor, :cliente, :tipo, :monto, :fv)"""),
        {"id": campana_id, "asesor": str(asesor_row[0]), "cliente": str(cliente[0]),
         "tipo": data.tipo, "monto": data.monto_ofertado, "fv": fv},
    )
    db.commit()
    return {"id": campana_id, "ok": True}
