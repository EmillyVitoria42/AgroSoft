import { useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  FileText,
  Loader2,
  RotateCcw,
  Upload,
} from 'lucide-react';
import { api, dataBR, moeda } from '../api';
import type { Analise, NotaExtraida, ResultadoLancamento, Status } from '../types';

/** Bloco no formato pedido: nome, documento e EXISTE – ID / NÃO EXISTE. */
function BlocoConsulta({
  titulo,
  nome,
  documentoRotulo,
  documento,
  existe,
  id,
  status,
}: {
  titulo: string;
  nome: string | null;
  documentoRotulo?: string;
  documento?: string | null;
  existe: boolean;
  id: number | null;
  status: Status | null;
}) {
  return (
    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-0.5">
      <p className="text-xs font-bold text-slate-500 uppercase">{titulo}:</p>

      <p className="font-semibold text-slate-800">{nome ?? '—'}</p>

      {documentoRotulo && documento && (
        <p className="text-sm text-slate-600">
          {documentoRotulo}: {documento}
        </p>
      )}

      {existe ? (
        <p className="font-bold text-emerald-700 pt-1">
          EXISTE – ID: {id}
          {status === 'INATIVO' && (
            <span className="ml-2 text-xs font-semibold text-amber-700">
              (INATIVO – será reativado)
            </span>
          )}
        </p>
      ) : (
        <p className="font-bold text-red-600 pt-1">NÃO EXISTE</p>
      )}
    </div>
  );
}

export function ExtrairNota() {
  const [file, setFile] = useState<File | null>(null);
  const [etapa, setEtapa] = useState<'envio' | 'analisando' | 'analisada' | 'lancando' | 'lancada'>('envio');
  const [nota, setNota] = useState<NotaExtraida | null>(null);
  const [analise, setAnalise] = useState<Analise | null>(null);
  const [resultado, setResultado] = useState<ResultadoLancamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const reiniciar = () => {
    setFile(null);
    setNota(null);
    setAnalise(null);
    setResultado(null);
    setErro(null);
    setEtapa('envio');
  };

  // 1) Extrai com a IA  2) Consulta o banco (EXISTE / NÃO EXISTE)
  const extrairEAnalisar = async () => {
    if (!file) {
      setErro('Por favor, selecione um arquivo PDF da Nota Fiscal.');
      return;
    }

    setErro(null);
    setEtapa('analisando');

    try {
      const form = new FormData();
      form.append('file', file);

      const extraida = await api<NotaExtraida>('/api/extrair-nota', { form });

      setNota(extraida);

      setAnalise(await api<Analise>('/api/analisar-nota', { json: extraida }));

      setEtapa('analisada');
    } catch (e: any) {
      setErro(e.message);
      setEtapa('envio');
    }
  };

  // 3) Cria o que falta e lança o movimento + parcela(s)
  const lancar = async () => {
    if (!nota) return;

    setErro(null);
    setEtapa('lancando');

    try {
      setResultado(await api<ResultadoLancamento>('/api/lancar-nota', { json: nota }));
      setEtapa('lancada');
    } catch (e: any) {
      setErro(e.message);
      setEtapa('analisada');
    }
  };

  const ocupado = etapa === 'analisando' || etapa === 'lancando';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Lançar Nota Fiscal (NF-e)</h2>
        <p className="text-sm text-slate-600">
          Envie o PDF do DANFE: a IA extrai os dados, o sistema consulta o banco e lança a conta a
          pagar.
        </p>
      </div>

      {/* Upload */}
      {(etapa === 'envio' || etapa === 'analisando') && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
          <h3 className="text-lg font-semibold text-slate-700 flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-600" />
            Upload de Documento
          </h3>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-emerald-500 transition-colors">
            <input
              type="file"
              accept=".pdf"
              id="file-upload"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  setFile(e.target.files[0]);
                  setErro(null);
                }
              }}
            />

            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
              <Upload className="w-10 h-10 text-slate-400" />
              <span className="text-slate-600 font-medium">
                {file ? file.name : 'Clique para selecionar o PDF da Nota Fiscal'}
              </span>
              <span className="text-xs text-slate-400">Apenas arquivos no formato PDF</span>
            </label>
          </div>

          <button
            onClick={extrairEAnalisar}
            disabled={!file || ocupado}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-medium rounded-lg flex items-center justify-center gap-2"
          >
            {etapa === 'analisando' ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processando PDF com IA e consultando o banco...
              </>
            ) : (
              'Extrair e Analisar Nota'
            )}
          </button>
        </div>
      )}

      {erro && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{erro}</span>
        </div>
      )}

      {/* Resultado da análise */}
      {nota && analise && etapa !== 'envio' && etapa !== 'analisando' && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-5">
          <div className="flex flex-wrap justify-between items-center gap-2 border-b pb-3">
            <h3 className="text-lg font-semibold text-slate-700 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              Análise dos dados no banco
            </h3>

            <span className="text-sm text-slate-600">
              NF {nota.numeroNotaFiscal ?? '—'} · Emissão {dataBR(nota.dataEmissao)} ·{' '}
              <strong className="text-emerald-700">{moeda(nota.valorTotal)}</strong> · Venc.{' '}
              {nota.parcelas.length > 1
                ? nota.parcelas.map((p) => dataBR(p.dataVencimento)).join(', ')
                : dataBR(nota.parcelas[0]?.dataVencimento ?? nota.dataVencimento)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <BlocoConsulta titulo="FORNECEDOR" {...analise.fornecedor} />
            <BlocoConsulta titulo="FATURADO" {...analise.faturado} />

            {analise.despesas.map((d) => (
              <BlocoConsulta
                key={d.descricao}
                titulo="DESPESA"
                nome={d.descricao}
                existe={d.existe}
                id={d.id}
                status={d.status}
              />
            ))}
          </div>

          {nota.produtos.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-slate-500 font-semibold">
                Itens detectados ({nota.produtos.length})
              </summary>
              <ul className="mt-2 divide-y divide-slate-100 border rounded-lg overflow-hidden">
                {nota.produtos.map((p, i) => (
                  <li key={i} className="p-2 text-slate-700 bg-slate-50/50">
                    {p}
                  </li>
                ))}
              </ul>
            </details>
          )}

          {analise.pendencias.length > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-sm space-y-1">
              <p className="font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> Não é possível lançar esta nota:
              </p>
              <ul className="list-disc ml-6">
                {analise.pendencias.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {etapa !== 'lancada' && (
            <div className="flex flex-wrap gap-2">
              <button
                onClick={lancar}
                disabled={!analise.podeLancar || etapa === 'lancando'}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-medium rounded-lg flex items-center gap-2"
              >
                {etapa === 'lancando' && <Loader2 className="w-4 h-4 animate-spin" />}
                Confirmar e lançar
              </button>

              <button
                onClick={reiniciar}
                disabled={etapa === 'lancando'}
                className="px-5 py-2.5 border border-slate-300 text-slate-700 rounded-lg"
              >
                Cancelar
              </button>
            </div>
          )}

          <details>
            <summary className="cursor-pointer text-xs text-slate-500 font-bold uppercase">
              JSON extraído pela IA
            </summary>
            <pre className="mt-2 p-4 bg-slate-900 text-emerald-400 rounded-lg text-xs overflow-x-auto font-mono">
              {JSON.stringify(nota, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Sucesso */}
      {etapa === 'lancada' && resultado && (
        <div className="p-6 bg-emerald-50 border border-emerald-300 rounded-xl space-y-2">
          <p className="text-lg font-bold text-emerald-800 flex items-center gap-2">
            <CheckCircle className="w-6 h-6" /> {resultado.mensagem}
          </p>

          <ul className="text-sm text-emerald-900 list-disc ml-6">
            <li>
              Conta a pagar nº {resultado.movimentoId} registrada (fornecedor ID{' '}
              {resultado.fornecedorId}, faturado ID {resultado.faturadoId}).
            </li>
            {resultado.criados.fornecedor && <li>Novo fornecedor criado.</li>}
            {resultado.criados.faturado && <li>Novo faturado criado.</li>}
            {resultado.criados.despesas.map((d) => (
              <li key={d}>Nova despesa criada: {d}.</li>
            ))}
            {resultado.reativados.map((r) => (
              <li key={r}>Cadastro reativado: {r}.</li>
            ))}
          </ul>

          <button
            onClick={reiniciar}
            className="mt-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" /> Lançar outra nota
          </button>
        </div>
      )}
    </div>
  );
}
