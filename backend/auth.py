"""
Login simples com token assinado (HMAC), sem dependências extras.

Credenciais configuráveis no .env / variáveis de ambiente:

    AUTH_LOGIN=admin
    AUTH_PASSWORD=agrosoft123
    AUTH_SECRET=<texto longo aleatório>   (opcional)
"""

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel


TOKEN_VALIDADE_SEGUNDOS = 60 * 60 * 12  # 12 horas

router = APIRouter(prefix="/api")


def _login() -> str:
    return (os.getenv("AUTH_LOGIN") or "admin").strip()


def _senha() -> str:
    return os.getenv("AUTH_PASSWORD") or "agrosoft123"


def _segredo() -> bytes:
    """
    Sem AUTH_SECRET, deriva um segredo das credenciais
    (trocar a senha invalida os tokens antigos).
    """

    return (
        os.getenv("AUTH_SECRET")
        or f"agrosoft::{_login()}::{_senha()}"
    ).encode()


def _assinar(conteudo: str) -> str:

    return hmac.new(
        _segredo(), conteudo.encode(), hashlib.sha256
    ).hexdigest()


def criar_token(login: str) -> str:

    expira = int(time.time()) + TOKEN_VALIDADE_SEGUNDOS

    conteudo = base64.urlsafe_b64encode(
        f"{login}|{expira}".encode()
    ).decode()

    return f"{conteudo}.{_assinar(conteudo)}"


def validar_token(token: str) -> Optional[str]:
    """Devolve o login se o token for válido; senão None."""

    try:
        conteudo, assinatura = token.split(".", 1)

        if not hmac.compare_digest(assinatura, _assinar(conteudo)):
            return None

        login, expira = (
            base64.urlsafe_b64decode(conteudo.encode())
            .decode()
            .rsplit("|", 1)
        )

        if int(expira) < time.time():
            return None

        return login

    except Exception:
        return None


def usuario_atual(
    authorization: Optional[str] = Header(None),
) -> str:
    """Dependência: exige 'Authorization: Bearer <token>'."""

    if authorization and authorization.lower().startswith("bearer "):

        login = validar_token(authorization[7:].strip())

        if login:
            return login

    raise HTTPException(
        status_code=401,
        detail="Sessão expirada. Faça login novamente.",
    )


class LoginIn(BaseModel):
    login: str
    senha: str


@router.post("/login")
def entrar(dados: LoginIn):

    login_ok = secrets.compare_digest(
        dados.login.strip().encode(), _login().encode()
    )

    senha_ok = secrets.compare_digest(
        dados.senha.encode(), _senha().encode()
    )

    if not (login_ok and senha_ok):
        raise HTTPException(
            status_code=401, detail="Login ou senha incorretos."
        )

    return {"token": criar_token(_login()), "login": _login()}
