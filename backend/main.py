import json
import os

from io import BytesIO
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from openai import OpenAI

from pydantic import BaseModel, Field

from pypdf import PdfReader


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ENV_PATH = Path(__file__).parent / ".env"

load_dotenv(
    ENV_PATH,
    override=True
)

MODELO = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="AgroSoft - Processamento de Notas Fiscais",
    description=(
        "API para extração e classificação de "
        "notas fiscais utilizando IA."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELOS / SCHEMAS
# ============================================================


class Fornecedor(BaseModel):
    """
    Dados do fornecedor.
    """

    razaoSocial: Optional[str] = Field(
        None,
        description="Razão Social do fornecedor"
    )

    fantasia: Optional[str] = Field(
        None,
        description="Nome Fantasia do fornecedor"
    )

    cnpj: Optional[str] = Field(
        None,
        description="CNPJ do fornecedor"
    )


class Faturado(BaseModel):
    """
    Dados do faturado/destinatário.
    """

    nomeCompleto: Optional[str] = Field(
        None,
        description="Nome completo do faturado"
    )

    cpf: Optional[str] = Field(
        None,
        description="CPF do faturado"
    )


class Parcela(BaseModel):
    """
    Estrutura preparada para futuras notas
    com mais de uma parcela.
    """

    numero: int = Field(
        1,
        description="Número da parcela"
    )

    dataVencimento: Optional[str] = Field(
        None,
        description="Data de vencimento da parcela"
    )


class NotaFiscalData(BaseModel):
    """
    Estrutura principal retornada pela API.
    """

    fornecedor: Fornecedor

    faturado: Faturado

    numeroNotaFiscal: Optional[str] = Field(
        None,
        description="Número da Nota Fiscal"
    )

    dataEmissao: Optional[str] = Field(
        None,
        description="Data de emissão no formato YYYY-MM-DD"
    )

    produtos: List[str] = Field(
        default_factory=list,
        description=(
            "Descrição dos produtos ou serviços "
            "presentes na nota fiscal"
        )
    )

    quantidadeParcelas: int = Field(
        1,
        description=(
            "Quantidade de parcelas da nota. "
            "Atualmente trabalhamos com uma parcela."
        )
    )

    dataVencimento: Optional[str] = Field(
        None,
        description=(
            "Data de vencimento da nota. "
            "Atualmente corresponde à primeira parcela."
        )
    )

    valorTotal: Optional[float] = Field(
        None,
        description="Valor total da Nota Fiscal"
    )

    classificacaoDespesa: Optional[str] = Field(
        None,
        description=(
            "Classificação da despesa interpretada "
            "a partir dos produtos da nota"
        )
    )

    # --------------------------------------------------------
    # Estrutura futura para múltiplas parcelas
    # --------------------------------------------------------

    parcelas: List[Parcela] = Field(
        default_factory=list,
        description=(
            "Estrutura preparada para receber "
            "uma ou mais parcelas futuramente."
        )
    )

    # --------------------------------------------------------
    # Estrutura futura para múltiplas classificações
    # --------------------------------------------------------

    classificacoesDespesa: List[str] = Field(
        default_factory=list,
        description=(
            "Estrutura preparada para receber "
            "mais de uma classificação de despesa."
        )
    )


# ============================================================
# PROMPT PRINCIPAL DA IA
# ============================================================

PROMPT = """
Você é um sistema especializado em processamento de
Notas Fiscais Eletrônicas (NF-e / DANFE).

Sua função é analisar o texto extraído de uma Nota Fiscal
e retornar SOMENTE as informações solicitadas pelo sistema.

NÃO invente informações.

NÃO complete informações ausentes com suposições.

Quando uma informação obrigatória não estiver disponível,
retorne null.

============================================================
CAMPOS OBRIGATÓRIOS
============================================================

O sistema deve extrair:

1. FORNECEDOR

- Razão Social
- Fantasia
- CNPJ

2. FATURADO

- Nome Completo
- CPF

3. NOTA FISCAL

- Número da Nota Fiscal
- Data de Emissão
- Descrição dos produtos
- Quantidade de Parcelas
- Data de Vencimento
- ValorTotal

4. CLASSIFICAÇÃO DA DESPESA

A classificação NÃO é simplesmente extraída da Nota Fiscal.

A classificação deve ser INTERPRETADA por você com base
nos produtos ou serviços presentes na Nota Fiscal.

============================================================
FORNECEDOR
============================================================

Extraia:

razaoSocial:
Razão Social do fornecedor.

fantasia:
Nome Fantasia do fornecedor, somente se estiver
disponível no documento.

cnpj:
CNPJ do fornecedor.

Não confunda o CNPJ do fornecedor com o CPF/CNPJ
do destinatário.

============================================================
FATURADO
============================================================

Extraia:

nomeCompleto:
Nome completo ou identificação do destinatário/faturado.

cpf:
CPF do faturado.

Se o documento apresentar somente CNPJ para o faturado
e não CPF, não invente um CPF.

============================================================
NÚMERO DA NOTA FISCAL
============================================================

Extraia o número da NF-e.

Não confunda:

- número da nota;
- série;
- chave de acesso;
- protocolo de autorização.

============================================================
DATA DE EMISSÃO
============================================================

Extraia a data de emissão da Nota Fiscal.

Converta para:

YYYY-MM-DD

Exemplo:

19/09/2025

deve ser:

2025-09-19

============================================================
PRODUTOS
============================================================

O campo produtos deve conter somente as descrições
dos produtos ou serviços identificados na Nota Fiscal.

Não é necessário criar uma entidade PRODUTOS.

Exemplo:

[
    "GRAXA DE POLIUREIA MP SD 400G",
    "ANEL O",
    "KIT DA BUCHA"
]

Não coloque códigos dos produtos no campo produtos.

Não coloque NCM no campo produtos.

Não coloque CFOP no campo produtos.

Não coloque preços no campo produtos.

Somente a descrição dos produtos ou serviços.

============================================================
PARCELAS
============================================================

Neste momento o sistema trabalhará com uma parcela.

Se a Nota Fiscal apresentar apenas uma parcela:

quantidadeParcelas = 1

A data de vencimento deve ser extraída da
FATURA/DUPLICATAS da Nota Fiscal.

Exemplo:

001: 17/10/2025 R$3.086,75

deve resultar em:

quantidadeParcelas = 1

dataVencimento = "2025-10-17"

A estrutura de parcelas deve ser preparada para
futuramente receber mais de uma parcela.

Para a situação atual, retorne:

"parcelas": [
    {
        "numero": 1,
        "dataVencimento": "YYYY-MM-DD"
    }
]

Se não houver informação de vencimento,
retorne null para dataVencimento.

============================================================
VALOR TOTAL
============================================================

Extraia o campo:

VALOR TOTAL DA NOTA

Não confunda com:

- valor total dos produtos;
- valor do ICMS;
- valor do frete;
- valor do seguro;
- valor do desconto.

O valorTotal deve ser um número decimal.

Exemplo:

R$ 3.086,75

deve ser:

3086.75

============================================================
CLASSIFICAÇÃO DA DESPESA
============================================================

IMPORTANTE:

DESPESA NÃO É UM CAMPO SIMPLESMENTE EXTRAÍDO DA NOTA.

A DESPESA deve ser INTERPRETADA com base nos produtos
ou serviços presentes na Nota Fiscal.

Neste momento haverá UMA classificação de despesa
por registro.

No futuro o sistema poderá trabalhar com mais de uma
classificação.

A classificação deve ser exatamente uma das categorias
abaixo.

============================================================
1. INSUMOS AGRÍCOLAS
============================================================

Exemplos:

- Sementes
- Fertilizantes
- Defensivos Agrícolas
- Corretivos

============================================================
2. MANUTENÇÃO E OPERAÇÃO
============================================================

Exemplos:

- Combustíveis e Lubrificantes
- Peças
- Parafusos
- Componentes Mecânicos
- Manutenção de Máquinas e Equipamentos
- Pneus
- Filtros
- Correias
- Ferramentas e Utensílios

Exemplo:

Compra de Óleo Diesel

→ MANUTENÇÃO E OPERAÇÃO

Compra de rolamentos e componentes mecânicos

→ MANUTENÇÃO E OPERAÇÃO

============================================================
3. RECURSOS HUMANOS
============================================================

Exemplos:

- Mão de Obra Temporária
- Salários
- Encargos

============================================================
4. SERVIÇOS OPERACIONAIS
============================================================

Exemplos:

- Frete
- Transporte
- Colheita Terceirizada
- Secagem
- Armazenagem
- Pulverização
- Aplicação

============================================================
5. INFRAESTRUTURA E UTILIDADES
============================================================

Exemplos:

- Energia Elétrica
- Arrendamento de Terras
- Construções
- Reformas
- Materiais de Construção

Exemplo:

Compra de Material Hidráulico

→ INFRAESTRUTURA E UTILIDADES

============================================================
6. ADMINISTRATIVAS
============================================================

Exemplos:

- Honorários Contábeis
- Honorários Advocatícios
- Honorários Agronômicos
- Despesas Bancárias
- Despesas Financeiras

============================================================
7. SEGUROS E PROTEÇÃO
============================================================

Exemplos:

- Seguro Agrícola
- Seguro de Ativos
- Seguro de Máquinas
- Seguro de Veículos
- Seguro Prestamista

============================================================
8. IMPOSTOS E TAXAS
============================================================

Exemplos:

- ITR
- IPTU
- IPVA
- INCRA
- CCIR

============================================================
9. INVESTIMENTOS
============================================================

Exemplos:

- Aquisição de Máquinas e Implementos
- Aquisição de Veículos
- Aquisição de Imóveis
- Infraestrutura Rural

============================================================
REGRAS DE CLASSIFICAÇÃO
============================================================

Analise TODOS os produtos da Nota Fiscal antes de
classificar a despesa.

Não classifique somente pelo primeiro produto.

Considere o conjunto dos produtos.

Exemplo:

Nota contendo:

- Rolamento
- Anel
- Bucha
- Graxa
- Peças mecânicas

Classificação:

MANUTENÇÃO E OPERAÇÃO

Exemplo:

Nota contendo:

- Fertilizante
- Adubo
- Corretivo

Classificação:

INSUMOS AGRÍCOLAS

Exemplo:

Nota contendo:

- Cimento
- Tubos
- Conexões hidráulicas
- Material de construção

Classificação:

INFRAESTRUTURA E UTILIDADES

============================================================
CLASSIFICAÇÃO FUTURA
============================================================

Atualmente existe somente:

"classificacaoDespesa"

com uma classificação.

Também retorne:

"classificacoesDespesa"

como uma lista contendo a classificação atual.

Exemplo:

"classificacaoDespesa":
"MANUTENÇÃO E OPERAÇÃO"

"classificacoesDespesa":
[
    "MANUTENÇÃO E OPERAÇÃO"
]

Essa lista existe para permitir futuramente
mais de uma classificação por registro.

============================================================
REGRAS GERAIS
============================================================

1. Não invente informações.

2. Não altere informações presentes na NF-e.

3. Não confunda fornecedor com faturado.

4. Não confunda valor total dos produtos com valor
   total da nota.

5. Não confunda número da NF-e com chave de acesso.

6. Não confunda data de emissão com data de vencimento.

7. Não crie produtos que não estejam no documento.

8. Produtos devem conter somente suas descrições.

9. A classificação da despesa deve ser interpretada
   a partir dos produtos.

10. Use somente as categorias de despesa fornecidas.

11. Caso uma informação não esteja disponível,
    utilize null.

12. A resposta deve ser SOMENTE JSON válido.

13. Não utilize Markdown.

14. Não utilize ```json.

15. Não escreva explicações antes ou depois do JSON.
"""


# ============================================================
# CONFIGURAÇÃO DA GROQ
# ============================================================


def carregar_configuracao():
    """
    Carrega as configurações do arquivo .env.
    """

    load_dotenv(
        ENV_PATH,
        override=True
    )

    api_key = (
        os.getenv("GROQ_API_KEY") or ""
    ).strip()

    modelo = (
        os.getenv("GROQ_MODEL")
        or "openai/gpt-oss-20b"
    ).strip()

    return api_key, modelo


def get_client() -> OpenAI:
    """
    Cria o cliente da Groq utilizando a
    biblioteca compatível com OpenAI.
    """

    api_key, _ = carregar_configuracao()

    if not api_key:

        raise HTTPException(
            status_code=500,
            detail=(
                "GROQ_API_KEY não encontrada. "
                f"Verifique o arquivo: {ENV_PATH}"
            )
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )


# ============================================================
# TRATAMENTO DE ERROS
# ============================================================


def traduzir_erro_api(
    e: Exception
) -> HTTPException:

    mensagem = str(e)

    mensagem_lower = mensagem.lower()

    # Chave inválida
    if (
        "401" in mensagem
        or "invalid_api_key" in mensagem_lower
    ):

        detalhe = (
            "A chave da API Groq foi rejeitada. "
            "Verifique a GROQ_API_KEY no arquivo .env."
        )

    # Limite da API
    elif (
        "429" in mensagem
        or "rate_limit" in mensagem_lower
    ):

        detalhe = (
            "O limite de requisições da Groq "
            "foi atingido. Aguarde e tente novamente."
        )

    # Requisição inválida
    elif "400" in mensagem:

        detalhe = (
            "A requisição enviada para a Groq "
            "é inválida. "
            f"Detalhes: {mensagem}"
        )

    # Outros erros
    else:

        detalhe = (
            "Erro ao comunicar com a API da Groq. "
            f"Detalhes: {mensagem}"
        )

    return HTTPException(
        status_code=502,
        detail=detalhe
    )


# ============================================================
# EXTRAÇÃO DO TEXTO DO PDF
# ============================================================


def extrair_texto_pdf(
    file_bytes: bytes
) -> str:

    """
    Extrai o texto do PDF utilizando pypdf.
    """

    try:

        pdf = PdfReader(
            BytesIO(file_bytes)
        )

        textos = []

        for pagina in pdf.pages:

            texto = pagina.extract_text()

            if texto:

                textos.append(texto)

        texto_final = "\n".join(
            textos
        ).strip()

        return texto_final

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Não foi possível extrair "
                f"texto do PDF: {str(e)}"
            )
        )


# ============================================================
# ROTA DE TESTE DA GROQ
# ============================================================


@app.get("/api/testar-groq")
def testar_groq():

    try:

        client = get_client()

        _, modelo = carregar_configuracao()

        response = client.chat.completions.create(

            model=modelo,

            messages=[
                {
                    "role": "user",
                    "content": "Responda apenas com: OK"
                }
            ],

            temperature=0
        )

        resposta = (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

        return {
            "sucesso": True,
            "modelo": modelo,
            "resposta": resposta
        }

    except Exception as e:

        raise traduzir_erro_api(e)


# ============================================================
# ROTA PRINCIPAL
# ============================================================


@app.post("/api/extrair-nota")
async def extrair_nota(
    file: UploadFile = File(...)
):
    """
    Recebe uma NF-e em PDF e retorna os dados
    estruturados em JSON.

    Fluxo:

    PDF
      ↓
    pypdf
      ↓
    texto
      ↓
    Groq
      ↓
    JSON
      ↓
    Pydantic
      ↓
    resposta da API
    """

    # --------------------------------------------------------
    # 1. Verificar arquivo
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Nenhum arquivo foi enviado."
        )

    filename = (
        file.filename
        .lower()
    )

    if not filename.endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="O arquivo deve estar no formato PDF."
        )

    # --------------------------------------------------------
    # 2. Ler arquivo
    # --------------------------------------------------------

    try:

        file_bytes = await file.read()

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Não foi possível ler o arquivo: "
                f"{str(e)}"
            )
        )

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado está vazio."
        )

    # --------------------------------------------------------
    # 3. Extrair texto
    # --------------------------------------------------------

    texto_pdf = extrair_texto_pdf(
        file_bytes
    )

    if not texto_pdf:

        raise HTTPException(
            status_code=400,
            detail=(
                "Não foi possível extrair texto "
                "do PDF. "
                "O arquivo pode ser um PDF escaneado "
                "ou conter somente imagens."
            )
        )

    # --------------------------------------------------------
    # 4. Configurar Groq
    # --------------------------------------------------------

    client = get_client()

    _, modelo = carregar_configuracao()

    # --------------------------------------------------------
    # 5. Montar prompt
    # --------------------------------------------------------

    prompt_completo = f"""
{PROMPT}

============================================================
TEXTO EXTRAÍDO DA NOTA FISCAL
============================================================

{texto_pdf}

============================================================
FORMATO OBRIGATÓRIO DA RESPOSTA
============================================================

Retorne exatamente um objeto JSON seguindo esta estrutura:

{{
    "fornecedor": {{
        "razaoSocial": null,
        "fantasia": null,
        "cnpj": null
    }},

    "faturado": {{
        "nomeCompleto": null,
        "cpf": null
    }},

    "numeroNotaFiscal": null,

    "dataEmissao": null,

    "produtos": [],

    "quantidadeParcelas": 1,

    "dataVencimento": null,

    "valorTotal": null,

    "classificacaoDespesa": null,

    "parcelas": [],

    "classificacoesDespesa": []
}}

IMPORTANTE:

- fornecedor deve ser um objeto.
- faturado deve ser um objeto.
- produtos deve ser uma lista.
- parcelas deve ser uma lista.
- classificacoesDespesa deve ser uma lista.
- quantidadeParcelas deve ser um número inteiro.
- valorTotal deve ser um número decimal ou null.
- datas devem estar no formato YYYY-MM-DD.
- classificacaoDespesa deve ser exatamente uma das
  categorias permitidas.
- classificacoesDespesa deve conter a classificação atual.
- Não invente informações.
- Retorne SOMENTE JSON.
"""

    # --------------------------------------------------------
    # 6. Chamar Groq
    # --------------------------------------------------------

    try:

        response = client.chat.completions.create(

            model=modelo,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um sistema de extração "
                        "e classificação de notas fiscais. "
                        "Retorne somente JSON válido."
                    )
                },
                {
                    "role": "user",
                    "content": prompt_completo
                }
            ],

            response_format={
                "type": "json_object"
            },

            temperature=0
        )

    except Exception as e:

        print(
            "========================================"
        )

        print("ERRO GROQ:")

        print(str(e))

        print(
            "========================================"
        )

        raise traduzir_erro_api(e)

    # --------------------------------------------------------
    # 7. Verificar resposta
    # --------------------------------------------------------

    if not response:

        raise HTTPException(
            status_code=502,
            detail=(
                "A Groq não retornou nenhuma resposta."
            )
        )

    if not response.choices:

        raise HTTPException(
            status_code=502,
            detail=(
                "A Groq não retornou nenhuma escolha."
            )
        )

    conteudo = (
        response
        .choices[0]
        .message
        .content
    )

    if not conteudo:

        raise HTTPException(
            status_code=502,
            detail=(
                "A Groq retornou uma resposta vazia."
            )
        )

    conteudo = conteudo.strip()

    # --------------------------------------------------------
    # 8. Limpar Markdown caso a IA retorne
    # --------------------------------------------------------

    if conteudo.startswith("```json"):

        conteudo = conteudo[
            len("```json"):
        ].strip()

        if conteudo.endswith("```"):

            conteudo = conteudo[
                :-3
            ].strip()

    elif conteudo.startswith("```"):

        conteudo = conteudo[
            len("```"):
        ].strip()

        if conteudo.endswith("```"):

            conteudo = conteudo[
                :-3
            ].strip()

    # --------------------------------------------------------
    # 9. Converter para JSON
    # --------------------------------------------------------

    try:

        dados = json.loads(
            conteudo
        )

    except json.JSONDecodeError as e:

        print(
            "========================================"
        )

        print(
            "RESPOSTA BRUTA DA GROQ:"
        )

        print(conteudo)

        print(
            "========================================"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "A Groq retornou uma resposta "
                "que não pôde ser convertida "
                f"para JSON: {str(e)}"
            )
        )

    # --------------------------------------------------------
    # 10. Ajustes de compatibilidade
    # --------------------------------------------------------

    # Garante que exista uma lista de produtos
    if not isinstance(
        dados.get("produtos"),
        list
    ):

        dados["produtos"] = []

    # Garante que exista uma lista de parcelas
    if not isinstance(
        dados.get("parcelas"),
        list
    ):

        dados["parcelas"] = []

    # Garante que exista uma lista de classificações
    if not isinstance(
        dados.get("classificacoesDespesa"),
        list
    ):

        dados["classificacoesDespesa"] = []

    # --------------------------------------------------------
    # 11. Preparar estrutura atual de parcela
    # --------------------------------------------------------

    quantidade_parcelas = dados.get(
        "quantidadeParcelas"
    )

    if quantidade_parcelas is None:

        quantidade_parcelas = 1

        dados[
            "quantidadeParcelas"
        ] = 1

    # Atualmente trabalhamos com uma parcela.
    #
    # Se a IA encontrou a data de vencimento,
    # também criamos a estrutura futura de parcelas.

    if (
        quantidade_parcelas == 1
        and dados.get("dataVencimento")
        and not dados.get("parcelas")
    ):

        dados["parcelas"] = [
            {
                "numero": 1,
                "dataVencimento": (
                    dados["dataVencimento"]
                )
            }
        ]

    # --------------------------------------------------------
    # 12. Preparar classificação futura
    # --------------------------------------------------------

    classificacao = dados.get(
        "classificacaoDespesa"
    )

    if (
        classificacao
        and not dados.get(
            "classificacoesDespesa"
        )
    ):

        dados[
            "classificacoesDespesa"
        ] = [
            classificacao
        ]

    # --------------------------------------------------------
    # 13. Validar com Pydantic
    # --------------------------------------------------------

    try:

        nota = NotaFiscalData.model_validate(
            dados
        )

    except Exception as e:

        print(
            "========================================"
        )

        print(
            "JSON RECEBIDO DA GROQ:"
        )

        print(
            json.dumps(
                dados,
                indent=4,
                ensure_ascii=False
            )
        )

        print(
            "========================================"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "A resposta da Groq não corresponde "
                "ao formato esperado: "
                f"{str(e)}"
            )
        )

    # --------------------------------------------------------
    # 14. Retornar JSON
    # --------------------------------------------------------

    return nota.model_dump()


# ============================================================
# ROTA INICIAL
# ============================================================


@app.get("/")
def inicio():

    _, modelo = carregar_configuracao()

    return {
        "projeto": (
            "AgroSoft - Processamento "
            "de Notas Fiscais"
        ),

        "status": "online",

        "modelo": modelo,

        "endpoints": {
            "teste_groq": "/api/testar-groq",
            "extrair_nota": "/api/extrair-nota",
            "documentacao": "/docs"
        }
    }