"""
Regras de negócio do AgroSoft (sem dependência do FastAPI).

- Cadastros (PESSOAS e CLASSIFICACAO): criar, editar, listar,
  INATIVAR e REATIVAR. Nunca excluem de verdade.
- Movimentos (contas a pagar / a receber) com parcelas e
  uma ou mais classificações.
- Análise e lançamento de uma Nota Fiscal extraída pela IA.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from db import (
    formatar_documento,
    normalizar_texto,
    rotulo_documento,
    somente_digitos,
)


class ErroNegocio(Exception):
    """Erro de regra de negócio (vira HTTP 4xx na API)."""

    def __init__(self, mensagem: str, status: int = 422):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


STATUS_VALIDOS = ("ATIVO", "INATIVO")

TIPOS_PESSOA = ("CLIENTE-FORNECEDOR", "FATURADO")

TIPOS_CLASSIFICACAO = ("DESPESA", "RECEITA")

TIPOS_MOVIMENTO = ("APAGAR", "ARECEBER")

# APAGAR usa classificação DESPESA; ARECEBER usa RECEITA
CLASSIFICACAO_DO_MOVIMENTO = {
    "APAGAR": "DESPESA",
    "ARECEBER": "RECEITA",
}


# ============================================================
# UTILIDADES
# ============================================================


def _limpar(texto: Optional[str]) -> str:
    """Remove espaços repetidos e das pontas."""

    return re.sub(r"\s+", " ", str(texto or "")).strip()


def _validar_status(status: str) -> str:

    status = (status or "").upper()

    if status not in STATUS_VALIDOS:
        raise ErroNegocio("Status inválido. Use ATIVO ou INATIVO.")

    return status


def _validar_data(valor: Optional[str], campo: str) -> str:

    try:
        return date.fromisoformat(str(valor)).isoformat()

    except (TypeError, ValueError):
        raise ErroNegocio(
            f"{campo} inválida. Use o formato AAAA-MM-DD."
        )


def _termos_busca(q: Optional[str]) -> list[str]:
    """Busca por mais de um elemento: 'maquinas 0001' -> 2 termos."""

    return [t for t in normalizar_texto(q).split(" ") if t]


def _filtro_busca(termos: list[str], blob_sql: str, doc_sql=None):
    """
    Cada termo precisa aparecer (AND) em algum dos campos.
    Retorna (trecho_sql, parametros).
    """

    partes, params = [], []

    for termo in termos:

        condicoes = [f"NORM({blob_sql}) LIKE ?"]
        params.append(f"%{termo}%")

        digitos = somente_digitos(termo)

        if doc_sql and len(digitos) >= 3:
            condicoes.append(f"{doc_sql} LIKE ?")
            params.append(f"%{digitos}%")

        partes.append("(" + " OR ".join(condicoes) + ")")

    return (" AND " + " AND ".join(partes)) if partes else "", params


# ============================================================
# PESSOAS (fornecedor/cliente e faturado)
# ============================================================


def pessoa_para_dict(row) -> dict:

    return {
        "id": row["id"],
        "tipo": row["tipo"],
        "razaoSocial": row["razao_social"],
        "fantasia": row["fantasia"],
        "documento": formatar_documento(row["documento"]),
        "status": row["status"],
    }


def listar_pessoas(conn, tipo: str, q: Optional[str], status: str):

    _validar_tipo(tipo, TIPOS_PESSOA)

    status = _validar_status(status)

    filtro, params = _filtro_busca(
        _termos_busca(q),
        "coalesce(razao_social,'') || ' ' || coalesce(fantasia,'')"
        " || ' ' || coalesce(documento,'') || ' ' || id",
        "documento",
    )

    linhas = conn.execute(
        "SELECT * FROM pessoas WHERE tipo = ? AND status = ?"
        + filtro
        + " ORDER BY razao_social COLLATE NOCASE",
        [tipo, status, *params],
    ).fetchall()

    return [pessoa_para_dict(r) for r in linhas]


def _validar_tipo(tipo: str, validos: tuple) -> str:

    if tipo not in validos:
        raise ErroNegocio(
            "Tipo inválido. Use: " + ", ".join(validos) + "."
        )

    return tipo


def buscar_pessoa(
    conn, tipo: str, documento: Optional[str], nome: Optional[str]
):
    """
    Procura uma pessoa já cadastrada (ATIVA ou INATIVA).

    - Com documento (CNPJ/CPF): compara o documento.
    - Sem documento: compara o nome (sem acento/maiúsculas).
    """

    digitos = somente_digitos(documento)

    if digitos:
        return conn.execute(
            "SELECT * FROM pessoas WHERE tipo = ? AND documento = ?",
            (tipo, digitos),
        ).fetchone()

    nome_norm = normalizar_texto(nome)

    if not nome_norm:
        return None

    return conn.execute(
        "SELECT * FROM pessoas WHERE tipo = ? AND NORM(razao_social) = ?"
        " ORDER BY id LIMIT 1",
        (tipo, nome_norm),
    ).fetchone()


def _checar_pessoa(razao_social, documento) -> tuple[str, str]:

    razao_social = _limpar(razao_social)

    if not razao_social:
        raise ErroNegocio("Informe a Razão Social / Nome.")

    digitos = somente_digitos(documento)

    if digitos and len(digitos) not in (11, 14):
        raise ErroNegocio(
            "Documento inválido: informe um CPF (11 dígitos) "
            "ou CNPJ (14 dígitos)."
        )

    return razao_social, digitos


def _conflito_pessoa(
    conn, tipo, razao_social, digitos, ignorar_id=None
):

    existente = buscar_pessoa(conn, tipo, digitos, razao_social)

    if existente is not None and existente["id"] != ignorar_id:

        raise ErroNegocio(
            f"Já existe cadastro com esses dados "
            f"(ID {existente['id']}, {existente['status']}). "
            + (
                "Reative o registro existente."
                if existente["status"] == "INATIVO"
                else "Edite o registro existente."
            ),
            409,
        )


def criar_pessoa(
    conn, tipo, razao_social, fantasia=None, documento=None
) -> int:
    """Cria PESSOA. O status nasce sempre ATIVO."""

    _validar_tipo(tipo, TIPOS_PESSOA)

    razao_social, digitos = _checar_pessoa(razao_social, documento)

    _conflito_pessoa(conn, tipo, razao_social, digitos)

    cur = conn.execute(
        "INSERT INTO pessoas (tipo, razao_social, fantasia, documento, "
        "status) VALUES (?, ?, ?, ?, 'ATIVO')",
        (
            tipo,
            razao_social,
            _limpar(fantasia) or None,
            digitos or None,
        ),
    )

    return cur.lastrowid


def atualizar_pessoa(
    conn, pessoa_id, razao_social, fantasia=None, documento=None
):
    """Edita PESSOA. O status (oculto) não é alterado aqui."""

    atual = conn.execute(
        "SELECT * FROM pessoas WHERE id = ?", (pessoa_id,)
    ).fetchone()

    if atual is None:
        raise ErroNegocio("Cadastro não encontrado.", 404)

    razao_social, digitos = _checar_pessoa(razao_social, documento)

    _conflito_pessoa(
        conn, atual["tipo"], razao_social, digitos, pessoa_id
    )

    conn.execute(
        "UPDATE pessoas SET razao_social = ?, fantasia = ?, "
        "documento = ? WHERE id = ?",
        (
            razao_social,
            _limpar(fantasia) or None,
            digitos or None,
            pessoa_id,
        ),
    )


def alterar_status_pessoa(conn, pessoa_id, status):

    status = _validar_status(status)

    cur = conn.execute(
        "UPDATE pessoas SET status = ? WHERE id = ?",
        (status, pessoa_id),
    )

    if cur.rowcount == 0:
        raise ErroNegocio("Cadastro não encontrado.", 404)


# ============================================================
# CLASSIFICAÇÃO (tipo de despesa / tipo de receita)
# ============================================================


def classificacao_para_dict(row) -> dict:

    return {
        "id": row["id"],
        "tipo": row["tipo"],
        "descricao": row["descricao"],
        "status": row["status"],
    }


def listar_classificacoes(conn, tipo, q, status):

    _validar_tipo(tipo, TIPOS_CLASSIFICACAO)

    status = _validar_status(status)

    filtro, params = _filtro_busca(
        _termos_busca(q),
        "descricao || ' ' || id",
    )

    linhas = conn.execute(
        "SELECT * FROM classificacao WHERE tipo = ? AND status = ?"
        + filtro
        + " ORDER BY descricao COLLATE NOCASE",
        [tipo, status, *params],
    ).fetchall()

    return [classificacao_para_dict(r) for r in linhas]


def buscar_classificacao(conn, tipo, descricao):

    return conn.execute(
        "SELECT * FROM classificacao WHERE tipo = ? "
        "AND NORM(descricao) = ? ORDER BY id LIMIT 1",
        (tipo, normalizar_texto(descricao)),
    ).fetchone()


def _checar_descricao(conn, tipo, descricao, ignorar_id=None) -> str:

    descricao = _limpar(descricao).upper()

    if not descricao:
        raise ErroNegocio("Informe a descrição.")

    existente = buscar_classificacao(conn, tipo, descricao)

    if existente is not None and existente["id"] != ignorar_id:

        raise ErroNegocio(
            f"Já existe essa descrição (ID {existente['id']}, "
            f"{existente['status']}). "
            + (
                "Reative o registro existente."
                if existente["status"] == "INATIVO"
                else "Edite o registro existente."
            ),
            409,
        )

    return descricao


def criar_classificacao(conn, tipo, descricao) -> int:
    """Cria CLASSIFICACAO. O status nasce sempre ATIVO."""

    _validar_tipo(tipo, TIPOS_CLASSIFICACAO)

    descricao = _checar_descricao(conn, tipo, descricao)

    cur = conn.execute(
        "INSERT INTO classificacao (tipo, descricao, status) "
        "VALUES (?, ?, 'ATIVO')",
        (tipo, descricao),
    )

    return cur.lastrowid


def atualizar_classificacao(conn, classificacao_id, descricao):

    atual = conn.execute(
        "SELECT * FROM classificacao WHERE id = ?",
        (classificacao_id,),
    ).fetchone()

    if atual is None:
        raise ErroNegocio("Cadastro não encontrado.", 404)

    descricao = _checar_descricao(
        conn, atual["tipo"], descricao, classificacao_id
    )

    conn.execute(
        "UPDATE classificacao SET descricao = ? WHERE id = ?",
        (descricao, classificacao_id),
    )


def alterar_status_classificacao(conn, classificacao_id, status):

    status = _validar_status(status)

    cur = conn.execute(
        "UPDATE classificacao SET status = ? WHERE id = ?",
        (status, classificacao_id),
    )

    if cur.rowcount == 0:
        raise ErroNegocio("Cadastro não encontrado.", 404)


# ============================================================
# MOVIMENTOS (contas a pagar / a receber) E PARCELAS
# ============================================================


def _centavos(valor) -> Decimal:

    try:
        return Decimal(str(valor)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    except Exception:
        raise ErroNegocio("Valor inválido.")


def dividir_valor(total: Decimal, quantidade: int) -> list[Decimal]:
    """Divide em partes iguais; a diferença de centavos vai na última."""

    base = (total / quantidade).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    partes = [base] * quantidade

    partes[-1] = total - base * (quantidade - 1)

    return partes


def _preparar_parcelas(valor_total: Decimal, parcelas: list[dict]):
    """
    Valida datas/valores e devolve a lista final ordenada por
    vencimento. Se nenhuma parcela tem valor, divide igualmente.
    """

    if not parcelas:
        raise ErroNegocio("Informe ao menos uma parcela.")

    datas = [
        _validar_data(p.get("dataVencimento"), "Data de vencimento")
        for p in parcelas
    ]

    valores = [p.get("valor") for p in parcelas]

    informados = [v is not None and v != "" for v in valores]

    if any(informados) and not all(informados):
        raise ErroNegocio(
            "Informe o valor de todas as parcelas ou de nenhuma "
            "(nesse caso o total é dividido igualmente)."
        )

    if all(informados):

        decimais = [_centavos(v) for v in valores]

        if any(v <= 0 for v in decimais):
            raise ErroNegocio("O valor das parcelas deve ser positivo.")

        if sum(decimais) != valor_total:
            raise ErroNegocio(
                "A soma das parcelas "
                f"(R$ {sum(decimais):.2f}) é diferente do valor "
                f"total (R$ {valor_total:.2f})."
            )

    else:
        decimais = dividir_valor(valor_total, len(parcelas))

    return sorted(zip(datas, decimais), key=lambda x: x[0])


def criar_movimento(
    conn,
    *,
    tipo: str,
    pessoa_id: int,
    faturado_id: int,
    classificacao_ids: list[int],
    valor_total,
    parcelas: list[dict],
    numero_documento: Optional[str] = None,
    data_emissao: Optional[str] = None,
    descricao: Optional[str] = None,
) -> int:
    """
    Cria o MOVIMENTOCONTAS + suas PARCELACONTAS e vincula uma ou
    mais classificações. Valida todos os vínculos.
    """

    _validar_tipo(tipo, TIPOS_MOVIMENTO)

    total = _centavos(valor_total)

    if total <= 0:
        raise ErroNegocio("O valor total deve ser maior que zero.")

    if data_emissao:
        data_emissao = _validar_data(data_emissao, "Data de emissão")

    # --- vínculos -------------------------------------------------

    pessoa = conn.execute(
        "SELECT * FROM pessoas WHERE id = ?", (pessoa_id,)
    ).fetchone()

    rotulo = "Fornecedor" if tipo == "APAGAR" else "Cliente"

    if (
        pessoa is None
        or pessoa["tipo"] != "CLIENTE-FORNECEDOR"
        or pessoa["status"] != "ATIVO"
    ):
        raise ErroNegocio(f"{rotulo} inválido ou inativo.")

    faturado = conn.execute(
        "SELECT * FROM pessoas WHERE id = ?", (faturado_id,)
    ).fetchone()

    if (
        faturado is None
        or faturado["tipo"] != "FATURADO"
        or faturado["status"] != "ATIVO"
    ):
        raise ErroNegocio("Faturado inválido ou inativo.")

    ids = list(dict.fromkeys(classificacao_ids or []))

    if not ids:
        raise ErroNegocio("Informe ao menos uma classificação.")

    tipo_classificacao = CLASSIFICACAO_DO_MOVIMENTO[tipo]

    for cid in ids:

        c = conn.execute(
            "SELECT * FROM classificacao WHERE id = ?", (cid,)
        ).fetchone()

        if (
            c is None
            or c["tipo"] != tipo_classificacao
            or c["status"] != "ATIVO"
        ):
            raise ErroNegocio(
                f"Classificação {cid} inválida: use apenas tipos de "
                f"{tipo_classificacao} ativos."
            )

    parcelas_finais = _preparar_parcelas(total, parcelas)

    # --- gravação -------------------------------------------------

    cur = conn.execute(
        "INSERT INTO movimento_contas (tipo, numero_documento, "
        "data_emissao, descricao, valor_total, pessoa_id, "
        "faturado_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'ATIVO')",
        (
            tipo,
            _limpar(numero_documento) or None,
            data_emissao or None,
            _limpar(descricao) or None,
            float(total),
            pessoa_id,
            faturado_id,
        ),
    )

    movimento_id = cur.lastrowid

    for cid in ids:
        conn.execute(
            "INSERT INTO movimento_classificacao "
            "(movimento_id, classificacao_id) VALUES (?, ?)",
            (movimento_id, cid),
        )

    quantidade = len(parcelas_finais)

    for numero, (vencimento, valor) in enumerate(
        parcelas_finais, start=1
    ):
        conn.execute(
            "INSERT INTO parcela_contas (movimento_id, identificacao, "
            "numero, data_vencimento, valor, status) "
            "VALUES (?, ?, ?, ?, ?, 'ATIVO')",
            (
                movimento_id,
                "ÚNICA" if quantidade == 1 else f"{numero}/{quantidade}",
                numero,
                vencimento,
                float(valor),
            ),
        )

    return movimento_id


_SQL_MOVIMENTOS = """
SELECT * FROM (
    SELECT
        m.id,
        m.tipo,
        m.numero_documento,
        m.data_emissao,
        m.descricao,
        m.valor_total,
        m.status,
        p.id            AS pessoa_id,
        p.razao_social  AS pessoa,
        f.id            AS faturado_id,
        f.razao_social  AS faturado,
        (SELECT group_concat(c.descricao, ', ')
           FROM movimento_classificacao mc
           JOIN classificacao c ON c.id = mc.classificacao_id
          WHERE mc.movimento_id = m.id) AS classificacoes,
        (SELECT count(*) FROM parcela_contas pc
          WHERE pc.movimento_id = m.id) AS parcelas
    FROM movimento_contas m
    JOIN pessoas p ON p.id = m.pessoa_id
    JOIN pessoas f ON f.id = m.faturado_id
)
WHERE tipo = ? AND status = ?
"""


def movimento_para_dict(row) -> dict:

    return {
        "id": row["id"],
        "tipo": row["tipo"],
        "numeroDocumento": row["numero_documento"],
        "dataEmissao": row["data_emissao"],
        "descricao": row["descricao"],
        "valorTotal": row["valor_total"],
        "status": row["status"],
        "pessoaId": row["pessoa_id"],
        "pessoa": row["pessoa"],
        "faturadoId": row["faturado_id"],
        "faturado": row["faturado"],
        "classificacoes": row["classificacoes"] or "",
        "parcelas": row["parcelas"],
    }


def listar_movimentos(conn, tipo, q, status):

    _validar_tipo(tipo, TIPOS_MOVIMENTO)

    status = _validar_status(status)

    filtro, params = _filtro_busca(
        _termos_busca(q),
        "coalesce(numero_documento,'') || ' ' || coalesce(descricao,'')"
        " || ' ' || pessoa || ' ' || faturado || ' ' || "
        "coalesce(classificacoes,'') || ' ' || id",
    )

    linhas = conn.execute(
        _SQL_MOVIMENTOS + filtro + " ORDER BY id DESC",
        [tipo, status, *params],
    ).fetchall()

    return [movimento_para_dict(r) for r in linhas]


def obter_movimento(conn, movimento_id) -> dict:

    linha = conn.execute(
        _SQL_MOVIMENTOS.replace("WHERE tipo = ? AND status = ?", "WHERE id = ?"),
        (movimento_id,),
    ).fetchone()

    if linha is None:
        raise ErroNegocio("Movimento não encontrado.", 404)

    movimento = movimento_para_dict(linha)

    movimento["parcelasDetalhe"] = [
        {
            "id": p["id"],
            "identificacao": p["identificacao"],
            "numero": p["numero"],
            "dataVencimento": p["data_vencimento"],
            "valor": p["valor"],
        }
        for p in conn.execute(
            "SELECT * FROM parcela_contas WHERE movimento_id = ? "
            "ORDER BY numero",
            (movimento_id,),
        ).fetchall()
    ]

    return movimento


def alterar_status_movimento(conn, movimento_id, status):
    """Inativa/reativa o movimento e suas parcelas (nunca exclui)."""

    status = _validar_status(status)

    cur = conn.execute(
        "UPDATE movimento_contas SET status = ? WHERE id = ?",
        (status, movimento_id),
    )

    if cur.rowcount == 0:
        raise ErroNegocio("Movimento não encontrado.", 404)

    conn.execute(
        "UPDATE parcela_contas SET status = ? WHERE movimento_id = ?",
        (status, movimento_id),
    )


# ============================================================
# NOTA FISCAL: ANÁLISE + LANÇAMENTO
# ============================================================


def _situacao(row) -> dict:
    """Resumo 'existe / não existe' de um cadastro encontrado."""

    if row is None:
        return {"existe": False, "id": None, "status": None}

    return {
        "existe": True,
        "id": row["id"],
        "status": row["status"],
    }


def _despesas_da_nota(nota) -> list[str]:
    """Lista de classificações de despesa (sem repetição)."""

    candidatas = list(nota.classificacoesDespesa or [])

    if not candidatas and nota.classificacaoDespesa:
        candidatas = [nota.classificacaoDespesa]

    vistas, resultado = set(), []

    for c in candidatas:

        c = _limpar(c).upper()

        if c and normalizar_texto(c) not in vistas:
            vistas.add(normalizar_texto(c))
            resultado.append(c)

    return resultado


def _parcelas_da_nota(nota) -> list[dict]:

    lista = [
        {"dataVencimento": p.dataVencimento}
        for p in (nota.parcelas or [])
        if p.dataVencimento
    ]

    if not lista and nota.dataVencimento:
        lista = [{"dataVencimento": nota.dataVencimento}]

    return lista


def analisar_nota(conn, nota) -> dict:
    """
    Consulta o banco e informa se FORNECEDOR, FATURADO e DESPESA
    existem. Também aponta pendências que impedem o lançamento.
    """

    pendencias: list[str] = []

    # --- FORNECEDOR -------------------------------------------------

    forn = nota.fornecedor

    forn_nome = _limpar(forn.razaoSocial)

    forn_doc = somente_digitos(forn.cnpj)

    if not forn_nome:
        pendencias.append("Razão Social do fornecedor não identificada.")

    if forn_doc and len(forn_doc) not in (11, 14):
        pendencias.append("CNPJ do fornecedor inválido.")

    forn_row = (
        buscar_pessoa(conn, "CLIENTE-FORNECEDOR", forn_doc, forn_nome)
        if forn_nome
        else None
    )

    fornecedor = {
        "nome": forn_nome or None,
        "documentoRotulo": rotulo_documento(forn_doc) if forn_doc else "CNPJ",
        "documento": formatar_documento(forn_doc),
        **_situacao(forn_row),
    }

    # --- FATURADO ---------------------------------------------------

    fat = nota.faturado

    fat_nome = _limpar(fat.nomeCompleto)

    fat_doc = somente_digitos(fat.cpf)

    if not fat_nome:
        pendencias.append("Nome do faturado não identificado.")

    if fat_doc and len(fat_doc) not in (11, 14):
        pendencias.append("CPF do faturado inválido.")

    fat_row = (
        buscar_pessoa(conn, "FATURADO", fat_doc, fat_nome)
        if fat_nome
        else None
    )

    faturado = {
        "nome": fat_nome or None,
        "documentoRotulo": rotulo_documento(fat_doc) if fat_doc else "CPF",
        "documento": formatar_documento(fat_doc),
        **_situacao(fat_row),
    }

    # --- DESPESA(S) -------------------------------------------------

    nomes_despesa = _despesas_da_nota(nota)

    if not nomes_despesa:
        pendencias.append("Classificação da despesa não identificada.")

    despesas = [
        {
            "descricao": d,
            **_situacao(buscar_classificacao(conn, "DESPESA", d)),
        }
        for d in nomes_despesa
    ]

    # --- DEMAIS DADOS DO MOVIMENTO ---------------------------------

    if not nota.valorTotal or nota.valorTotal <= 0:
        pendencias.append("Valor total da nota não identificado.")

    parcelas = _parcelas_da_nota(nota)

    if not parcelas:
        pendencias.append("Data de vencimento não identificada.")

    for p in parcelas:
        try:
            date.fromisoformat(p["dataVencimento"])
        except (TypeError, ValueError):
            pendencias.append("Data de vencimento inválida.")
            break

    if nota.dataEmissao:
        try:
            date.fromisoformat(nota.dataEmissao)
        except ValueError:
            pendencias.append("Data de emissão inválida.")

    # --- NOTA JÁ LANÇADA? -------------------------------------------

    duplicada = None

    if forn_row is not None and _limpar(nota.numeroNotaFiscal):

        achado = conn.execute(
            "SELECT id FROM movimento_contas WHERE tipo = 'APAGAR' "
            "AND pessoa_id = ? AND numero_documento = ? "
            "AND status = 'ATIVO' LIMIT 1",
            (forn_row["id"], _limpar(nota.numeroNotaFiscal)),
        ).fetchone()

        if achado is not None:
            duplicada = {"movimentoId": achado["id"]}

            pendencias.append(
                f"Esta nota já foi lançada (movimento {achado['id']})."
            )

    return {
        "fornecedor": fornecedor,
        "faturado": faturado,
        "despesas": despesas,
        "notaDuplicada": duplicada,
        "pendencias": pendencias,
        "podeLancar": not pendencias,
    }


def lancar_nota(conn, nota) -> dict:
    """
    Cria o que não existe (fornecedor, faturado, despesa), reativa o
    que estiver inativo e registra o MOVIMENTO (APAGAR) + PARCELA(S).

    Deve ser chamado dentro de uma transação: se algo falhar, nada
    fica gravado.
    """

    analise = analisar_nota(conn, nota)

    if not analise["podeLancar"]:
        raise ErroNegocio(" ".join(analise["pendencias"]), 422)

    criados = {
        "fornecedor": False,
        "faturado": False,
        "despesas": [],
    }

    reativados: list[str] = []

    # --- FORNECEDOR -------------------------------------------------

    forn = nota.fornecedor

    pessoa_id = analise["fornecedor"]["id"]

    if pessoa_id is None:

        pessoa_id = criar_pessoa(
            conn,
            "CLIENTE-FORNECEDOR",
            forn.razaoSocial,
            forn.fantasia,
            forn.cnpj,
        )

        criados["fornecedor"] = True

    elif analise["fornecedor"]["status"] == "INATIVO":

        alterar_status_pessoa(conn, pessoa_id, "ATIVO")

        reativados.append("fornecedor")

    # --- FATURADO ---------------------------------------------------

    fat = nota.faturado

    faturado_id = analise["faturado"]["id"]

    if faturado_id is None:

        faturado_id = criar_pessoa(
            conn, "FATURADO", fat.nomeCompleto, None, fat.cpf
        )

        criados["faturado"] = True

    elif analise["faturado"]["status"] == "INATIVO":

        alterar_status_pessoa(conn, faturado_id, "ATIVO")

        reativados.append("faturado")

    # --- DESPESA(S) -------------------------------------------------

    classificacao_ids = []

    for d in analise["despesas"]:

        if d["id"] is None:

            cid = criar_classificacao(conn, "DESPESA", d["descricao"])

            criados["despesas"].append(d["descricao"])

        else:

            cid = d["id"]

            if d["status"] == "INATIVO":

                alterar_status_classificacao(conn, cid, "ATIVO")

                reativados.append(f"despesa {d['descricao']}")

        classificacao_ids.append(cid)

    # --- MOVIMENTO + PARCELA(S) ------------------------------------

    movimento_id = criar_movimento(
        conn,
        tipo="APAGAR",
        pessoa_id=pessoa_id,
        faturado_id=faturado_id,
        classificacao_ids=classificacao_ids,
        valor_total=nota.valorTotal,
        parcelas=_parcelas_da_nota(nota),
        numero_documento=nota.numeroNotaFiscal,
        data_emissao=nota.dataEmissao,
        descricao="; ".join(nota.produtos or [])[:500],
    )

    return {
        "mensagem": "Registro lançado com sucesso!",
        "movimentoId": movimento_id,
        "fornecedorId": pessoa_id,
        "faturadoId": faturado_id,
        "classificacaoIds": classificacao_ids,
        "criados": criados,
        "reativados": reativados,
    }
