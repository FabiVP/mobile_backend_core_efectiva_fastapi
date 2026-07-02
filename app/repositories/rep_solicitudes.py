import json
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session


def _upsert_cliente(db: Session, d: dict) -> str:
    """Devuelve el cliente_id; lo crea si no existe (por numero_documento)."""
    row = db.execute(
        text("SELECT id FROM clientes WHERE numero_documento = :doc"),
        {"doc": d["numero_documento"]},
    ).first()
    if row:
        return str(row[0])
    cid = str(uuid.uuid4())
    db.execute(
        text(
            """INSERT INTO clientes (id, numero_documento, nombres, apellidos,
                   telefono, tipo_negocio, nombre_negocio, es_prospecto)
               VALUES (:id,:doc,:nom,:ape,:tel,:tn,:nn,TRUE)"""
        ),
        {
            "id": cid,
            "doc": d["numero_documento"],
            "nom": d.get("nombres", ""),
            "ape": d.get("apellidos", ""),
            "tel": d.get("telefono"),
            "tn": d.get("tipo_negocio"),
            "nn": d.get("nombre_negocio"),
        },
    )
    return cid


def crear(db: Session, asesor_id: str, agencia_id: str | None, d: dict) -> dict:
    """Crea una solicitud de credito (M5 / HU-17)."""
    cliente_id = _upsert_cliente(db, d)
    sol_id = str(uuid.uuid4())
    expediente = "EXP-" + sol_id.replace("-", "")[:8].upper()
    db.execute(
        text(
            """INSERT INTO solicitudes_credito
                 (id, numero_expediente, asesor_id, cliente_id, agencia_id,
                  canal, tipo_negocio, nombre_negocio, ingresos_estimados,
                  monto_solicitado, plazo_meses, moneda, tipo_cuota, garantia,
                  destino_credito, cuota_estimada, tea_referencial,
                  firma_cliente_base64, estado)
               VALUES
                 (:id,:exp,:asesor,:cli,:ag,'asesor',:tn,:nn,:ing,
                  :monto,:plazo,:mon,:tc,:gar,:dest,:cuota,:tea,:firma,'enviado')"""
        ),
        {
            "id": sol_id,
            "exp": expediente,
            "asesor": asesor_id,
            "cli": cliente_id,
            "ag": agencia_id,
            "tn": d.get("tipo_negocio"),
            "nn": d.get("nombre_negocio"),
            "ing": d.get("ingresos_estimados"),
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

    # Encola para promover al nucleo bancario (puente sync_outbox -> core).
    payload = {
        "numero_documento": d["numero_documento"],
        "nombres": d.get("nombres", ""),
        "apellidos": d.get("apellidos", ""),
        "monto_solicitado": float(d["monto_solicitado"]),
        "plazo_meses": int(d["plazo_meses"]),
        "numero_expediente": expediente,
    }
    db.execute(
        text(
            """INSERT INTO sync_outbox (id, entidad, entidad_id, operacion, payload, estado)
               VALUES (:id, 'solicitudes_credito', :eid, 'create', CAST(:payload AS jsonb), 'pendiente')"""
        ),
        {
            "id": str(uuid.uuid4()),
            "eid": sol_id,
            "payload": json.dumps(payload),
        },
    )
    db.commit()
    return {"id": sol_id, "numero_expediente": expediente, "estado": "enviado"}


def agregar_nota(db: Session, solicitud_id: str, asesor_id: str, contenido: str) -> dict:
    """Agrega una nota interna a una solicitud (RF-72)."""
    nid = str(uuid.uuid4())
    db.execute(
        text(
            """INSERT INTO solicitudes_notas_internas
                 (id, solicitud_id, asesor_id, contenido)
               VALUES (:id,:sol,:asesor,:cont)"""
        ),
        {"id": nid, "sol": solicitud_id, "asesor": asesor_id, "cont": contenido[:500]},
    )
    db.commit()
    return {"id": nid}


def listar_notas(db: Session, solicitud_id: str) -> list[dict]:
    """Notas internas de una solicitud, recientes primero (RF-72)."""
    rows = db.execute(
        text(
            """SELECT contenido, created_at
               FROM solicitudes_notas_internas
               WHERE solicitud_id = :sol
               ORDER BY created_at DESC"""
        ),
        {"sol": solicitud_id},
    ).mappings().all()
    return [
        {
            "contenido": r["contenido"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


def listar(db: Session, asesor_id: str, perfil: str = "") -> list[dict]:
    """Solicitudes del asesor en el mes actual (HU-20), recientes primero.
    Si el usuario es supervisor, retorna todas las solicitudes del mes."""
    where_extra = ""
    params: dict = {}
    if perfil != "supervisor":
        where_extra = "AND s.asesor_id = :asesor"
        params["asesor"] = asesor_id
    rows = db.execute(
        text(
            f"""
            SELECT s.id, s.numero_expediente, s.monto_solicitado, s.monto_aprobado,
                   s.estado, s.created_at,
                   c.nombres, c.apellidos,
                   a.nombres AS asesor_nombres, a.apellidos AS asesor_apellidos
            FROM solicitudes_credito s
            JOIN clientes c ON c.id = s.cliente_id
            JOIN asesores a ON a.id = s.asesor_id
            WHERE date_trunc('month', s.created_at) = date_trunc('month', now())
              {where_extra}
            ORDER BY s.created_at DESC
            """
        ),
        params,
    ).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "numero_expediente": r["numero_expediente"],
            "cliente_nombre": f"{r['nombres']} {r['apellidos']}",
            "monto_solicitado": float(r["monto_solicitado"] or 0),
            "monto_aprobado": float(r["monto_aprobado"] or 0),
            "estado": r["estado"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "asesor_nombre": f"{r['asesor_nombres']} {r['asesor_apellidos']}",
        }
        for r in rows
    ]


def obtener(db: Session, solicitud_id: str) -> dict | None:
    """Detalle completo de una solicitud."""
    row = db.execute(
        text(
            """
            SELECT s.*, c.nombres, c.apellidos, c.numero_documento, c.telefono as cliente_telefono,
                   a.nombres as asesor_nombre, a.apellidos as asesor_apellidos
            FROM solicitudes_credito s
            JOIN clientes c ON c.id = s.cliente_id
            JOIN asesores a ON a.id = s.asesor_id
            WHERE s.id = :id
            """
        ),
        {"id": solicitud_id},
    ).mappings().first()
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "numero_expediente": row["numero_expediente"],
        "cod_solicitud_core": row["cod_solicitud_core"],
        "asesor_id": str(row["asesor_id"]),
        "cliente_id": str(row["cliente_id"]),
        "agencia_id": str(row["agencia_id"]) if row["agencia_id"] else None,
        "cliente_nombre": f"{row['nombres']} {row['apellidos']}",
        "cliente_documento": row["numero_documento"],
        "cliente_telefono": row["cliente_telefono"],
        "asesor_nombre": f"{row['asesor_nombre']} {row['asesor_apellidos']}",
        "tipo_negocio": row["tipo_negocio"],
        "nombre_negocio": row["nombre_negocio"],
        "ingresos_estimados": float(row["ingresos_estimados"] or 0),
        "monto_solicitado": float(row["monto_solicitado"] or 0),
        "monto_aprobado": float(row["monto_aprobado"] or 0),
        "plazo_meses": row["plazo_meses"],
        "moneda": row["moneda"],
        "tipo_cuota": row["tipo_cuota"],
        "garantia": row["garantia"],
        "destino_credito": row["destino_credito"],
        "cuota_estimada": float(row["cuota_estimada"] or 0),
        "tea_referencial": float(row["tea_referencial"] or 0),
        "estado": row["estado"],
        "motivo_rechazo": row["motivo_rechazo"],
        "condicion_adicional": row["condicion_adicional"],
        "analista_asignado": row["analista_asignado"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def actualizar(db: Session, solicitud_id: str, data: dict) -> dict:
    """Actualiza estado y/o campos de evaluacion de una solicitud."""
    sets = []
    params = {"id": solicitud_id}
    for campo in ("estado", "monto_aprobado", "motivo_rechazo", "condicion_adicional", "analista_asignado"):
        if campo in data:
            sets.append(f"{campo} = :{campo}")
            params[campo] = data[campo]

    if not sets:
        return {"ok": False, "detail": "Sin campos para actualizar"}

    estado_anterior = db.execute(
        text("SELECT estado FROM solicitudes_credito WHERE id = :id"),
        {"id": solicitud_id},
    ).scalar()

    sets.append("updated_at = now()")
    db.execute(
        text(f"UPDATE solicitudes_credito SET {', '.join(sets)} WHERE id = :id"),
        params,
    )

    if "estado" in data and estado_anterior and estado_anterior != data["estado"]:
        db.execute(
            text("""INSERT INTO solicitudes_bitacora (id, solicitud_id, estado_anterior, estado_nuevo, cambiado_por)
                     VALUES (gen_random_uuid(), :sol, :ant, :nue, :usr)"""),
            {"sol": solicitud_id, "ant": estado_anterior, "nue": data["estado"],
             "usr": data.get("cambiado_por", "supervisor")},
        )

    db.commit()
    return {"ok": True, "id": solicitud_id, "estado": data.get("estado", estado_anterior)}


def _generar_cronograma(monto: float, tea: float, plazo_meses: int, fecha_desembolso):
    """Genera cuotas del cronograma usando frances."""
    tasa_mensual = pow(1 + tea / 100, 1 / 12) - 1
    cuota = monto * tasa_mensual / (1 - pow(1 + tasa_mensual, -plazo_meses))
    saldo = monto
    rows = []
    for i in range(1, plazo_meses + 1):
        interes = saldo * tasa_mensual
        capital = cuota - interes
        if i == plazo_meses:
            capital = saldo
            cuota = capital + interes
        saldo -= capital
        dia = min(fecha_desembolso.day, 28)
        mes = fecha_desembolso.month + i
        anno = fecha_desembolso.year + (mes - 1) // 12
        mes = ((mes - 1) % 12) + 1
        venc = date(anno, mes, dia)
        rows.append({
            "nro": i,
            "venc": venc,
            "cuota": round(cuota, 2),
            "capital": round(capital, 2),
            "interes": round(interes, 2),
            "saldo": round(max(saldo, 0), 2),
        })
    return rows


def desembolsar(db: Session, solicitud_id: str) -> dict:
    """Marca una solicitud como desembolsada y crea credito + cronograma."""
    row = db.execute(
        text("""SELECT s.estado, s.cliente_id, s.monto_aprobado, s.plazo_meses,
                      s.tea_referencial, s.monto_solicitado, s.numero_expediente
               FROM solicitudes_credito s WHERE s.id = :id"""),
        {"id": solicitud_id},
    ).mappings().first()
    if row is None:
        return {"ok": False, "detail": "Solicitud no encontrada"}
    if row["estado"] not in ("aprobado", "condicionado"):
        return {"ok": False, "detail": f"Solicitud en estado '{row['estado']}' no puede desembolsarse"}

    monto = float(row["monto_aprobado"] or row["monto_solicitado"])
    plazo = row["plazo_meses"] or 12
    tea = float(row["tea_referencial"] or 15.0)
    cliente_id = row["cliente_id"]

    cod_cuenta = "CRE-" + solicitud_id.replace("-", "")[:8].upper()
    fecha_des = date.today()

    db.execute(
        text("""UPDATE solicitudes_credito SET estado = 'desembolsado', updated_at = now()
                 WHERE id = :id"""),
        {"id": solicitud_id},
    )
    db.execute(
        text("""INSERT INTO solicitudes_bitacora (id, solicitud_id, estado_anterior, estado_nuevo, cambiado_por)
                 VALUES (gen_random_uuid(), :sol, :ant, 'desembolsado', 'sistema')"""),
        {"sol": solicitud_id, "ant": row["estado"]},
    )

    # Crear registro en cr_creditos (espejo)
    db.execute(
        text("""INSERT INTO cr_creditos
                 (id, cod_cuenta_credito, cliente_id, producto, monto_desembolsado,
                  saldo_capital, saldo_total, dias_mora, estado, fecha_desembolso,
                  tea, cuotas_total, cuotas_pagadas)
                 VALUES
                 (gen_random_uuid(), :cod, :cli, 'CREDITO_EFECTIVA', :monto,
                  :monto, :monto, 0, 'vigente', :fec,
                  :tea, :plazo, 0)"""),
        {"cod": cod_cuenta, "cli": cliente_id, "monto": monto,
         "fec": fecha_des, "tea": tea, "plazo": plazo},
    )

    # Generar e insertar cronograma
    cronograma = _generar_cronograma(monto, tea, plazo, fecha_des)
    for c in cronograma:
        db.execute(
            text("""INSERT INTO cr_cronograma_pagos
                     (id, cod_cuenta_credito, nro_cuota, fecha_vencimiento,
                      monto_cuota, monto_capital, monto_interes, saldo, estado_cuota)
                     VALUES
                     (gen_random_uuid(), :cod, :nro, :venc,
                      :cuota, :cap, :int, :saldo, 'pendiente')"""),
            {"cod": cod_cuenta, "nro": c["nro"], "venc": c["venc"],
             "cuota": c["cuota"], "cap": c["capital"], "int": c["interes"],
             "saldo": c["saldo"]},
        )

    db.commit()
    return {"ok": True, "id": solicitud_id, "estado": "desembolsado",
            "cod_cuenta_credito": cod_cuenta}


def subir_documento(db: Session, solicitud_id: str, data: dict) -> dict:
    """Registra metadata de un documento adjunto a una solicitud."""
    doc_id = str(uuid.uuid4())
    db.execute(
        text("""INSERT INTO solicitudes_documentos
                 (id, solicitud_id, tipo_documento, archivo_base64, content_type, storage_url, tamanio_kb)
                 VALUES (:id, :sol, :tipo, :b64, :ct, :url, :kb)"""),
        {"id": doc_id, "sol": solicitud_id, "tipo": data["tipo_documento"],
         "b64": data.get("archivo_base64"), "ct": data.get("content_type"),
         "url": data.get("storage_url"), "kb": data.get("tamanio_kb")},
    )
    db.commit()
    return {"id": doc_id}


def cronograma_solicitud(db: Session, solicitud_id: str) -> list[dict]:
    """Cronograma de pagos asociado a una solicitud desembolsada."""
    rows = db.execute(
        text(
            """
            SELECT cp.nro_cuota, cp.fecha_vencimiento, cp.monto_cuota,
                   cp.monto_capital, cp.monto_interes, cp.saldo, cp.estado_cuota, cp.fecha_pago
            FROM solicitudes_credito s
            JOIN clientes c ON c.id = s.cliente_id
            JOIN cr_creditos cr ON cr.cliente_id = c.id
            JOIN cr_cronograma_pagos cp ON cp.cod_cuenta_credito = cr.cod_cuenta_credito
            WHERE s.id = :sol
            ORDER BY cp.nro_cuota
            """
        ),
        {"sol": solicitud_id},
    ).mappings().all()
    return [
        {
            "nro_cuota": r["nro_cuota"],
            "fecha_vencimiento": r["fecha_vencimiento"].isoformat() if r["fecha_vencimiento"] else None,
            "monto_cuota": float(r["monto_cuota"] or 0),
            "monto_capital": float(r["monto_capital"] or 0),
            "monto_interes": float(r["monto_interes"] or 0),
            "saldo": float(r["saldo"] or 0),
            "estado_cuota": r["estado_cuota"],
            "fecha_pago": r["fecha_pago"].isoformat() if r["fecha_pago"] else None,
        }
        for r in rows
    ]


def bitacora(db: Session, solicitud_id: str) -> list[dict]:
    """Bitacora de cambios de estado de una solicitud (RF-75)."""
    rows = db.execute(
        text(
            """
            SELECT estado_anterior, estado_nuevo, cambiado_por, created_at
            FROM solicitudes_bitacora
            WHERE solicitud_id = :sol
            ORDER BY created_at DESC
            """
        ),
        {"sol": solicitud_id},
    ).mappings().all()
    return [
        {
            "estado_anterior": r["estado_anterior"],
            "estado_nuevo": r["estado_nuevo"],
            "cambiado_por": r["cambiado_por"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
