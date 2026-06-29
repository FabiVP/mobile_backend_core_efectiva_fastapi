from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    rtr_auth, rtr_cartera, rtr_ficha, rtr_cobranza, rtr_preeval, rtr_buro,
    rtr_solicitudes, rtr_reportes, rtr_alertas, rtr_campanas, rtr_sync,
    rtr_cliente,
)

app = FastAPI(
    title="Core Mobile — Banco Andino",
    description="Capa operacional de canales moviles: fuerza de ventas en campo "
                "y app de clientes. Alimenta al core bd_core_financiero.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # apps moviles (Flutter / Android) — ajustar en produccion
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rtr_auth.router,    prefix="/auth",     tags=["Auth"])
app.include_router(rtr_cartera.router, prefix="/cartera",  tags=["Cartera"])
app.include_router(rtr_ficha.router,   prefix="/clientes", tags=["Ficha"])
app.include_router(rtr_cobranza.router, prefix="/cobranza", tags=["Cobranza"])
app.include_router(rtr_preeval.router, prefix="/pre-evaluar", tags=["PreEvaluacion"])
app.include_router(rtr_buro.router,    prefix="/buro",      tags=["Buro"])
app.include_router(rtr_solicitudes.router, prefix="/solicitudes", tags=["Solicitudes"])
app.include_router(rtr_reportes.router, prefix="/reportes", tags=["Reportes"])
app.include_router(rtr_alertas.router, prefix="/alertas", tags=["Alertas"])
app.include_router(rtr_campanas.router, prefix="/campanas", tags=["Campanas"])
app.include_router(rtr_sync.router, prefix="/sync", tags=["Sync (Puente al Core)"])

# App de clientes (appbanco / Flutter clientes) — login DNI + productos
app.include_router(rtr_cliente.router, prefix="/cliente", tags=["Cliente (App)"])

@app.get("/")
def root():
    return {"sistema": "Core Mobile Banco Andino", "version": "1.0.0", "status": "ok"}
