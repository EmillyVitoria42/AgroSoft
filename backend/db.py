"""
Camada de banco de dados (SQLite).

Entidades (conforme requisitos da Etapa 2):

- PESSOAS            -> tipo CLIENTE-FORNECEDOR | FATURADO
- CLASSIFICACAO      -> tipo DESPESA | RECEITA
- MOVIMENTOCONTAS   -> tipo APAGAR | ARECEBER
- PARCELACONTAS      -> identificacao ("ÚNICA", "1/3", ...)

Regras:
- Cadastros nunca são excluídos: apenas INATIVADOS (e podem ser REATIVADOS).
"""

import os
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(
    os.getenv("DATABASE_PATH")
    or Path(__file__).parent / "agrosoft.db"
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS pessoas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo          TEXT NOT NULL
                  CHECK (tipo IN ('CLIENTE-FORNECEDOR', 'FATURADO')),
    razao_social  TEXT NOT NULL,
    fantasia      TEXT,
    documento     TEXT,
    status        TEXT NOT NULL DEFAULT 'ATIVO'
                  CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pessoas_tipo_documento
    ON pessoas (tipo, documento)
    WHERE documento IS NOT NULL;

CREATE TABLE IF NOT EXISTS classificacao (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       TEXT NOT NULL CHECK (tipo IN ('DESPESA', 'RECEITA')),
    descricao  TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'ATIVO'
               CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS movimento_contas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL CHECK (tipo IN ('APAGAR', 'ARECEBER')),
    numero_documento  TEXT,
    data_emissao      TEXT,
    descricao         TEXT,
    valor_total       REAL NOT NULL,
    pessoa_id         INTEGER NOT NULL REFERENCES pessoas (id),
    faturado_id       INTEGER NOT NULL REFERENCES pessoas (id),
    status            TEXT NOT NULL DEFAULT 'ATIVO'
                      CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em         TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS movimento_classificacao (
    movimento_id     INTEGER NOT NULL REFERENCES movimento_contas (id),
    classificacao_id INTEGER NOT NULL REFERENCES classificacao (id),
    PRIMARY KEY (movimento_id, classificacao_id)
);

CREATE TABLE IF NOT EXISTS parcela_contas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    movimento_id     INTEGER NOT NULL REFERENCES movimento_contas (id),
    identificacao    TEXT NOT NULL,
    numero           INTEGER NOT NULL,
    data_vencimento  TEXT NOT NULL,
    valor            REAL NOT NULL,
    status           TEXT NOT NULL DEFAULT 'ATIVO'
                     CHECK (status IN ('ATIVO', 'INATIVO'))
);
"""


# ============================================================
# TEXTO / DOCUMENTOS
# ============================================================


def somente_digitos(valor) -> str:
    """Remove tudo que não for dígito (CNPJ/CPF)."""

    return re.sub(r"\D", "", str(valor or ""))


def normalizar_texto(valor) -> str:
    """
    MAIÚSCULAS, sem acentos e sem espaços repetidos.
    Usado para comparar nomes/descrições.
    """

    texto = unicodedata.normalize("NFKD", str(valor or ""))

    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )

    return re.sub(r"\s+", " ", texto).strip().upper()


def formatar_documento(digitos: str | None) -> str | None:
    """11 dígitos -> CPF, 14 dígitos -> CNPJ."""

    d = somente_digitos(digitos)

    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

    if len(d) == 14:
        return (
            f"{d[:2]}.{d[2:5]}.{d[5:8]}/"
            f"{d[8:12]}-{d[12:]}"
        )

    return d or None


def rotulo_documento(digitos: str | None) -> str:

    tamanho = len(somente_digitos(digitos))

    if tamanho == 14:
        return "CNPJ"

    if tamanho == 11:
        return "CPF"

    return "DOCUMENTO"


# ============================================================
# CONEXÃO
# ============================================================


def conectar() -> sqlite3.Connection:

    conn = sqlite3.connect(DB_PATH, timeout=30)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    # Permite buscas sem acento / sem diferença de maiúsculas
    conn.create_function(
        "NORM", 1, normalizar_texto, deterministic=True
    )

    return conn


@contextmanager
def transacao():
    """
    Abre uma transação. Se qualquer erro acontecer,
    nada é gravado (rollback).
    """

    conn = conectar()

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def iniciar_banco() -> None:

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with transacao() as conn:
        conn.executescript(SCHEMA)
