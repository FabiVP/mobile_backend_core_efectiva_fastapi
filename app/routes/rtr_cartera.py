from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.schemas.sch_cartera import MarcarVisitaIn
from app.repositories import rep_cartera

router = APIRouter()

@router.get("")
def listar_cartera(
    fecha: date | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Cartera del asesor autenticado con paginacion (30 por página).
    Muestra todos los registros ordenados del más reciente al más antiguo."""
    return rep_cartera.listar_por_asesor(db, asesor["asesor_id"], fecha, pagina, por_pagina)

@router.post("/{cartera_id}/visita")
def marcar_visita(
    cartera_id: str,
    data: MarcarVisitaIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Registra el resultado de una visita (RF-07/RF-17)."""
    ok = rep_cartera.marcar_visita(db, asesor["asesor_id"], cartera_id, data.model_dump())
    if not ok:
        raise HTTPException(status_code=404, detail="Item de cartera no encontrado")
    return {"status": "ok", "cartera_id": cartera_id, "estado_visita": data.resultado}
