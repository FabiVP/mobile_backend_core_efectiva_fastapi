"""Repositorio del lado app de clientes — consultas sobre bd_core_mobile."""
from sqlalchemy.orm import Session
from app.models.mdl_clientes import Cliente
from app.models.mdl_cliente_mobile import (
    UsuarioCliente, CrCuentaAhorro, CrCredito, CrCronogramaPago,
    CrMovimiento, Tarjeta, OperacionCliente, Notificacion,
)


def get_usuario_by_username(db: Session, username: str) -> UsuarioCliente | None:
    return db.query(UsuarioCliente).filter(
        UsuarioCliente.username == username
    ).first()


def get_cliente(db: Session, cliente_id: str) -> Cliente | None:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


def cuentas_ahorro(db: Session, cliente_id: str) -> list[CrCuentaAhorro]:
    return db.query(CrCuentaAhorro).filter(
        CrCuentaAhorro.cliente_id == cliente_id
    ).order_by(CrCuentaAhorro.cod_cuenta_ahorro.asc()).all()


def creditos(db: Session, cliente_id: str) -> list[CrCredito]:
    return db.query(CrCredito).filter(
        CrCredito.cliente_id == cliente_id
    ).order_by(CrCredito.fecha_desembolso.desc().nullslast()).all()


def cronograma(db: Session, cod_cuenta_credito: str) -> list[CrCronogramaPago]:
    return db.query(CrCronogramaPago).filter(
        CrCronogramaPago.cod_cuenta_credito == cod_cuenta_credito
    ).order_by(CrCronogramaPago.nro_cuota.asc()).all()


def movimientos(db: Session, cliente_id: str, limit: int = 20) -> list[CrMovimiento]:
    return db.query(CrMovimiento).filter(
        CrMovimiento.cliente_id == cliente_id
    ).order_by(CrMovimiento.fecha_operacion.desc()).limit(limit).all()


def tarjetas(db: Session, cliente_id: str) -> list[Tarjeta]:
    return db.query(Tarjeta).filter(
        Tarjeta.cliente_id == cliente_id
    ).order_by(Tarjeta.created_at.asc()).all()


def notificaciones(db: Session, cliente_id: str, limit: int = 30) -> list[Notificacion]:
    return db.query(Notificacion).filter(
        Notificacion.destinatario_tipo == "cliente",
        Notificacion.cliente_id == cliente_id,
    ).order_by(Notificacion.created_at.desc()).limit(limit).all()


def crear_operacion(db: Session, cliente_id: str, data: dict) -> OperacionCliente:
    op = OperacionCliente(
        cliente_id=cliente_id,
        cod_cuenta_origen=data.get("cod_cuenta_origen"),
        cod_cuenta_destino=data.get("cod_cuenta_destino"),
        tipo=data.get("tipo"),
        monto=data.get("monto"),
        moneda=data.get("moneda", "PEN"),
        estado="pendiente",
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op
