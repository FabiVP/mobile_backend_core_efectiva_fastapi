from fastapi import Depends, HTTPException
from app.core.cfg_auth import get_current_asesor, get_current_cliente

PERFILES_SUPERVISOR = ("supervisor", "administrador")
PERFILES_ADMIN = ("administrador",)
PERFILES_OPERADOR = ("operador", "super_operador", "supervisor", "administrador")


def require_perfil(*perfiles_requeridos: str):
    """Dependency factory: valida que el asesor autenticado tenga uno de los perfiles indicados.
    Uso: ``Depends(require_perfil('supervisor', 'administrador'))``
    """
    def _check(asesor: dict = Depends(get_current_asesor)):
        if asesor.get("perfil") not in perfiles_requeridos:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para realizar esta accion",
            )
        return asesor
    return _check


def require_cliente_owner(*, cliente_id_field: str = "cliente_id"):
    """Verifica que el cliente autenticado sea el dueno del recurso."""
    def _check(
        cliente: dict = Depends(get_current_cliente),
    ):
        return cliente
    return _check
