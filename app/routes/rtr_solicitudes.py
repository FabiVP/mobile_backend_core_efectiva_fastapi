from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.core.cfg_rbac import require_perfil
from app.schemas.sch_solicitudes import (
    SolicitudIn, SolicitudCreada, SolicitudResumen,
)
from app.repositories import rep_solicitudes
from app.services import svc_promocion

router = APIRouter()


class NotaIn(BaseModel):
    contenido: str


class NotaOut(BaseModel):
    contenido: str
    created_at: str | None = None


class SolicitudUpdateIn(BaseModel):
    estado: str | None = None
    monto_aprobado: float | None = None
    motivo_rechazo: str | None = None
    condicion_adicional: str | None = None
    analista_asignado: str | None = None
    cambiado_por: str = "supervisor"


class DocumentoIn(BaseModel):
    tipo_documento: str
    archivo_base64: str | None = None
    content_type: str | None = None
    storage_url: str | None = None
    tamanio_kb: int | None = None


@router.post("", response_model=SolicitudCreada)
def crear_solicitud(
    data: SolicitudIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Registra una solicitud de credito (M5 / HU-17)."""
    return rep_solicitudes.crear(
        db, asesor["asesor_id"], asesor.get("agencia_id"), data.model_dump()
    )


@router.get("", response_model=list[SolicitudResumen])
def listar_solicitudes(
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Historial de solicitudes del mes (HU-20) y tablero de estado (M9)."""
    return rep_solicitudes.listar(db, asesor["asesor_id"], asesor.get("perfil", ""))


@router.get("/{solicitud_id}")
def obtener_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Detalle completo de una solicitud."""
    sol = rep_solicitudes.obtener(db, solicitud_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return sol


@router.patch("/{solicitud_id}")
def actualizar_solicitud(
    solicitud_id: str,
    data: SolicitudUpdateIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Actualiza estado/evaluacion de una solicitud (solo el asesor dueno o supervisor)."""
    sol = rep_solicitudes.obtener(db, solicitud_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if asesor.get("perfil") not in ("supervisor", "administrador"):
        if sol["asesor_id"] != asesor["asesor_id"]:
            raise HTTPException(status_code=403, detail="No eres el asesor de esta solicitud")
        solo_estado = all(k == "estado" or k == "cambiado_por" for k in data.model_dump(exclude_none=True).keys())
        if not solo_estado:
            raise HTTPException(status_code=403, detail="Solo puedes cambiar el estado de tu solicitud")
    return rep_solicitudes.actualizar(
        db, solicitud_id, data.model_dump(exclude_none=True)
    )


@router.post("/{solicitud_id}/transmitir")
def transmitir_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Transmite una solicitud al core.
    1) Cambia estado a 'enviado'
    2) Promueve sync_outbox pendiente al nucleo bancario (bd_core_financiero)"""
    sol = rep_solicitudes.obtener(db, solicitud_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if sol["asesor_id"] != asesor["asesor_id"]:
        raise HTTPException(status_code=403, detail="No eres el asesor de esta solicitud")
    if sol["estado"] not in ("borrador", "enviado"):
        raise HTTPException(status_code=400, detail=f"No se puede transmitir una solicitud en estado '{sol['estado']}'")

    result = rep_solicitudes.actualizar(
        db, solicitud_id, {"estado": "enviado", "cambiado_por": "asesor"}
    )

    sync_result = svc_promocion.promover(db)
    result["sync"] = sync_result
    return result


@router.post("/{solicitud_id}/desembolsar")
def desembolsar_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(require_perfil("supervisor", "administrador")),
):
    """Desembolsa una solicitud aprobada/condicionada (solo supervisor/admin).
    Ademas promueve automaticamente al nucleo bancario."""
    result = rep_solicitudes.desembolsar(db, solicitud_id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["detail"])
    sync_result = svc_promocion.promover(db)
    result["sync"] = sync_result
    return result


@router.post("/{solicitud_id}/documentos")
def subir_documento(
    solicitud_id: str,
    data: DocumentoIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Registra un documento adjunto a la solicitud."""
    return rep_solicitudes.subir_documento(
        db, solicitud_id, data.model_dump()
    )


@router.get("/{solicitud_id}/cronograma")
def cronograma_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Cronograma de pagos de una solicitud desembolsada."""
    return rep_solicitudes.cronograma_solicitud(db, solicitud_id)


@router.get("/{solicitud_id}/bitacora")
def bitacora_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Bitacora de cambios de estado de una solicitud (RF-75)."""
    return rep_solicitudes.bitacora(db, solicitud_id)


@router.post("/{solicitud_id}/notas")
def agregar_nota(
    solicitud_id: str,
    data: NotaIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Agrega una nota interna a la solicitud (RF-72)."""
    return rep_solicitudes.agregar_nota(
        db, solicitud_id, asesor["asesor_id"], data.contenido
    )


@router.get("/{solicitud_id}/notas", response_model=list[NotaOut])
def listar_notas(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Notas internas de la solicitud (RF-72)."""
    return rep_solicitudes.listar_notas(db, solicitud_id)
