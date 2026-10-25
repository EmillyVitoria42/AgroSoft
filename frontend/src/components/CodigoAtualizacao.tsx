import { GitCommit } from 'lucide-react';
import type { Versao } from '../types';

/** Código (hash do commit) da última atualização no GitHub. */
export function CodigoAtualizacao({ versao }: { versao: Versao | null }) {
  const disponivel = versao && versao.commit !== 'indisponível';

  return (
    <div className="bg-white border border-slate-200 rounded-lg px-4 py-3 text-xs text-slate-600 space-y-1">
      <p className="flex items-center gap-1.5 font-semibold text-slate-700 uppercase">
        <GitCommit className="w-4 h-4 text-emerald-600" />
        Código da última atualização (GitHub)
      </p>

      {disponivel ? (
        <>
          <a
            href={`${versao.repositorio}/commit/${versao.commit}`}
            target="_blank"
            rel="noreferrer"
            className="block font-mono text-sm text-emerald-700 hover:underline break-all"
            data-testid="codigo-atualizacao"
          >
            {versao.commit}
          </a>

          {(versao.mensagem || versao.data) && (
            <p className="text-slate-500">
              {versao.mensagem}
              {versao.mensagem && versao.data ? ' · ' : ''}
              {versao.data ? new Date(versao.data).toLocaleString('pt-BR') : ''}
            </p>
          )}
        </>
      ) : (
        <p className="font-mono text-slate-500">
          {versao ? 'indisponível neste ambiente' : 'carregando…'}
        </p>
      )}
    </div>
  );
}
