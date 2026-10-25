import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle,
  Eye,
  Loader2,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { api, dataBR, moeda } from '../api';
import type { Status } from '../types';

interface Props {
  tipo: 'APAGAR' | 'ARECEBER';
}

interface Movimento {
  id: number;
  numeroDocumento: string | null;
  dataEmissao: string | null;
  descricao: string | null;
  valorTotal: number;
  status: Status;
  pessoa: string;
  faturado: string;
  classificacoes: string;
  parcelas: number;
  parcelasDetalhe?: { id: number; identificacao: string; dataVencimento: string; valor: number }[];
}

interface Opcao {
  id: number;
  razaoSocial?: string;
  descricao?: string;
}

interface FormParcela {
  dataVencimento: string;
  valor: string;
}

const COLUNAS = [
  { chave: 'id', rotulo: 'ID' },
  { chave: 'numeroDocumento', rotulo: 'Documento' },
  { chave: 'pessoa', rotulo: '' }, // preenchido conforme o tipo
  { chave: 'faturado', rotulo: 'Faturado' },
  { chave: 'classificacoes', rotulo: '' },
  { chave: 'valorTotal', rotulo: 'Valor' },
  { chave: 'parcelas', rotulo: 'Parcelas' },
  { chave: 'status', rotulo: 'Status' },
];

const FORM_VAZIO = {
  pessoaId: '',
  faturadoId: '',
  numeroDocumento: '',
  dataEmissao: '',
  descricao: '',
  valorTotal: '',
};

/** Registrar contas a pagar (despesas) ou a receber (receitas). */
export function Contas({ tipo }: Props) {
  const pagar = tipo === 'APAGAR';
  const rotuloPessoa = pagar ? 'Fornecedor' : 'Cliente';
  const rotuloClass = pagar ? 'Despesa(s)' : 'Receita(s)';
  const tipoClass = pagar ? 'DESPESA' : 'RECEITA';

  const colunas = COLUNAS.map((c) =>
    c.chave === 'pessoa'
      ? { ...c, rotulo: rotuloPessoa }
      : c.chave === 'classificacoes'
        ? { ...c, rotulo: rotuloClass }
        : c,
  );

  const [registros, setRegistros] = useState<Movimento[]>([]);
  const [termo, setTermo] = useState('');
  const [situacao, setSituacao] = useState<Status>('ATIVO');
  const [ordem, setOrdem] = useState<{ chave: string; asc: boolean }>({ chave: 'id', asc: false });
  const [consultou, setConsultou] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [detalhe, setDetalhe] = useState<Movimento | null>(null);

  // formulário de novo lançamento
  const [aberto, setAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [f, setF] = useState(FORM_VAZIO);
  const [classIds, setClassIds] = useState<number[]>([]);
  const [parcelas, setParcelas] = useState<FormParcela[]>([{ dataVencimento: '', valor: '' }]);
  const [pessoas, setPessoas] = useState<Opcao[]>([]);
  const [faturados, setFaturados] = useState<Opcao[]>([]);
  const [classificacoes, setClassificacoes] = useState<Opcao[]>([]);

  const carregar = async (q: string, status: Status) => {
    setCarregando(true);
    setErro(null);

    try {
      const params = new URLSearchParams({ tipo, status });
      if (q.trim()) params.set('q', q.trim());

      setRegistros(await api<Movimento[]>(`/api/movimentos?${params}`));
      setConsultou(true);
    } catch (e: any) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  };

  const ordenados = useMemo(() => {
    const lista = [...registros];

    lista.sort((a: any, b: any) => {
      const va = a[ordem.chave] ?? '';
      const vb = b[ordem.chave] ?? '';
      const c =
        typeof va === 'number' && typeof vb === 'number'
          ? va - vb
          : String(va).localeCompare(String(vb), 'pt-BR', { numeric: true, sensitivity: 'base' });

      return ordem.asc ? c : -c;
    });

    return lista;
  }, [registros, ordem]);

  const novo = async () => {
    setErro(null);
    setAviso(null);
    setDetalhe(null);

    try {
      const [p, fa, c] = await Promise.all([
        api<Opcao[]>('/api/pessoas?tipo=CLIENTE-FORNECEDOR&status=ATIVO'),
        api<Opcao[]>('/api/pessoas?tipo=FATURADO&status=ATIVO'),
        api<Opcao[]>(`/api/classificacoes?tipo=${tipoClass}&status=ATIVO`),
      ]);

      setPessoas(p);
      setFaturados(fa);
      setClassificacoes(c);
      setF(FORM_VAZIO);
      setClassIds([]);
      setParcelas([{ dataVencimento: '', valor: '' }]);
      setAberto(true);
    } catch (e: any) {
      setErro(e.message);
    }
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    setErro(null);

    try {
      await api('/api/movimentos', {
        json: {
          tipo,
          pessoaId: Number(f.pessoaId),
          faturadoId: Number(f.faturadoId),
          classificacaoIds: classIds,
          numeroDocumento: f.numeroDocumento || null,
          dataEmissao: f.dataEmissao || null,
          descricao: f.descricao || null,
          valorTotal: Number(f.valorTotal.replace(',', '.')),
          parcelas: parcelas.map((p) => ({
            dataVencimento: p.dataVencimento,
            valor: p.valor.trim() ? Number(p.valor.replace(',', '.')) : null,
          })),
        },
      });

      setAberto(false);
      setAviso('Registro lançado com sucesso!');
      await carregar(termo, situacao);
    } catch (e: any) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  };

  const ver = async (m: Movimento) => {
    try {
      setDetalhe(await api<Movimento>(`/api/movimentos/${m.id}`));
    } catch (e: any) {
      setErro(e.message);
    }
  };

  const excluir = async (m: Movimento) => {
    if (!window.confirm('Excluir este lançamento? Ele ficará INATIVO e poderá ser reativado.')) return;

    try {
      await api(`/api/movimentos/${m.id}`, { method: 'DELETE' });
      setAviso('Lançamento inativado.');
      setDetalhe(null);
      await carregar(termo, situacao);
    } catch (e: any) {
      setErro(e.message);
    }
  };

  const reativar = async (m: Movimento) => {
    try {
      await api(`/api/movimentos/${m.id}/reativar`, { method: 'POST' });
      setAviso('Lançamento reativado.');
      await carregar(termo, situacao);
    } catch (e: any) {
      setErro(e.message);
    }
  };

  const input =
    'mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-normal focus:outline-none focus:border-emerald-500';

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">
          Contas a {pagar ? 'Pagar' : 'Receber'}
        </h2>
        <p className="text-sm text-slate-600">
          Cada lançamento pode ter uma ou mais {pagar ? 'despesas' : 'receitas'} e uma ou mais
          parcelas com vencimentos distintos.
          {pagar && ' Notas fiscais também podem ser lançadas automaticamente em "Lançar NF-e".'}
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setAviso(null);
          carregar(termo, situacao);
        }}
        className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap gap-2 items-end"
      >
        <label className="flex-1 min-w-[220px] text-xs font-semibold text-slate-500 uppercase">
          Buscar (um ou mais termos)
          <input
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder={`ex.: ${rotuloPessoa.toLowerCase()} documento classificação`}
            className={input + ' normal-case text-slate-800'}
          />
        </label>

        <label className="text-xs font-semibold text-slate-500 uppercase">
          Situação
          <select
            value={situacao}
            onChange={(e) => setSituacao(e.target.value as Status)}
            className={input + ' normal-case text-slate-800'}
          >
            <option value="ATIVO">Ativos</option>
            <option value="INATIVO">Inativos</option>
          </select>
        </label>

        <button
          type="submit"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"
        >
          <Search className="w-4 h-4" /> Buscar
        </button>

        <button
          type="button"
          onClick={() => {
            setTermo('');
            setSituacao('ATIVO');
            setAviso(null);
            carregar('', 'ATIVO');
          }}
          className="px-4 py-2 border border-emerald-600 text-emerald-700 hover:bg-emerald-50 text-sm font-medium rounded-lg"
        >
          TODOS
        </button>

        <button
          type="button"
          onClick={novo}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" /> Novo lançamento
        </button>
      </form>

      {aviso && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle className="w-4 h-4 flex-shrink-0" /> {aviso}
        </div>
      )}

      {erro && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> {erro}
        </div>
      )}

      {/* Novo lançamento */}
      {aberto && (
        <form onSubmit={salvar} className="bg-white p-4 rounded-xl border border-emerald-300 space-y-4">
          <h3 className="font-semibold text-slate-700">
            Novo lançamento – conta a {pagar ? 'pagar' : 'receber'}
          </h3>

          {(pessoas.length === 0 || faturados.length === 0 || classificacoes.length === 0) && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-sm">
              Antes de lançar, cadastre ao menos: 1 {rotuloPessoa.toLowerCase()}, 1 faturado e 1 tipo
              de {pagar ? 'despesa' : 'receita'} (menu acima).
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-sm font-medium text-slate-700">
              {rotuloPessoa} *
              <select
                required
                value={f.pessoaId}
                onChange={(e) => setF({ ...f, pessoaId: e.target.value })}
                className={input}
              >
                <option value="">Selecione…</option>
                {pessoas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.razaoSocial}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium text-slate-700">
              Faturado *
              <select
                required
                value={f.faturadoId}
                onChange={(e) => setF({ ...f, faturadoId: e.target.value })}
                className={input}
              >
                <option value="">Selecione…</option>
                {faturados.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.razaoSocial}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium text-slate-700">
              Nº do documento
              <input
                value={f.numeroDocumento}
                onChange={(e) => setF({ ...f, numeroDocumento: e.target.value })}
                className={input}
              />
            </label>

            <label className="text-sm font-medium text-slate-700">
              Data de emissão
              <input
                type="date"
                value={f.dataEmissao}
                onChange={(e) => setF({ ...f, dataEmissao: e.target.value })}
                className={input}
              />
            </label>

            <label className="text-sm font-medium text-slate-700">
              Valor total (R$) *
              <input
                required
                inputMode="decimal"
                value={f.valorTotal}
                onChange={(e) => setF({ ...f, valorTotal: e.target.value })}
                placeholder="0,00"
                className={input}
              />
            </label>

            <label className="text-sm font-medium text-slate-700">
              Descrição
              <input
                value={f.descricao}
                onChange={(e) => setF({ ...f, descricao: e.target.value })}
                className={input}
              />
            </label>
          </div>

          <fieldset>
            <legend className="text-sm font-medium text-slate-700">
              {rotuloClass} * (uma ou mais)
            </legend>

            <div className="mt-1 flex flex-wrap gap-2">
              {classificacoes.map((c) => {
                const marcado = classIds.includes(c.id);

                return (
                  <label
                    key={c.id}
                    className={`px-3 py-1.5 rounded-full border text-sm cursor-pointer ${
                      marcado
                        ? 'bg-emerald-100 border-emerald-500 text-emerald-900'
                        : 'border-slate-300 text-slate-700'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="hidden"
                      checked={marcado}
                      onChange={() =>
                        setClassIds(marcado ? classIds.filter((i) => i !== c.id) : [...classIds, c.id])
                      }
                    />
                    {c.descricao}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-700">
              Parcelas * <span className="font-normal text-slate-500">
                (deixe o valor em branco para dividir o total igualmente)
              </span>
            </legend>

            {parcelas.map((p, i) => (
              <div key={i} className="flex gap-2 items-center">
                <span className="text-sm text-slate-500 w-6">{i + 1}.</span>

                <input
                  type="date"
                  required
                  value={p.dataVencimento}
                  onChange={(e) =>
                    setParcelas(parcelas.map((x, j) => (j === i ? { ...x, dataVencimento: e.target.value } : x)))
                  }
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />

                <input
                  inputMode="decimal"
                  placeholder="valor (opcional)"
                  value={p.valor}
                  onChange={(e) =>
                    setParcelas(parcelas.map((x, j) => (j === i ? { ...x, valor: e.target.value } : x)))
                  }
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-40"
                />

                {parcelas.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setParcelas(parcelas.filter((_, j) => j !== i))}
                    className="p-1.5 text-slate-500 hover:text-red-600"
                    aria-label="Remover parcela"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}

            <button
              type="button"
              onClick={() => setParcelas([...parcelas, { dataVencimento: '', valor: '' }])}
              className="text-sm text-emerald-700 hover:underline flex items-center gap-1"
            >
              <Plus className="w-4 h-4" /> Adicionar parcela
            </button>
          </fieldset>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={salvando || classIds.length === 0}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"
            >
              {salvando && <Loader2 className="w-4 h-4 animate-spin" />} Lançar
            </button>

            <button
              type="button"
              onClick={() => setAberto(false)}
              className="px-4 py-2 border border-slate-300 text-slate-700 text-sm rounded-lg"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {/* Detalhe */}
      {detalhe && (
        <div className="bg-white p-4 rounded-xl border border-slate-300 space-y-2">
          <div className="flex justify-between items-start">
            <h3 className="font-semibold text-slate-700">
              Lançamento #{detalhe.id} – {detalhe.pessoa}
            </h3>
            <button onClick={() => setDetalhe(null)} aria-label="Fechar">
              <X className="w-4 h-4 text-slate-500" />
            </button>
          </div>

          <p className="text-sm text-slate-600">
            Faturado: {detalhe.faturado} · {rotuloClass}: {detalhe.classificacoes} · Emissão{' '}
            {dataBR(detalhe.dataEmissao)}
          </p>

          {detalhe.descricao && <p className="text-sm text-slate-500">{detalhe.descricao}</p>}

          <table className="text-sm w-full max-w-md">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="py-1">Parcela</th>
                <th>Vencimento</th>
                <th className="text-right">Valor</th>
              </tr>
            </thead>
            <tbody>
              {detalhe.parcelasDetalhe?.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="py-1">{p.identificacao}</td>
                  <td>{dataBR(p.dataVencimento)}</td>
                  <td className="text-right">{moeda(p.valor)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              {colunas.map((c) => (
                <th
                  key={c.chave}
                  onClick={() => setOrdem((o) => ({ chave: c.chave, asc: o.chave === c.chave ? !o.asc : true }))}
                  className="px-3 py-2 text-left font-semibold cursor-pointer select-none whitespace-nowrap hover:bg-slate-200"
                >
                  <span className="inline-flex items-center gap-1">
                    {c.rotulo}
                    {ordem.chave === c.chave &&
                      (ordem.asc ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                  </span>
                </th>
              ))}
              <th className="px-3 py-2 text-right font-semibold">Ações</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {carregando && (
              <tr>
                <td colSpan={colunas.length + 1} className="px-3 py-6 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin inline" />
                </td>
              </tr>
            )}

            {!carregando && ordenados.length === 0 && (
              <tr>
                <td colSpan={colunas.length + 1} className="px-3 py-6 text-center text-slate-400">
                  {consultou
                    ? 'Nenhum registro encontrado.'
                    : 'Use a busca ou clique em TODOS para carregar os registros.'}
                </td>
              </tr>
            )}

            {!carregando &&
              ordenados.map((m) => (
                <tr key={m.id} className={m.status === 'INATIVO' ? 'bg-slate-50 text-slate-400' : ''}>
                  <td className="px-3 py-2">{m.id}</td>
                  <td className="px-3 py-2">{m.numeroDocumento ?? '—'}</td>
                  <td className="px-3 py-2">{m.pessoa}</td>
                  <td className="px-3 py-2">{m.faturado}</td>
                  <td className="px-3 py-2">{m.classificacoes}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{moeda(m.valorTotal)}</td>
                  <td className="px-3 py-2">{m.parcelas}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        m.status === 'ATIVO' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => ver(m)}
                      className="px-2 py-1 text-slate-700 hover:bg-slate-100 rounded inline-flex items-center gap-1"
                    >
                      <Eye className="w-4 h-4" /> Parcelas
                    </button>

                    {m.status === 'ATIVO' ? (
                      <button
                        onClick={() => excluir(m)}
                        className="px-2 py-1 text-red-600 hover:bg-red-50 rounded inline-flex items-center gap-1"
                      >
                        <Trash2 className="w-4 h-4" /> Excluir
                      </button>
                    ) : (
                      <button
                        onClick={() => reativar(m)}
                        className="px-2 py-1 text-emerald-700 hover:bg-emerald-50 rounded inline-flex items-center gap-1"
                      >
                        <RotateCcw className="w-4 h-4" /> Reativar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
