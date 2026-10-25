import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { api } from '../api';
import type { Status } from '../types';

export interface Campo {
  nome: string;
  rotulo: string;
  obrigatorio?: boolean;
  placeholder?: string;
}

export interface Coluna {
  chave: string;
  rotulo: string;
}

interface Props {
  titulo: string;
  descricao: string;
  /** '/api/pessoas' ou '/api/classificacoes' */
  endpoint: string;
  /** valor do filtro "tipo" (ex.: FATURADO, DESPESA) */
  tipo: string;
  campos: Campo[];
  colunas: Coluna[];
}

type Registro = Record<string, any> & { id: number; status: Status };

/**
 * Tela de manutenção de cadastros (layout recomendado):
 * - tabela começa vazia;
 * - dados vêm pela BUSCA (mais de um elemento) ou por TODOS (ATIVOS);
 * - clique no título da coluna ordena;
 * - ações: Editar / Excluir (lógico = INATIVO) e Reativar;
 * - STATUS é oculto: ATIVO no cadastro; Excluir -> INATIVO.
 */
export function CrudPage({ titulo, descricao, endpoint, tipo, campos, colunas }: Props) {
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [termo, setTermo] = useState('');
  const [situacao, setSituacao] = useState<Status>('ATIVO');
  const [ordem, setOrdem] = useState<{ chave: string; asc: boolean }>({ chave: 'id', asc: true });
  const [form, setForm] = useState<{ id?: number; valores: Record<string, string> } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [consultou, setConsultou] = useState(false);

  const carregar = async (q: string, status: Status) => {
    setCarregando(true);
    setErro(null);

    try {
      const params = new URLSearchParams({ tipo, status });
      if (q.trim()) params.set('q', q.trim());

      setRegistros(await api<Registro[]>(`${endpoint}?${params}`));
      setConsultou(true);
    } catch (e: any) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  };

  const buscar = (e?: React.FormEvent) => {
    e?.preventDefault();
    setAviso(null);
    carregar(termo, situacao);
  };

  // TODOS: carrega todos os registros com STATUS = ATIVO
  const todos = () => {
    setTermo('');
    setSituacao('ATIVO');
    setAviso(null);
    carregar('', 'ATIVO');
  };

  const ordenados = useMemo(() => {
    const lista = [...registros];

    lista.sort((a, b) => {
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

  const alternarOrdem = (chave: string) =>
    setOrdem((o) => ({ chave, asc: o.chave === chave ? !o.asc : true }));

  const novo = () => {
    setErro(null);
    setAviso(null);
    setForm({ valores: Object.fromEntries(campos.map((c) => [c.nome, ''])) });
  };

  const editar = (r: Registro) => {
    setErro(null);
    setAviso(null);
    setForm({
      id: r.id,
      valores: Object.fromEntries(campos.map((c) => [c.nome, r[c.nome] ?? ''])),
    });
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;

    setSalvando(true);
    setErro(null);

    try {
      if (form.id) {
        await api(`${endpoint}/${form.id}`, { method: 'PUT', json: form.valores });
      } else {
        await api(endpoint, { method: 'POST', json: { tipo, ...form.valores } });
      }

      setAviso(form.id ? 'Cadastro atualizado com sucesso.' : 'Cadastro criado com sucesso.');
      setForm(null);
      await carregar(termo, situacao);
    } catch (e: any) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (r: Registro) => {
    if (!window.confirm('Excluir este cadastro? Ele ficará INATIVO e poderá ser reativado.')) return;

    try {
      await api(`${endpoint}/${r.id}`, { method: 'DELETE' });
      setAviso('Cadastro inativado.');
      await carregar(termo, situacao);
    } catch (e: any) {
      setErro(e.message);
    }
  };

  const reativar = async (r: Registro) => {
    try {
      await api(`${endpoint}/${r.id}/reativar`, { method: 'POST' });
      setAviso('Cadastro reativado.');
      await carregar(termo, situacao);
    } catch (e: any) {
      setErro(e.message);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">{titulo}</h2>
        <p className="text-sm text-slate-600">{descricao}</p>
      </div>

      {/* Busca */}
      <form
        onSubmit={buscar}
        className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap gap-2 items-end"
      >
        <label className="flex-1 min-w-[220px] text-xs font-semibold text-slate-500 uppercase">
          Buscar (um ou mais termos)
          <input
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="ex.: iguaçu máquinas 0001"
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm normal-case font-normal text-slate-800 focus:outline-none focus:border-emerald-500"
          />
        </label>

        <label className="text-xs font-semibold text-slate-500 uppercase">
          Situação
          <select
            value={situacao}
            onChange={(e) => setSituacao(e.target.value as Status)}
            className="mt-1 block border border-slate-300 rounded-lg px-3 py-2 text-sm normal-case font-normal text-slate-800"
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
          onClick={todos}
          className="px-4 py-2 border border-emerald-600 text-emerald-700 hover:bg-emerald-50 text-sm font-medium rounded-lg"
        >
          TODOS
        </button>

        <button
          type="button"
          onClick={novo}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" /> Novo
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

      {/* Formulário (STATUS fica oculto) */}
      {form && (
        <form
          onSubmit={salvar}
          className="bg-white p-4 rounded-xl border border-emerald-300 space-y-3"
        >
          <h3 className="font-semibold text-slate-700">
            {form.id ? `Editar cadastro #${form.id}` : 'Novo cadastro'}
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {campos.map((c) => (
              <label key={c.nome} className="text-sm font-medium text-slate-700">
                {c.rotulo}
                {c.obrigatorio && <span className="text-red-500"> *</span>}
                <input
                  value={form.valores[c.nome] ?? ''}
                  required={c.obrigatorio}
                  placeholder={c.placeholder}
                  onChange={(e) =>
                    setForm({ ...form, valores: { ...form.valores, [c.nome]: e.target.value } })
                  }
                  className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 font-normal focus:outline-none focus:border-emerald-500"
                />
              </label>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={salvando}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"
            >
              {salvando && <Loader2 className="w-4 h-4 animate-spin" />} Salvar
            </button>

            <button
              type="button"
              onClick={() => setForm(null)}
              className="px-4 py-2 border border-slate-300 text-slate-700 text-sm rounded-lg"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              {colunas.map((c) => (
                <th
                  key={c.chave}
                  onClick={() => alternarOrdem(c.chave)}
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
              ordenados.map((r) => (
                <tr key={r.id} className={r.status === 'INATIVO' ? 'bg-slate-50 text-slate-400' : ''}>
                  {colunas.map((c) => (
                    <td key={c.chave} className="px-3 py-2">
                      {c.chave === 'status' ? (
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                            r.status === 'ATIVO'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-200 text-slate-600'
                          }`}
                        >
                          {r.status}
                        </span>
                      ) : (
                        r[c.chave] ?? '—'
                      )}
                    </td>
                  ))}

                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => editar(r)}
                      className="px-2 py-1 text-slate-700 hover:bg-slate-100 rounded inline-flex items-center gap-1"
                    >
                      <Pencil className="w-4 h-4" /> Editar
                    </button>

                    {r.status === 'ATIVO' ? (
                      <button
                        onClick={() => excluir(r)}
                        className="px-2 py-1 text-red-600 hover:bg-red-50 rounded inline-flex items-center gap-1"
                      >
                        <Trash2 className="w-4 h-4" /> Excluir
                      </button>
                    ) : (
                      <button
                        onClick={() => reativar(r)}
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
