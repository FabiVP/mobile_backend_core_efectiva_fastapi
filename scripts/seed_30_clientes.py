"""
Seed: 30 clientes demo (rol Cliente) para App Clientes.
Login con el numero de documento como username y password.
"""
import sys, os, uuid
from sqlalchemy import text
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cfg_database import SessionLocal
from app.core.cfg_security import hash_password

CLIENTES = [
    ("Anaximandro", "Quispe",       "40118120", "964110201", "Bodega Don Anaxi", "El Tambo", 48, 2200.00, 900.00),
    ("Eulalia",     "Mamani",       "41223341", "964110202", "Picanteria La Eulalia", "Chilca", 36, 3000.00, 1400.00),
    ("Teofilo",     "Huaman",       "42330336", "964110203", "Maderas Huaman", "Pilcomayo", 60, 4200.00, 1800.00),
    ("Casandra",    "Flores",       "43440349", "964110204", "Distribuidora Casandra", "Huancayo", 84, 7000.00, 2600.00),
    ("Demostenes",  "Rojas",        "40556071", "964110205", "Ferreteria El Constructor", "San Agustin de Cajas", 30, 5200.00, 2100.00),
    ("Hipatia",     "Condori",      "41669066", "964110206", "Confecciones Hipatia", "El Tambo", 54, 6800.00, 2900.00),
    ("Anibal",      "Vargas",       "43773379", "964110207", "Transportes Anibal", "Concepcion", 42, 9500.00, 4200.00),
    ("Penelope",    "Apaza",        "40886086", "964110208", "Granja Penelope", "Sapallanga", 72, 8800.00, 3600.00),
    ("Heraclito",   "Ccahua",       "41990091", "964110209", "Importaciones Heraclito", "Huancayo", 96, 12000.00, 5000.00),
    ("Cleopatra",   "Soto",         "43003039", "964110210", "Botica Cleopatra", "Chupaca", 66, 11000.00, 4400.00),
    ("Esquilo",     "Ramos",        "40110010", "964110211", "Minimarket Esquilo", "Huayucachi", 24, 1900.00, 800.00),
    ("Ariadna",     "Quispe",       "41226021", "964110212", "Estilos Ariadna", "El Tambo", 40, 3300.00, 1300.00),
    ("Sofocles",    "Huanca",       "43336033", "964110213", "Panaderia Sofocles", "Sicaya", 58, 5600.00, 2300.00),
    ("Casiopea",    "Torres",       "40550055", "964110214", "Taller Casiopea", "Pilcomayo", 50, 7400.00, 3000.00),
    ("Aristofanes", "Cruz",         "41669166", "964110215", "Insumos Aristofanes", "Orcotuna", 78, 8200.00, 3300.00),
    ("Calipso",     "Mendoza",      "43880088", "964110216", "Calzados Calipso", "Huancayo", 62, 7900.00, 3100.00),
    ("Demetrio",    "Quispe",       "40119019", "964110217", "Mayorista Demetrio", "Jauja", 90, 11500.00, 4700.00),
    ("Antigona",    "Flores",       "41226126", "964110218", "Recreo Antigona", "Concepcion", 70, 9200.00, 3900.00),
    ("Pitagoras",   "Rojas",        "43339033", "964110219", "Ferreteria Pitagoras", "El Tambo", 100, 13000.00, 5200.00),
    ("Berenice",    "Apaza",        "40556056", "964110220", "Tejidos Berenice", "San Jeronimo de Tunan", 46, 8600.00, 3500.00),
    ("Anaxagoras",  "Huaman",       "43889089", "964110221", "Carga Anaxagoras", "Huancayo", 84, 14000.00, 5800.00),
    ("Climene",     "Vargas",       "41003001", "964110222", "Avicola Climene", "Sapallanga", 76, 13500.00, 5500.00),
    ("Epaminondas", "Soto",         "40115011", "964110223", "Bodega Epaminondas", "Pucara", 28, 2600.00, 1000.00),
    ("Lisistrata",  "Ramos",        "41336036", "964110224", "Variedades Lisistrata", "Huancayo", 52, 4100.00, 1700.00),
    ("Filoctetes",  "Cruz",         "41552052", "964110225", "Cevicheria Filoctetes", "Chilca", 18, 3800.00, 2200.00),
    ("Calirroe",    "Mendoza",      "41888088", "964110226", "Calzados Calirroe", "El Tambo", 34, 5000.00, 2600.00),
    ("Tucidides",   "Quispe",       "42220022", "964110227", "Ferreteria Tucidides", "Concepcion", 40, 6200.00, 2900.00),
    ("Aquiles",     "Mamani",       "43337037", "964110228", "Comercial Aquiles", "Huancayo", 60, 9000.00, 3600.00),
    ("Medea",       "Apaza",        "41884084", "964110229", "Bodega Medea", "Pilcomayo", 22, 1800.00, 1100.00),
    ("Esquines",    "Rojas",        "43334034", "964110230", "Fletes Esquines", "Jauja", 30, 7000.00, 3200.00),
]

def run():
    db = SessionLocal()
    try:
        insertados = 0
        for nombres, apellidos, doc, telefono, negocio, distrito, antiguedad, ingreso, gasto in CLIENTES:
            existe = db.execute(
                text("SELECT id FROM clientes WHERE numero_documento = :doc"),
                {"doc": doc},
            ).first()
            if existe:
                print(f"  YA EXISTE: {nombres} {apellidos} ({doc})")
                continue

            cli_id = str(uuid.uuid4())
            db.execute(
                text("""INSERT INTO clientes
                   (id, numero_documento, nombres, apellidos, telefono,
                    tipo_negocio, nombre_negocio, direccion, es_prospecto)
                   VALUES (:id, :doc, :nom, :ape, :tel,
                    :tn, :nn, :dir, FALSE)"""),
                {"id": cli_id, "doc": doc, "nom": nombres, "ape": apellidos,
                 "tel": telefono, "tn": "Negocio", "nn": negocio,
                 "dir": f"{distrito}, Junin"},
            )

            user_id = str(uuid.uuid4())
            db.execute(
                text("""INSERT INTO usuarios_cliente
                   (id, cliente_id, username, password_hash, activo)
                   VALUES (:id, :cli, :user, :pw, TRUE)"""),
                {"id": user_id, "cli": cli_id, "user": doc,
                 "pw": hash_password(doc)},
            )
            insertados += 1
            print(f"  CREADO: {nombres} {apellidos} ({doc}) / pass: {doc}")

        db.commit()
        print(f"\nOK. {insertados} clientes creados. Login con DNI como usuario y clave.")
    finally:
        db.close()

if __name__ == "__main__":
    run()
