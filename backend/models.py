from typing import List, Optional

from pydantic import BaseModel, Field


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
