from pydantic import BaseModel
from typing import Optional


class SolicitudIn(BaseModel):
    # Solicitante / negocio
    numero_documento: str
    nombres: str = ""
    apellidos: str = ""
    telefono: Optional[str] = None
    tipo_negocio: Optional[str] = None
    nombre_negocio: Optional[str] = None
    ingresos_estimados: Optional[float] = None
    # Condiciones
    monto_solicitado: float
    plazo_meses: int
    moneda: str = "PEN"
    tipo_cuota: str = "mensual"
    garantia: str = "sin_garantia"
    destino_credito: Optional[str] = None
    cuota_estimada: Optional[float] = None
    tea_referencial: Optional[float] = None
    firma_cliente_base64: Optional[str] = None


class SolicitudCreada(BaseModel):
    id: str
    numero_expediente: str
    estado: str


class SolicitudResumen(BaseModel):
    id: str
    numero_expediente: str
    cliente_nombre: str
    monto_solicitado: float
    monto_aprobado: float
    estado: str
    created_at: Optional[str] = None
    asesor_nombre: Optional[str] = None
