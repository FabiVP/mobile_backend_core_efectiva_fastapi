from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.schemas.sch_ficha import FichaOut, UbicacionIn
from app.repositories import rep_ficha
import uuid

router = APIRouter()


class ClienteCreateIn(BaseModel):
    numero_documento: str
    nombres: str
    apellidos: str
    telefono: str | None = None
    direccion: str | None = None
    tipo_negocio: str | None = None
    nombre_negocio: str | None = None
    ingresos_estimados: float | None = None
    lat: float | None = None
    lng: float | None = None


class ClienteUpdateIn(BaseModel):
    nombres: str | None = None
    apellidos: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    tipo_negocio: str | None = None
    nombre_negocio: str | None = None
    ingresos_estimados: float | None = None
    lat: float | None = None
    lng: float | None = None


@router.get("")
def listar_clientes(
    dni: str | None = Query(None),
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Lista de clientes del asesor. Filtra por DNI si se especifica."""
    if dni:
        rows = db.execute(
            text("SELECT id, numero_documento, nombres, apellidos, telefono, direccion, tipo_negocio FROM clientes WHERE numero_documento LIKE :dni ORDER BY nombres"),
            {"dni": f"%{dni}%"},
        ).mappings().all()
    else:
        rows = db.execute(
            text("""SELECT c.id, c.numero_documento, c.nombres, c.apellidos, c.telefono,
                           c.direccion, c.tipo_negocio
                    FROM clientes c
                    JOIN cartera_diaria cd ON cd.cliente_id = c.id
                    WHERE cd.asesor_id = :asesor AND cd.fecha_asignacion = CURRENT_DATE
                    ORDER BY c.nombres"""),
            {"asesor": asesor["asesor_id"]},
        ).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "numero_documento": r["numero_documento"],
            "nombres": r["nombres"],
            "apellidos": r["apellidos"],
            "telefono": r["telefono"],
            "direccion": r["direccion"],
            "tipo_negocio": r["tipo_negocio"],
        }
        for r in rows
    ]


@router.post("")
def crear_cliente(
    data: ClienteCreateIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Crea un nuevo cliente (prospecto)."""
    existe = db.execute(
        text("SELECT id FROM clientes WHERE numero_documento = :doc"),
        {"doc": data.numero_documento},
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="El DNI ya existe")

    cid = str(uuid.uuid4())
    db.execute(
        text("""INSERT INTO clientes (id, numero_documento, nombres, apellidos, telefono, direccion,
                 tipo_negocio, nombre_negocio, ingresos_estimados, lat, lng, es_prospecto)
                 VALUES (:id, :doc, :nom, :ape, :tel, :dir, :tn, :nn, :ing, :lat, :lng, TRUE)"""),
        {"id": cid, "doc": data.numero_documento, "nom": data.nombres, "ape": data.apellidos,
         "tel": data.telefono, "dir": data.direccion, "tn": data.tipo_negocio,
         "nn": data.nombre_negocio, "ing": data.ingresos_estimados,
         "lat": data.lat, "lng": data.lng},
    )
    db.commit()
    return {"id": cid, "numero_documento": data.numero_documento, "nombres": data.nombres, "apellidos": data.apellidos}


@router.patch("/{cliente_id}")
def actualizar_cliente(
    cliente_id: str,
    data: ClienteUpdateIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Actualiza datos del cliente."""
    sets = []
    params = {"id": cliente_id}
    for campo in ("nombres", "apellidos", "telefono", "direccion", "tipo_negocio",
                  "nombre_negocio", "ingresos_estimados", "lat", "lng"):
        val = getattr(data, campo, None)
        if val is not None:
            sets.append(f"{campo} = :{campo}")
            params[campo] = val

    if not sets:
        return {"ok": False, "detail": "Sin campos para actualizar"}

    sets.append("updated_at = now()")
    db.execute(text(f"UPDATE clientes SET {', '.join(sets)} WHERE id = :id"), params)
    db.commit()
    return {"ok": True}


@router.get("/{cliente_id}/ficha", response_model=FichaOut)
def ficha_cliente(
    cliente_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Ficha completa del cliente (M3 / HU-11)."""
    ficha = rep_ficha.obtener_ficha(db, cliente_id)
    if ficha is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return ficha


@router.post("/{cliente_id}/ubicacion")
def actualizar_ubicacion(
    cliente_id: str,
    body: UbicacionIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Actualiza las coordenadas del negocio del cliente (HU-10 / RF-25/26)."""
    ok = rep_ficha.actualizar_ubicacion(
        db, cliente_id, body.lat, body.lng, body.direccion
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"ok": True, "lat": body.lat, "lng": body.lng}
