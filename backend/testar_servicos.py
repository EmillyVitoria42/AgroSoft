"""
Teste das regras de negócio no PostgreSQL.

Usa um SCHEMA temporário dentro do banco indicado em DATABASE_URL
(backend/.env ou variável de ambiente). Ele é apagado no final, então
os dados reais não são tocados.

    cd backend
    python testar_servicos.py
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Schema temporário ANTES de importar db
SCHEMA_TESTE = "teste_" + uuid.uuid4().hex[:8]
os.environ["DATABASE_SCHEMA"] = SCHEMA_TESTE

import db                                              # noqa: E402
import servicos as s                                   # noqa: E402
from models import NotaFiscalData                      # noqa: E402
from servicos import ErroNegocio                       # noqa: E402


def esperar_erro(funcao, trecho, status=None):
    try:
        funcao()
    except ErroNegocio as e:
        assert trecho.lower() in e.mensagem.lower(), e.mensagem
        if status:
            assert e.status == status, (e.status, e.mensagem)
        return
    raise AssertionError(f"Deveria falhar com: {trecho}")


def nota(**extra):
    base = {
        "fornecedor": {
            "razaoSocial": "IGUAÇU MAQUINAS LTDA",
            "fantasia": None,
            "cnpj": "11.111.111/0001-00",
        },
        "faturado": {
            "nomeCompleto": "BELTRANO DA SILVA",
            "cpf": "999.999.999-99",
        },
        "numeroNotaFiscal": "12345",
        "dataEmissao": "2025-09-19",
        "produtos": ["GRAXA DE POLIUREIA MP SD 400G", "ANEL O"],
        "quantidadeParcelas": 1,
        "dataVencimento": "2025-10-17",
        "valorTotal": 3086.75,
        "classificacaoDespesa": "MANUTENÇÃO E OPERAÇÃO",
        "parcelas": [{"numero": 1, "dataVencimento": "2025-10-17"}],
        "classificacoesDespesa": ["MANUTENÇÃO E OPERAÇÃO"],
    }
    base.update(extra)
    return NotaFiscalData.model_validate(base)


db.iniciar_banco()

# ---------------------------------------------------------------
# Banco vazio: tudo "NÃO EXISTE"
# ---------------------------------------------------------------
with db.transacao() as conn:
    a = s.analisar_nota(conn, nota())

assert not a["fornecedor"]["existe"]
assert not a["faturado"]["existe"]
assert not a["despesas"][0]["existe"]
assert a["podeLancar"], a["pendencias"]
assert a["fornecedor"]["documento"] == "11.111.111/0001-00"
assert a["fornecedor"]["documentoRotulo"] == "CNPJ"
assert a["faturado"]["documentoRotulo"] == "CPF"

# ---------------------------------------------------------------
# Cenário do documento: fornecedor NÃO existe; faturado e despesa
# EXISTEM (cadastrados antes)
# ---------------------------------------------------------------
with db.transacao() as conn:
    id_fat = s.criar_pessoa(
        conn, "FATURADO", "Beltrano da Silva", None, "99999999999"
    )
    id_desp = s.criar_classificacao(
        conn, "DESPESA", "Manutenção e Operação"
    )

with db.transacao() as conn:
    a = s.analisar_nota(conn, nota())

assert a["fornecedor"]["existe"] is False
assert a["faturado"] == {
    "nome": "BELTRANO DA SILVA",
    "documentoRotulo": "CPF",
    "documento": "999.999.999-99",
    "existe": True,
    "id": id_fat,
    "status": "ATIVO",
}
assert a["despesas"][0]["existe"] and a["despesas"][0]["id"] == id_desp

# ---------------------------------------------------------------
# Lançamento: cria só o fornecedor + movimento + parcela
# ---------------------------------------------------------------
with db.transacao() as conn:
    r = s.lancar_nota(conn, nota())

assert r["mensagem"] == "Registro lançado com sucesso!"
assert r["criados"] == {
    "fornecedor": True, "faturado": False, "despesas": []
}
assert r["faturadoId"] == id_fat

with db.transacao() as conn:
    mov = s.obter_movimento(conn, r["movimentoId"])

assert mov["tipo"] == "APAGAR" and mov["status"] == "ATIVO"
assert mov["valorTotal"] == 3086.75
assert mov["classificacoes"] == "MANUTENÇÃO E OPERAÇÃO"
assert [p["identificacao"] for p in mov["parcelasDetalhe"]] == ["ÚNICA"]
assert mov["parcelasDetalhe"][0]["dataVencimento"] == "2025-10-17"
assert mov["parcelasDetalhe"][0]["valor"] == 3086.75

# Agora o fornecedor EXISTE; a mesma nota não pode ser lançada 2x
with db.transacao() as conn:
    a = s.analisar_nota(conn, nota())

assert a["fornecedor"]["existe"] and a["fornecedor"]["id"] == r["fornecedorId"]
assert a["notaDuplicada"] and not a["podeLancar"]

with db.transacao() as conn:
    esperar_erro(lambda: s.lancar_nota(conn, nota()), "já foi lançada")

# ---------------------------------------------------------------
# Nota em 3 parcelas (divisão com centavos) e 2 despesas
# ---------------------------------------------------------------
n2 = nota(
    numeroNotaFiscal="999",
    valorTotal=100.00,
    classificacaoDespesa="INSUMOS AGRÍCOLAS",
    classificacoesDespesa=["INSUMOS AGRÍCOLAS", "SERVIÇOS OPERACIONAIS"],
    parcelas=[
        {"numero": 1, "dataVencimento": "2025-11-01"},
        {"numero": 2, "dataVencimento": "2025-12-01"},
        {"numero": 3, "dataVencimento": "2026-01-01"},
    ],
    quantidadeParcelas=3,
)

with db.transacao() as conn:
    r2 = s.lancar_nota(conn, n2)
    mov2 = s.obter_movimento(conn, r2["movimentoId"])

assert r2["criados"]["despesas"] == [
    "INSUMOS AGRÍCOLAS", "SERVIÇOS OPERACIONAIS"
]
assert [p["identificacao"] for p in mov2["parcelasDetalhe"]] == [
    "1/3", "2/3", "3/3"
]
assert [p["valor"] for p in mov2["parcelasDetalhe"]] == [33.33, 33.33, 33.34]
assert sum(p["valor"] for p in mov2["parcelasDetalhe"]) == 100.0

# ---------------------------------------------------------------
# Pendências bloqueiam o lançamento e NADA é gravado
# ---------------------------------------------------------------
sem_venc = nota(
    numeroNotaFiscal="555", dataVencimento=None, parcelas=[]
)

with db.transacao() as conn:
    a = s.analisar_nota(conn, sem_venc)

assert not a["podeLancar"]
assert any("vencimento" in p.lower() for p in a["pendencias"])

with db.transacao() as conn:
    antes = conn.execute("SELECT count(*) FROM movimento_contas").fetchone()[0]

try:
    with db.transacao() as conn:
        s.lancar_nota(conn, sem_venc)
except ErroNegocio:
    pass

with db.transacao() as conn:
    depois = conn.execute("SELECT count(*) FROM movimento_contas").fetchone()[0]

assert antes == depois

# ---------------------------------------------------------------
# Cadastros: nunca excluir, só INATIVAR / REATIVAR
# ---------------------------------------------------------------
with db.transacao() as conn:
    forn = r["fornecedorId"]
    s.alterar_status_pessoa(conn, forn, "INATIVO")

    ativos = s.listar_pessoas(conn, "CLIENTE-FORNECEDOR", None, "ATIVO")
    inativos = s.listar_pessoas(conn, "CLIENTE-FORNECEDOR", None, "INATIVO")

assert ativos == [] and [p["id"] for p in inativos] == [forn]

# fornecedor INATIVO continua "EXISTE" (com status) e é reativado
with db.transacao() as conn:
    a = s.analisar_nota(conn, nota(numeroNotaFiscal="777"))

assert a["fornecedor"]["existe"] and a["fornecedor"]["status"] == "INATIVO"

with db.transacao() as conn:
    r3 = s.lancar_nota(conn, nota(numeroNotaFiscal="777"))

assert r3["reativados"] == ["fornecedor"]

with db.transacao() as conn:
    assert s.listar_pessoas(conn, "CLIENTE-FORNECEDOR", None, "ATIVO")

# duplicidade / validações
with db.transacao() as conn:
    esperar_erro(
        lambda: s.criar_pessoa(
            conn, "FATURADO", "Outro", None, "999.999.999-99"
        ),
        "já existe", 409,
    )
    esperar_erro(
        lambda: s.criar_pessoa(conn, "FATURADO", "X", None, "123"),
        "documento inválido",
    )
    esperar_erro(
        lambda: s.criar_classificacao(conn, "DESPESA", "manutencao e operacao"),
        "já existe", 409,
    )

# busca por mais de um elemento (AND), sem acento e por CNPJ
with db.transacao() as conn:
    assert len(s.listar_pessoas(conn, "CLIENTE-FORNECEDOR", "iguacu maquinas", "ATIVO")) == 1
    assert len(s.listar_pessoas(conn, "CLIENTE-FORNECEDOR", "iguacu 11.111.111/0001", "ATIVO")) == 1
    assert len(s.listar_pessoas(conn, "CLIENTE-FORNECEDOR", "iguacu xyz", "ATIVO")) == 0
    assert len(s.listar_movimentos(conn, "APAGAR", "iguacu manutencao", "ATIVO")) == 2

# inativar movimento inativa as parcelas
with db.transacao() as conn:
    s.alterar_status_movimento(conn, r["movimentoId"], "INATIVO")
    assert s.listar_movimentos(conn, "APAGAR", "12345", "ATIVO") == []
    assert len(s.listar_movimentos(conn, "APAGAR", "12345", "INATIVO")) == 1
    assert conn.execute(
        "SELECT status FROM parcela_contas WHERE movimento_id = ?",
        (r["movimentoId"],),
    ).fetchone()[0] == "INATIVO"

# ---------------------------------------------------------------
# Conta a RECEBER manual (receita + parcelas informadas)
# ---------------------------------------------------------------
with db.transacao() as conn:
    cliente = s.criar_pessoa(
        conn, "CLIENTE-FORNECEDOR", "Cooperativa Boa Safra", None, "22222222000100"
    )
    receita = s.criar_classificacao(conn, "RECEITA", "Venda de Soja")

    mid = s.criar_movimento(
        conn,
        tipo="ARECEBER",
        pessoa_id=cliente,
        faturado_id=id_fat,
        classificacao_ids=[receita],
        valor_total=1000,
        parcelas=[
            {"dataVencimento": "2026-03-01", "valor": 400},
            {"dataVencimento": "2026-02-01", "valor": 600},
        ],
    )
    m = s.obter_movimento(conn, mid)

# parcelas ordenadas por vencimento
assert [(p["identificacao"], p["valor"]) for p in m["parcelasDetalhe"]] == [
    ("1/2", 600.0), ("2/2", 400.0)
]

with db.transacao() as conn:
    # despesa não pode classificar uma conta a receber
    esperar_erro(
        lambda: s.criar_movimento(
            conn, tipo="ARECEBER", pessoa_id=cliente, faturado_id=id_fat,
            classificacao_ids=[id_desp], valor_total=10,
            parcelas=[{"dataVencimento": "2026-03-01"}],
        ),
        "inválida",
    )
    # soma das parcelas diferente do total
    esperar_erro(
        lambda: s.criar_movimento(
            conn, tipo="ARECEBER", pessoa_id=cliente, faturado_id=id_fat,
            classificacao_ids=[receita], valor_total=10,
            parcelas=[{"dataVencimento": "2026-03-01", "valor": 3}],
        ),
        "soma das parcelas",
    )

# ---------------------------------------------------------------
# Limpeza: apaga o schema temporário
# ---------------------------------------------------------------
db.DATABASE_SCHEMA = ""

with db.transacao() as conn:
    conn.execute(f"DROP SCHEMA {SCHEMA_TESTE} CASCADE")

print("TODOS OS TESTES PASSARAM")
