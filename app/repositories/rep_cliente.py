"""Repositorio del lado app de clientes — consultas sobre bd_core_mobile."""
import json
import uuid
from sqlalchemy import text
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


def _default_asesor_id(db: Session) -> str:
    """Devuelve el ID del primer asesor disponible (para solicitudes de clientes)."""
    row = db.execute(text("SELECT id FROM asesores ORDER BY created_at LIMIT 1")).first()
    if row:
        return str(row[0])
    raise ValueError("No hay asesores registrados en el sistema")


def crear_solicitud(db: Session, cliente_id: str, d: dict) -> dict:
    """Crea una solicitud de credito desde la app de clientes."""
    cliente = db.execute(
        text("SELECT numero_documento, nombres, apellidos FROM clientes WHERE id = :id"),
        {"id": cliente_id},
    ).mappings().first()
    if not cliente:
        raise ValueError("Cliente no encontrado")

    asesor_id = _default_asesor_id(db)
    sol_id = str(uuid.uuid4())
    expediente = "EXP-" + sol_id.replace("-", "")[:8].upper()

    db.execute(
        text("""INSERT INTO solicitudes_credito
                 (id, numero_expediente, asesor_id, cliente_id, canal,
                  tipo_negocio, nombre_negocio, ingresos_estimados,
                  gastos_mensuales, patrimonio_estimado,
                  monto_solicitado, plazo_meses, moneda, tipo_cuota, garantia,
                  destino_credito, cuota_estimada, tea_referencial,
                  firma_cliente_base64, estado)
                VALUES
                 (:id, :exp, :asesor, :cli, 'cliente',
                  :tn, :nn, :ing, :gm, :pat,
                  :monto, :plazo, :mon, :tc, :gar,
                  :dest, :cuota, :tea, :firma, 'enviado')"""),
        {
            "id": sol_id,
            "exp": expediente,
            "asesor": asesor_id,
            "cli": cliente_id,
            "tn": d.get("tipo_negocio"),
            "nn": d.get("nombre_negocio"),
            "ing": d.get("ingresos_estimados"),
            "gm": d.get("gastos_mensuales"),
            "pat": d.get("patrimonio_estimado"),
            "monto": d["monto_solicitado"],
            "plazo": d["plazo_meses"],
            "mon": d.get("moneda", "PEN"),
            "tc": d.get("tipo_cuota", "mensual"),
            "gar": d.get("garantia", "sin_garantia"),
            "dest": d.get("destino_credito"),
            "cuota": d.get("cuota_estimada"),
            "tea": d.get("tea_referencial"),
            "firma": d.get("firma_cliente_base64"),
        },
    )

    payload = {
        "numero_documento": cliente["numero_documento"],
        "nombres": cliente["nombres"] or "",
        "apellidos": cliente["apellidos"] or "",
        "monto_solicitado": float(d["monto_solicitado"]),
        "plazo_meses": int(d["plazo_meses"]),
        "numero_expediente": expediente,
    }
    db.execute(
        text("""INSERT INTO sync_outbox (id, entidad, entidad_id, operacion, payload, estado)
                 VALUES (:id, 'solicitudes_credito', :eid, 'create', CAST(:payload AS jsonb), 'pendiente')"""),
        {"id": str(uuid.uuid4()), "eid": sol_id, "payload": json.dumps(payload)},
    )
    db.commit()
    return {"id": sol_id, "numero_expediente": expediente, "estado": "enviado"}


def subir_documento_solicitud(db: Session, solicitud_id: str, data: dict) -> dict:
    """Registra metadata de un documento adjunto desde la app cliente."""
    doc_id = str(uuid.uuid4())
    db.execute(
        text("""INSERT INTO solicitudes_documentos
                 (id, solicitud_id, tipo_documento, archivo_base64, content_type, storage_url, tamanio_kb, nitidez_score)
                 VALUES (:id, :sol, :tipo, :b64, :ct, :url, :kb, :ns)"""),
        {"id": doc_id, "sol": solicitud_id, "tipo": data["tipo_documento"],
         "b64": data.get("archivo_base64"), "ct": data.get("content_type"),
         "url": data.get("storage_url"), "kb": data.get("tamanio_kb"),
         "ns": data.get("nitidez_score")},
    )
    db.commit()
    return {"id": doc_id}
