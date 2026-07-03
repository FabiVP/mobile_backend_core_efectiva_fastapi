from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from app.models.mdl_cartera import CarteraDiaria
from app.models.mdl_clientes import Cliente

def _build_response(c, cli, solicitud_estado=None):
    return {
        "id": str(c.id),
        "cliente_id": str(c.cliente_id),
        "cliente_nombre": f"{cli.nombres} {cli.apellidos}",
        "documento": cli.numero_documento,
        "tipo_gestion": c.tipo_gestion,
        "solicitud_estado": solicitud_estado,
        "prioridad": c.prioridad,
        "score_prioridad": c.score_prioridad or 0,
        "monto_credito": float(c.monto_credito or 0),
        "estado_visita": c.estado_visita,
        "orden_manual": c.orden_manual,
        "fecha_asignacion": c.fecha_asignacion.isoformat() if c.fecha_asignacion else None,
        "lat": float(cli.lat) if cli.lat is not None else None,
        "lng": float(cli.lng) if cli.lng is not None else None,
    }

def _ultimo_estado_solicitud(db: Session, cliente_id: str) -> str | None:
    """Retorna el estado de la solicitud mas reciente del cliente (no borrador)."""
    sol = db.execute(
        text("""SELECT estado FROM solicitudes_credito
                 WHERE cliente_id = :cli AND estado != 'borrador'
                 ORDER BY created_at DESC LIMIT 1"""),
        {"cli": cliente_id},
    ).scalar()
    return sol

def listar_por_asesor(db: Session, asesor_id: str, fecha: date | None = None, pagina: int = 1, por_pagina: int = 30) -> dict:
    """Cartera del asesor con paginacion, ordenada por fecha DESC y score DESC.
    Muestra todos los registros (no solo una fecha)."""
    query = (
        db.query(CarteraDiaria, Cliente)
        .join(Cliente, Cliente.id == CarteraDiaria.cliente_id)
        .filter(CarteraDiaria.asesor_id == asesor_id)
        .order_by(desc(CarteraDiaria.fecha_asignacion), desc(CarteraDiaria.score_prioridad))
    )

    total = query.count()
    offset = (pagina - 1) * por_pagina
    filas = query.offset(offset).limit(por_pagina).all()

    items = [
        _build_response(c, cli, _ultimo_estado_solicitud(db, str(c.cliente_id)))
        for c, cli in filas
    ]
    return {
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": (total + por_pagina - 1) // por_pagina,
    }

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
