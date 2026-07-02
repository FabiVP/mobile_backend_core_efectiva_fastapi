"""Schemas Pydantic del lado app de clientes."""
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# ── Autenticación ──────────────────────────────────────────────
class LoginClienteIn(BaseModel):
    numero_documento: str   # DNI (= usuarios_cliente.username)
    password: str


class RegisterClienteIn(BaseModel):
    numero_documento: str
    nombres: str
    apellidos: str
    telefono: str | None = None
    email: str | None = None
    password: str


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_cliente: str | None = None
    numero_documento: str
    nombres: str
    apellidos: str
    email: str | None = None
    telefono: str | None = None


class TokenClienteOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    cliente: ClienteOut


# ── Productos ──────────────────────────────────────────────────
class CuentaAhorroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_cuenta_ahorro: str
    tipo_cuenta: str | None = None
    moneda: str | None = None
    saldo_capital: float | None = None
    saldo_interes: float | None = None
    tea: float | None = None
    estado: str | None = None


class CreditoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_cuenta_credito: str
    producto: str | None = None
    monto_desembolsado: float | None = None
    saldo_capital: float | None = None
    saldo_total: float | None = None
    dias_mora: int = 0
    calificacion_interna: str | None = None
    estado: str | None = None
    fecha_desembolso: date | None = None
    tea: float | None = None
    cuotas_total: int | None = None
    cuotas_pagadas: int | None = None


class CuotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_cuenta_credito: str
    nro_cuota: int
    fecha_vencimiento: date
    monto_cuota: float | None = None
    monto_capital: float | None = None
    monto_interes: float | None = None
    saldo: float | None = None
    estado_cuota: str | None = None
    fecha_pago: date | None = None


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_operacion: str
    cod_cuenta: str | None = None
    tipo: str | None = None      # DEB / CRE / TRF
    concepto: str | None = None
    canal: str | None = None
    monto: float
    moneda: str | None = None
    fecha_operacion: datetime


class TarjetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    numero_enmascarado: str
    marca: str | None = None
    linea_credito: float | None = None
    saldo_utilizado: float | None = None
    fecha_corte: date | None = None
    fecha_pago: date | None = None
    estado: str | None = None


class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    titulo: str
    cuerpo: str | None = None
    tipo: str | None = None
    leida: bool = False
    created_at: datetime


# ── Solicitud de crédito desde app cliente ─────────────────────
class SolicitudClienteIn(BaseModel):
    tipo_negocio: str | None = None
    nombre_negocio: str | None = None
    ingresos_estimados: float | None = None
    gastos_mensuales: float | None = None
    patrimonio_estimado: float | None = None
    monto_solicitado: float
    plazo_meses: int
    moneda: str = "PEN"
    tipo_cuota: str = "mensual"
    garantia: str = "sin_garantia"
    destino_credito: str | None = None
    cuota_estimada: float | None = None
    tea_referencial: float | None = None
    firma_cliente_base64: str | None = None


class SolicitudClienteOut(BaseModel):
    id: str
    numero_expediente: str
    estado: str


class DocumentoClienteIn(BaseModel):
    tipo_documento: str
    archivo_base64: str | None = None
    content_type: str | None = None
    storage_url: str | None = None
    tamanio_kb: int | None = None
    nitidez_score: float | None = None


# ── Operaciones iniciadas por el cliente ───────────────────────
class OperacionIn(BaseModel):
    cod_cuenta_origen: str
    cod_cuenta_destino: str | None = None
    tipo: str   # pago_cuota / transferencia / recarga
    monto: float
    moneda: str = "PEN"


class OperacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_cuenta_origen: str | None = None
    cod_cuenta_destino: str | None = None
    tipo: str | None = None
    monto: float
    moneda: str | None = None
    estado: str
    created_at: datetime
