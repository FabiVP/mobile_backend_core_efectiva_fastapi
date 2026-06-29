from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.mdl_cartera import CarteraDiaria
from app.models.mdl_clientes import Cliente

def _build_response(c, cli):
    return {
        "id": str(c.id),
        "cliente_id": str(c.cliente_id),
        "cliente_nombre": f"{cli.nombres} {cli.apellidos}",
        "documento": cli.numero_documento,
        "tipo_gestion": c.tipo_gestion,
        "prioridad": c.prioridad,
        "score_prioridad": c.score_prioridad or 0,
        "monto_credito": float(c.monto_credito or 0),
        "estado_visita": c.estado_visita,
        "orden_manual": c.orden_manual,
        "lat": float(cli.lat) if cli.lat is not None else None,
        "lng": float(cli.lng) if cli.lng is not None else None,
    }

def listar_por_asesor(db: Session, asesor_id: str, fecha: date) -> list[dict]:
    """Cartera del asesor para una fecha, ordenada por score (RF-09).
    Si no hay datos para la fecha exacta, toma la fecha mas reciente disponible."""
    filas = (
        db.query(CarteraDiaria, Cliente)
        .join(Cliente, Cliente.id == CarteraDiaria.cliente_id)
        .filter(
            CarteraDiaria.asesor_id == asesor_id,
            CarteraDiaria.fecha_asignacion == fecha,
        )
        .order_by(desc(CarteraDiaria.score_prioridad))
        .all()
    )
    if filas:
        return [_build_response(c, cli) for c, cli in filas]

    ultima_fecha = db.query(func.max(CarteraDiaria.fecha_asignacion)).filter(
        CarteraDiaria.asesor_id == asesor_id,
    ).scalar()
    if ultima_fecha is None:
        return []

    filas = (
        db.query(CarteraDiaria, Cliente)
        .join(Cliente, Cliente.id == CarteraDiaria.cliente_id)
        .filter(
            CarteraDiaria.asesor_id == asesor_id,
            CarteraDiaria.fecha_asignacion == ultima_fecha,
        )
        .order_by(desc(CarteraDiaria.score_prioridad))
        .all()
    )
    return [_build_response(c, cli) for c, cli in filas]

def marcar_visita(db: Session, asesor_id: str, cartera_id: str, data: dict) -> bool:
    fila = (
        db.query(CarteraDiaria)
        .filter(CarteraDiaria.id == cartera_id, CarteraDiaria.asesor_id == asesor_id)
        .first()
    )
    if not fila:
        return False
    fila.estado_visita = "visitado" if data["resultado"] == "visitado" else data["resultado"]
    fila.resultado_visita = data["resultado"]
    fila.observacion_visita = data.get("observacion", "")
    fila.timestamp_visita = datetime.now(timezone.utc)
    fila.lat_visita = data.get("lat")
    fila.lng_visita = data.get("lng")
    db.commit()
    return True
