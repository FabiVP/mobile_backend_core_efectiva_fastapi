from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.cfg_auth import get_current_asesor

router = APIRouter()


class PreEvalIn(BaseModel):
    numero_documento: str
    nombres: str = ""
    tipo_negocio: str = ""
    ingresos_estimados: float = 0
    monto_solicitado: float = 0
    destino_credito: str = ""


class PreEvalOut(BaseModel):
    calificacion: str   # APTO / REVISAR / NO_PROCEDE
    motivo: str
    puntaje: int


@router.post("", response_model=PreEvalOut)
def pre_evaluar(data: PreEvalIn, asesor: dict = Depends(get_current_asesor)):
    """Pre-evaluacion crediticia simulada (M4 / RF-38).

    Regla mock por capacidad de pago: relacion monto vs. ingresos anuales.
    En produccion esto invocaria el motor de scoring del core.
    """
    ingresos_anuales = max(data.ingresos_estimados, 1) * 12
    ratio = data.monto_solicitado / ingresos_anuales if ingresos_anuales else 99

    if data.ingresos_estimados <= 0:
        return PreEvalOut(
            calificacion="REVISAR",
            motivo="Ingresos no declarados; requiere analisis adicional.",
            puntaje=50,
        )
    if ratio <= 0.6:
        return PreEvalOut(
            calificacion="APTO",
            motivo="Capacidad de pago suficiente para el monto solicitado.",
            puntaje=85,
        )
    if ratio <= 1.2:
        return PreEvalOut(
            calificacion="REVISAR",
            motivo="El monto solicitado es alto respecto a sus ingresos.",
            puntaje=60,
        )
    return PreEvalOut(
        calificacion="NO_PROCEDE",
        motivo="El monto supera ampliamente la capacidad de pago estimada.",
        puntaje=25,
    )
