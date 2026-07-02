"""
Rutas de la **app de clientes** (appbanco / Flutter clientes).

Login con DNI (usuarios_cliente) y consulta de productos del cliente
autenticado: cuentas de ahorro, créditos + cronograma, movimientos,
tarjetas y notificaciones. Todas (excepto login) requieren Bearer token.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_cliente
from app.schemas.sch_cliente import (
    LoginClienteIn, RegisterClienteIn, TokenClienteOut, ClienteOut, CuentaAhorroOut, CreditoOut,
    CuotaOut, MovimientoOut, TarjetaOut, NotificacionOut, OperacionIn, OperacionOut,
    SolicitudClienteIn, SolicitudClienteOut, DocumentoClienteIn,
)
from app.controllers import ctl_auth_cliente
from app.repositories import rep_cliente
from app.core.cfg_security import hash_password, create_access_token
from app.models.mdl_cliente_mobile import UsuarioCliente
import uuid

router = APIRouter()


@router.post("/login", response_model=TokenClienteOut)
def login(data: LoginClienteIn, db: Session = Depends(get_db)):
    """Login del cliente (numero_documento + password) -> JWT."""
    result = ctl_auth_cliente.login(db, data.numero_documento, data.password)
    if result and result.get("_bloqueado"):
        raise HTTPException(status_code=423, detail="Usuario bloqueado por intentos fallidos")
    if not result:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return result


@router.post("/register")
def register(data: RegisterClienteIn, db: Session = Depends(get_db)):
    """Registro de nuevo cliente en la app."""
    existe = db.query(UsuarioCliente).filter(
        UsuarioCliente.username == data.numero_documento
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="El DNI ya está registrado")

    cliente_id = str(uuid.uuid4())
    db.execute(
        text("""INSERT INTO clientes (id, numero_documento, nombres, apellidos, telefono, email, es_prospecto)
                 VALUES (:id, :doc, :nom, :ape, :tel, :email, TRUE)"""),
        {"id": cliente_id, "doc": data.numero_documento, "nom": data.nombres,
         "ape": data.apellidos, "tel": data.telefono, "email": data.email},
    )
    user_id = str(uuid.uuid4())
    db.execute(
        text("""INSERT INTO usuarios_cliente (id, cliente_id, username, password_hash, activo)
                 VALUES (:id, :cli, :user, :pw, TRUE)"""),
        {"id": user_id, "cli": cliente_id, "user": data.numero_documento,
         "pw": hash_password(data.password)},
    )
    db.commit()

    token = create_access_token({
        "sub": data.numero_documento,
        "cliente_id": cliente_id,
        "nombre": f"{data.nombres} {data.apellidos}",
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "cliente": {
            "id": cliente_id,
            "numero_documento": data.numero_documento,
            "nombres": data.nombres,
            "apellidos": data.apellidos,
            "email": data.email,
            "telefono": data.telefono,
        },
    }


@router.get("/perfil", response_model=ClienteOut)
def perfil(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    cliente = rep_cliente.get_cliente(db, cli["cliente_id"])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/cuentas", response_model=list[CuentaAhorroOut])
def cuentas(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.cuentas_ahorro(db, cli["cliente_id"])


@router.get("/creditos", response_model=list[CreditoOut])
def creditos(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.creditos(db, cli["cliente_id"])


@router.get("/creditos/{cod_cuenta_credito}/cronograma", response_model=list[CuotaOut])
def cronograma(
    cod_cuenta_credito: str,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    return rep_cliente.cronograma(db, cod_cuenta_credito)


@router.get("/movimientos", response_model=list[MovimientoOut])
def movimientos(
    limit: int = 20,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    return rep_cliente.movimientos(db, cli["cliente_id"], limit)


@router.get("/tarjetas", response_model=list[TarjetaOut])
def tarjetas(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.tarjetas(db, cli["cliente_id"])


@router.get("/notificaciones", response_model=list[NotificacionOut])
def notificaciones(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.notificaciones(db, cli["cliente_id"])


@router.post("/operaciones", response_model=OperacionOut)
def crear_operacion(
    data: OperacionIn,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    """Registra una operación iniciada por el cliente (transferencia / pago)."""
    return rep_cliente.crear_operacion(db, cli["cliente_id"], data.model_dump())


@router.post("/solicitudes", response_model=SolicitudClienteOut)
def crear_solicitud(
    data: SolicitudClienteIn,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    """Registra una solicitud de credito desde la app de clientes."""
    try:
        return rep_cliente.crear_solicitud(db, cli["cliente_id"], data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/solicitudes/{solicitud_id}/documentos")
def subir_documento(
    solicitud_id: str,
    data: DocumentoClienteIn,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    """Registra un documento adjunto a la solicitud desde la app cliente."""
    return rep_cliente.subir_documento_solicitud(db, solicitud_id, data.model_dump())
