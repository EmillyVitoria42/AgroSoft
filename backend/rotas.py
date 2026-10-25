"""
Rotas HTTP do AgroSoft (finas: toda a regra está em servicos.py).

Todas exigem login (Bearer token), exceto /api/login e /api/versao.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import servicos
from auth import usuario_atual
from db import transacao
from models import NotaFiscalData
from servicos import ErroNegocio
from versao import obter_versao


router = APIRouter(prefix="/api")

protegido = APIRouter(
    prefix="/api", dependencies=[Depends(usuario_atual)]
)


def erro_http(e: ErroNegocio) -> HTTPException:
    return HTTPException(status_code=e.status, detail=e.mensagem)


# ============================================================
# VERSÃO (pública) - código da última atualização no GitHub
# ============================================================


@router.get("/versao")
def versao():
    return obter_versao()


# ============================================================
# PESSOAS: fornecedor/cliente e faturado
# ============================================================


class PessoaIn(BaseModel):
    tipo: Literal["CLIENTE-FORNECEDOR", "FATURADO"]
    razaoSocial: str
    fantasia: Optional[str] = None
    documento: Optional[str] = None


class PessoaEdicao(BaseModel):
    razaoSocial: str
    fantasia: Optional[str] = None
    documento: Optional[str] = None


@protegido.get("/pessoas")
def listar_pessoas(
    tipo: str,
    q: Optional[str] = None,
    status: str = "ATIVO",
):
    try:
        with transacao() as conn:
            return servicos.listar_pessoas(conn, tipo, q, status)
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.post("/pessoas", status_code=201)
def criar_pessoa(dados: PessoaIn):
    try:
        with transacao() as conn:
            novo_id = servicos.criar_pessoa(
                conn,
                dados.tipo,
                dados.razaoSocial,
                dados.fantasia,
                dados.documento,
            )
        return {"id": novo_id}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.put("/pessoas/{pessoa_id}")
def atualizar_pessoa(pessoa_id: int, dados: PessoaEdicao):
    try:
        with transacao() as conn:
            servicos.atualizar_pessoa(
                conn,
                pessoa_id,
                dados.razaoSocial,
                dados.fantasia,
                dados.documento,
            )
        return {"id": pessoa_id}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.delete("/pessoas/{pessoa_id}")
def inativar_pessoa(pessoa_id: int):
    """Exclusão LÓGICA: STATUS = INATIVO."""
    try:
        with transacao() as conn:
            servicos.alterar_status_pessoa(conn, pessoa_id, "INATIVO")
        return {"id": pessoa_id, "status": "INATIVO"}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.post("/pessoas/{pessoa_id}/reativar")
def reativar_pessoa(pessoa_id: int):
    try:
        with transacao() as conn:
            servicos.alterar_status_pessoa(conn, pessoa_id, "ATIVO")
        return {"id": pessoa_id, "status": "ATIVO"}
    except ErroNegocio as e:
        raise erro_http(e)


# ============================================================
# CLASSIFICAÇÃO: tipo de despesa / tipo de receita
# ============================================================


class ClassificacaoIn(BaseModel):
    tipo: Literal["DESPESA", "RECEITA"]
    descricao: str


class ClassificacaoEdicao(BaseModel):
    descricao: str


@protegido.get("/classificacoes")
def listar_classificacoes(
    tipo: str,
    q: Optional[str] = None,
    status: str = "ATIVO",
):
    try:
        with transacao() as conn:
            return servicos.listar_classificacoes(
                conn, tipo, q, status
            )
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.post("/classificacoes", status_code=201)
def criar_classificacao(dados: ClassificacaoIn):
    try:
        with transacao() as conn:
            novo_id = servicos.criar_classificacao(
                conn, dados.tipo, dados.descricao
            )
        return {"id": novo_id}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.put("/classificacoes/{classificacao_id}")
def atualizar_classificacao(
    classificacao_id: int, dados: ClassificacaoEdicao
):
    try:
        with transacao() as conn:
            servicos.atualizar_classificacao(
                conn, classificacao_id, dados.descricao
            )
        return {"id": classificacao_id}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.delete("/classificacoes/{classificacao_id}")
def inativar_classificacao(classificacao_id: int):
    """Exclusão LÓGICA: STATUS = INATIVO."""
    try:
        with transacao() as conn:
            servicos.alterar_status_classificacao(
                conn, classificacao_id, "INATIVO"
            )
        return {"id": classificacao_id, "status": "INATIVO"}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.post("/classificacoes/{classificacao_id}/reativar")
def reativar_classificacao(classificacao_id: int):
    try:
        with transacao() as conn:
            servicos.alterar_status_classificacao(
                conn, classificacao_id, "ATIVO"
            )
        return {"id": classificacao_id, "status": "ATIVO"}
    except ErroNegocio as e:
        raise erro_http(e)


# ============================================================
# MOVIMENTOS: contas a pagar / a receber
# ============================================================


class ParcelaIn(BaseModel):
    dataVencimento: str
    valor: Optional[float] = None


class MovimentoIn(BaseModel):
    tipo: Literal["APAGAR", "ARECEBER"]
    pessoaId: int
    faturadoId: int
    classificacaoIds: List[int]
    numeroDocumento: Optional[str] = None
    dataEmissao: Optional[str] = None
    descricao: Optional[str] = None
    valorTotal: float
    parcelas: List[ParcelaIn]


@protegido.get("/movimentos")
def listar_movimentos(
    tipo: str,
    q: Optional[str] = None,
    status: str = "ATIVO",
):
    try:
        with transacao() as conn:
            return servicos.listar_movimentos(conn, tipo, q, status)
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.get("/movimentos/{movimento_id}")
def obter_movimento(movimento_id: int):
    try:
        with transacao() as conn:
            return servicos.obter_movimento(conn, movimento_id)
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.post("/movimentos", status_code=201)
def criar_movimento(dados: MovimentoIn):
    try:
        with transacao() as conn:
            novo_id = servicos.criar_movimento(
                conn,
                tipo=dados.tipo,
                pessoa_id=dados.pessoaId,
                faturado_id=dados.faturadoId,
                classificacao_ids=dados.classificacaoIds,
                valor_total=dados.valorTotal,
                parcelas=[p.model_dump() for p in dados.parcelas],
                numero_documento=dados.numeroDocumento,
                data_emissao=dados.dataEmissao,
                descricao=dados.descricao,
            )
        return {"id": novo_id}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.delete("/movimentos/{movimento_id}")
def inativar_movimento(movimento_id: int):
    """Exclusão LÓGICA: STATUS = INATIVO (movimento e parcelas)."""
    try:
        with transacao() as conn:
            servicos.alterar_status_movimento(
                conn, movimento_id, "INATIVO"
            )
        return {"id": movimento_id, "status": "INATIVO"}
    except ErroNegocio as e:
        raise erro_http(e)


@protegido.post("/movimentos/{movimento_id}/reativar")
def reativar_movimento(movimento_id: int):
    try:
        with transacao() as conn:
            servicos.alterar_status_movimento(
                conn, movimento_id, "ATIVO"
            )
        return {"id": movimento_id, "status": "ATIVO"}
    except ErroNegocio as e:
        raise erro_http(e)


# ============================================================
# NOTA FISCAL: análise (consulta) e lançamento
# ============================================================


@protegido.post("/analisar-nota")
def analisar_nota(nota: NotaFiscalData):
    """
    Consulta o banco e informa se FORNECEDOR, FATURADO e DESPESA
    existem (EXISTE - ID: n / NÃO EXISTE). Não grava nada.
    """
    with transacao() as conn:
        return servicos.analisar_nota(conn, nota)


@protegido.post("/lancar-nota", status_code=201)
def lancar_nota(nota: NotaFiscalData):
    """
    Cria fornecedor / faturado / despesa (se for o caso) e registra
    o movimento APAGAR com sua(s) parcela(s) - tudo ou nada.
    """
    try:
        with transacao() as conn:
            return servicos.lancar_nota(conn, nota)
    except ErroNegocio as e:
        raise erro_http(e)
