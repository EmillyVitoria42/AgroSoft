import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

ENV_PATH = Path(__file__).parent / ".env"
MODELO = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas Pydantic para Structured Output ---
class Fornecedor(BaseModel):
    razaoSocial: Optional[str] = Field(None, description="Razão social do fornecedor")
    nomeFantasia: Optional[str] = Field(None, description="Nome fantasia do fornecedor")
    cnpj: Optional[str] = Field(None, description="CNPJ do fornecedor")


class Faturado(BaseModel):
    nomeCompleto: Optional[str] = Field(
        None, description="Nome ou razão social do comprador"
    )
    cpf: Optional[str] = Field(None, description="CPF ou CNPJ do comprador")


class NotaFiscalData(BaseModel):
    numero: Optional[str] = Field(None, description="Número da nota fiscal")
    dataEmissao: Optional[str] = Field(
        None, description="Data de emissão no formato YYYY-MM-DD"
    )
    fornecedor: Optional[Fornecedor] = None
    faturado: Optional[Faturado] = None
    produtos: List[str] = Field(
        default_factory=list,
        description="Lista com os nomes dos produtos ou serviços descritos",
    )
    quantidadeParcelas: Optional[int] = Field(
        1, description="Quantidade total de parcelas de pagamento"
    )
    dataVencimento: Optional[str] = Field(
        None,
        description="Data de vencimento da primeira parcela/fatura no formato YYYY-MM-DD",
    )
    valorTotal: Optional[float] = Field(
        None, description="Valor total da nota fiscal em float (ex: 150.50)"
    )
    classificacaoDespesa: Optional[str] = Field(
        None,
        description="Categorização da despesa (ex: 'MANUTENÇÃO E OPERAÇÃO')",
    )


PROMPT = """
Você é um assistente especialista em extração de dados de Documentos Auxiliares da Nota Fiscal Eletrônica (DANFE) e Notas de Serviço.
Analise a nota fiscal em anexo e extraia exatamente as informações solicitadas no schema.

Regra para classificacaoDespesa:
- Se houver peças, rolamentos, graxas, óleos, combustíveis ou itens de manutenção agrícola/mecânica, classifique obrigatoriamente como "MANUTENÇÃO E OPERAÇÃO".
- Se algum campo não for encontrado no documento, retorne null.
"""


def get_client() -> genai.Client:
    """Relê o .env a cada chamada: permite alterar a chave sem reiniciar o servidor."""
    load_dotenv(ENV_PATH, override=True)
    key = (os.getenv("GEMINI_API_KEY") or "").strip().strip("\"'")
    if not key:
        raise HTTPException(
            status_code=400,
            detail=f"GEMINI_API_KEY não encontrada. Verifique o arquivo {ENV_PATH}",
        )
    return genai.Client(api_key=key)


def traduzir_erro_api(e: errors.APIError) -> HTTPException:
    dicas = {
        400: "Requisição/chave inválida (confira a GEMINI_API_KEY).",
        401: "Chave rejeitada pelo Google.",
        403: "Sem permissão: chave restrita, API não habilitada ou região sem acesso.",
        404: f"Modelo '{MODELO}' não encontrado para esta chave.",
        429: "Cota/limite de requisições excedido (aguarde ou use outro modelo/projeto).",
    }
    dica = dicas.get(e.code, "Erro do lado do Google. Tente novamente.")
    return HTTPException(
        status_code=502, detail=f"[{e.code} {e.status}] {dica} | {e.message}"
    )


def obter_mime_type(file: UploadFile) -> str:
    """Garante que o mime_type correto seja enviado ao Gemini mesmo em uploads genéricos."""
    mime_type = file.content_type or ""
    filename = (file.filename or "").lower()

    if mime_type and mime_type != "application/octet-stream":
        return mime_type

    if filename.endswith(".pdf"):
        return "application/pdf"
    elif filename.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    elif filename.endswith(".png"):
        return "image/png"
    elif filename.endswith(".webp"):
        return "image/webp"

    return "application/pdf"


@app.get("/api/testar-gemini")
def testar_gemini():
    """Endpoint para isolar a verificação de conectividade e validação da chave API."""
    try:
        r = get_client().models.generate_content(
            model=MODELO, contents="Responda apenas: ok"
        )
        return {"modelo": MODELO, "resposta": (r.text or "").strip()}
    except errors.APIError as e:
        raise traduzir_erro_api(e)


@app.post("/api/extrair-nota")
async def extrair_nota(file: UploadFile = File(...)):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=400, detail="O arquivo enviado está vazio."
        )

    mime_type = obter_mime_type(file)
    client = get_client()

    try:
        response = client.models.generate_content(
            model=MODELO,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NotaFiscalData,  # Força o Gemini a respeitar estritamente a classe NotaFiscalData
                temperature=0,
            ),
        )
    except errors.APIError as e:
        print("Erro na API Gemini:", e.code, e.status, e.message)
        raise traduzir_erro_api(e)

    if not response.text:
        motivo = getattr(response.prompt_feedback, "block_reason", None)
        finish = (
            response.candidates[0].finish_reason
            if response.candidates
            else None
        )
        raise HTTPException(
            status_code=502,
            detail=f"Gemini devolveu resposta vazia (block_reason={motivo}, finish_reason={finish}).",
        )

    try:
        # Como o response_schema força a saída no padrão do Pydantic, o JSON já vem perfeitamente formatado
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print("Resposta bruta com erro de JSON:", response.text)
        raise HTTPException(
            status_code=502, detail=f"Erro ao decodificar JSON retornado: {e}"
        )