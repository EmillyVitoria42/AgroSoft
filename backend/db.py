"""
Camada de banco de dados (PostgreSQL).

Entidades (conforme requisitos da Etapa 2):

- PESSOAS            -> tipo CLIENTE-FORNECEDOR | FATURADO
- CLASSIFICACAO      -> tipo DESPESA | RECEITA
- MOVIMENTOCONTAS   -> tipo APAGAR | ARECEBER
- PARCELACONTAS      -> identificacao ("ÚNICA", "1/3", ...)

Regras:
- Cadastros nunca são excluídos: apenas INATIVADOS (e podem ser REATIVADOS).

Conexão:
- Variável de ambiente DATABASE_URL (obrigatória), por exemplo:
  postgresql://usuario:senha@host:5432/agrosoft
- DATABASE_SCHEMA (opcional): usa um schema separado (os testes usam
  isso para não mexer nas tabelas reais).
"""

import os
import re
import unicodedata
from contextlib import contextmanager

import psycopg2
import psycopg2.extras


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "").strip()


SCHEMA = r"""
-- Função usada nas buscas: MAIÚSCULAS, sem acentos e sem espaços
-- repetidos (equivalente ao normalizar_texto() do Python).
-- Não depende de extensões do PostgreSQL.
CREATE OR REPLACE FUNCTION norm(texto TEXT) RETURNS TEXT AS $fn$
    SELECT btrim(
        regexp_replace(
            upper(
                translate(
                    coalesce(texto, ''),
                    'áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ',
                    'aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN'
                )
            ),
            '\s+', ' ', 'g'
        )
    )
$fn$ LANGUAGE SQL IMMUTABLE;

CREATE TABLE IF NOT EXISTS pessoas (
    id            SERIAL PRIMARY KEY,
    tipo          VARCHAR(20) NOT NULL
                  CHECK (tipo IN ('CLIENTE-FORNECEDOR', 'FATURADO')),
    razao_social  VARCHAR(255) NOT NULL,
    fantasia      VARCHAR(255),
    documento     VARCHAR(14),
    status        VARCHAR(10) NOT NULL DEFAULT 'ATIVO'
                  CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pessoas_tipo_documento
    ON pessoas (tipo, documento)
    WHERE documento IS NOT NULL;

CREATE TABLE IF NOT EXISTS classificacao (
    id         SERIAL PRIMARY KEY,
    tipo       VARCHAR(10) NOT NULL CHECK (tipo IN ('DESPESA', 'RECEITA')),
    descricao  VARCHAR(255) NOT NULL,
    status     VARCHAR(10) NOT NULL DEFAULT 'ATIVO'
               CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS movimento_contas (
    id                SERIAL PRIMARY KEY,
    tipo              VARCHAR(10) NOT NULL
                      CHECK (tipo IN ('APAGAR', 'ARECEBER')),
    numero_documento  VARCHAR(60),
    data_emissao      DATE,
    descricao         TEXT,
    valor_total       NUMERIC(14, 2) NOT NULL,
    pessoa_id         INTEGER NOT NULL REFERENCES pessoas (id),
    faturado_id       INTEGER NOT NULL REFERENCES pessoas (id),
    status            VARCHAR(10) NOT NULL DEFAULT 'ATIVO'
                      CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS movimento_classificacao (
    movimento_id     INTEGER NOT NULL REFERENCES movimento_contas (id),
    classificacao_id INTEGER NOT NULL REFERENCES classificacao (id),
    PRIMARY KEY (movimento_id, classificacao_id)
);

CREATE TABLE IF NOT EXISTS parcela_contas (
    id               SERIAL PRIMARY KEY,
    movimento_id     INTEGER NOT NULL REFERENCES movimento_contas (id),
    identificacao    VARCHAR(20) NOT NULL,
    numero           INTEGER NOT NULL,
    data_vencimento  DATE NOT NULL,
    valor            NUMERIC(14, 2) NOT NULL,
    status           VARCHAR(10) NOT NULL DEFAULT 'ATIVO'
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


class Conexao:
    """
    Envolve a conexão do psycopg2 para oferecer conn.execute(...),
    usando "?" como marcador de parâmetro. Assim o restante do
    sistema (servicos.py) continua escrevendo SQL do mesmo jeito.
    """

    def __init__(self, bruta):
        self._bruta = bruta

    def execute(self, sql: str, params=None):

        cur = self._bruta.cursor()

        if params is None:
            cur.execute(sql)

        else:
            # "%" literal precisa ser escapado; "?" vira "%s"
            cur.execute(
                sql.replace("%", "%%").replace("?", "%s"),
                tuple(params),
            )

        return cur

    def commit(self):
        self._bruta.commit()

    def rollback(self):
        self._bruta.rollback()

    def close(self):
        self._bruta.close()


def conectar() -> Conexao:

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL não configurada. Defina a URL do PostgreSQL, "
            "ex.: postgresql://usuario:senha@localhost:5432/agrosoft"
        )

    opcoes = {}

    if DATABASE_SCHEMA:

        if not re.fullmatch(r"[a-z_][a-z0-9_]*", DATABASE_SCHEMA):
            raise RuntimeError("DATABASE_SCHEMA inválido.")

        opcoes["options"] = f"-c search_path={DATABASE_SCHEMA}"

    bruta = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.DictCursor,
        **opcoes,
    )

    return Conexao(bruta)


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
    """Cria o schema (se pedido), a função norm() e as tabelas."""

    with transacao() as conn:

        if DATABASE_SCHEMA:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {DATABASE_SCHEMA}")

        conn.execute(SCHEMA)
