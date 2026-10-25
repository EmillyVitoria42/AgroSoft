export type Status = 'ATIVO' | 'INATIVO';

export interface Versao {
  commit: string;
  commitCurto: string;
  data: string | null;
  mensagem: string | null;
  repositorio: string;
}

export interface NotaExtraida {
  numeroNotaFiscal: string | null;
  dataEmissao: string | null;
  fornecedor: {
    razaoSocial: string | null;
    fantasia: string | null;
    cnpj: string | null;
  };
  faturado: {
    nomeCompleto: string | null;
    cpf: string | null;
  };
  produtos: string[];
  quantidadeParcelas: number;
  dataVencimento: string | null;
  valorTotal: number | null;
  classificacaoDespesa: string | null;
  parcelas: { numero: number; dataVencimento: string | null }[];
  classificacoesDespesa: string[];
}

export interface ItemAnalise {
  nome: string | null;
  documentoRotulo: string;
  documento: string | null;
  existe: boolean;
  id: number | null;
  status: Status | null;
}

export interface DespesaAnalise {
  descricao: string;
  existe: boolean;
  id: number | null;
  status: Status | null;
}

export interface Analise {
  fornecedor: ItemAnalise;
  faturado: ItemAnalise;
  despesas: DespesaAnalise[];
  notaDuplicada: { movimentoId: number } | null;
  pendencias: string[];
  podeLancar: boolean;
}

export interface ResultadoLancamento {
  mensagem: string;
  movimentoId: number;
  fornecedorId: number;
  faturadoId: number;
  classificacaoIds: number[];
  criados: { fornecedor: boolean; faturado: boolean; despesas: string[] };
  reativados: string[];
}
