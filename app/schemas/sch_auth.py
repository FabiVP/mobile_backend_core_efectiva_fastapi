from pydantic import BaseModel

class LoginIn(BaseModel):
    codigo_empleado: str
    password: str

class AsesorOut(BaseModel):
    id: str
    codigo_empleado: str
    nombres: str
    apellidos: str
    perfil: str
    agencia_id: str | None = None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    asesor: AsesorOut
