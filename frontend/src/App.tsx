import { useCallback, useEffect, useState } from 'react';
import { LogOut, Sprout } from 'lucide-react';
import { api, getToken, setToken } from './api';
import type { Versao } from './types';
import { CodigoAtualizacao } from './components/CodigoAtualizacao';
import { Contas } from './components/Contas';
import { CrudPage } from './components/CrudPage';
import { ExtrairNota } from './components/ExtrairNota';
import { Login } from './components/Login';

type Aba =
  | 'nota'
  | 'fornecedores'
  | 'faturados'
  | 'despesas'
  | 'receitas'
  | 'pagar'
  | 'receber';

const ABAS: { id: Aba; rotulo: string }[] = [
  { id: 'nota', rotulo: 'Lançar NF-e' },
  { id: 'pagar', rotulo: 'Contas a Pagar' },
  { id: 'receber', rotulo: 'Contas a Receber' },
  { id: 'fornecedores', rotulo: 'Fornecedores / Clientes' },
  { id: 'faturados', rotulo: 'Faturados' },
  { id: 'despesas', rotulo: 'Tipos de Despesa' },
  { id: 'receitas', rotulo: 'Tipos de Receita' },
];

export function App() {
  const [logado, setLogado] = useState(!!getToken());
  const [aba, setAba] = useState<Aba>('nota');
  const [versao, setVersao] = useState<Versao | null>(null);

  // Código da última atualização no GitHub (aparece na tela principal)
  useEffect(() => {
    api<Versao>('/api/versao')
      .then(setVersao)
      .catch(() => setVersao({ commit: 'indisponível', commitCurto: '', data: null, mensagem: null, repositorio: '' }));
  }, []);

  // Sessão expirada (401) -> volta para o login
  useEffect(() => {
    const sair = () => setLogado(false);
    window.addEventListener('agrosoft:logout', sair);
    return () => window.removeEventListener('agrosoft:logout', sair);
  }, []);

  const sair = useCallback(() => {
    setToken(null);
    setLogado(false);
  }, []);

  if (!logado) {
    return <Login versao={versao} onEntrar={() => setLogado(true)} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <Sprout className="w-7 h-7 text-emerald-600" />
              AgroSoft – Gestão Financeira Agrícola
            </h1>
            <p className="text-sm text-slate-600">
              Extração de NF-e por IA, cadastros e contas a pagar/receber.
            </p>
          </div>

          <div className="flex items-start gap-3">
            <div className="max-w-md">
              <CodigoAtualizacao versao={versao} />
            </div>

            <button
              onClick={sair}
              className="px-3 py-2 text-sm text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-100 flex items-center gap-1.5"
            >
              <LogOut className="w-4 h-4" /> Sair
            </button>
          </div>
        </div>

        <nav className="max-w-6xl mx-auto px-6 flex flex-wrap gap-1">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 ${
                aba === a.id
                  ? 'border-emerald-600 text-emerald-700'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </nav>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        {aba === 'nota' && <ExtrairNota />}

        {aba === 'pagar' && <Contas key="pagar" tipo="APAGAR" />}

        {aba === 'receber' && <Contas key="receber" tipo="ARECEBER" />}

        {aba === 'fornecedores' && (
          <CrudPage
            titulo="Manter Fornecedor / Cliente"
            descricao="Cadastro de pessoas (tipo CLIENTE-FORNECEDOR) usadas nas contas a pagar e a receber."
            endpoint="/api/pessoas"
            tipo="CLIENTE-FORNECEDOR"
            campos={[
              { nome: 'razaoSocial', rotulo: 'Razão Social / Nome', obrigatorio: true },
              { nome: 'fantasia', rotulo: 'Nome Fantasia' },
              { nome: 'documento', rotulo: 'CNPJ / CPF', placeholder: 'somente números ou com máscara' },
            ]}
            colunas={[
              { chave: 'id', rotulo: 'ID' },
              { chave: 'razaoSocial', rotulo: 'Razão Social / Nome' },
              { chave: 'fantasia', rotulo: 'Fantasia' },
              { chave: 'documento', rotulo: 'CNPJ / CPF' },
              { chave: 'status', rotulo: 'Status' },
            ]}
          />
        )}

        {aba === 'faturados' && (
          <CrudPage
            titulo="Manter Faturado"
            descricao="Cadastro de pessoas (tipo FATURADO): quem é o destinatário/pagador das notas."
            endpoint="/api/pessoas"
            tipo="FATURADO"
            campos={[
              { nome: 'razaoSocial', rotulo: 'Nome / Razão Social', obrigatorio: true },
              { nome: 'documento', rotulo: 'CPF / CNPJ', placeholder: 'somente números ou com máscara' },
            ]}
            colunas={[
              { chave: 'id', rotulo: 'ID' },
              { chave: 'razaoSocial', rotulo: 'Nome / Razão Social' },
              { chave: 'documento', rotulo: 'CPF / CNPJ' },
              { chave: 'status', rotulo: 'Status' },
            ]}
          />
        )}

        {aba === 'despesas' && (
          <CrudPage
            titulo="Manter Tipo de Despesa"
            descricao="Classificações de despesa usadas nas contas a pagar (ex.: MANUTENÇÃO E OPERAÇÃO)."
            endpoint="/api/classificacoes"
            tipo="DESPESA"
            campos={[{ nome: 'descricao', rotulo: 'Descrição', obrigatorio: true }]}
            colunas={[
              { chave: 'id', rotulo: 'ID' },
              { chave: 'descricao', rotulo: 'Descrição' },
              { chave: 'status', rotulo: 'Status' },
            ]}
          />
        )}

        {aba === 'receitas' && (
          <CrudPage
            titulo="Manter Tipo de Receita"
            descricao="Classificações de receita usadas nas contas a receber."
            endpoint="/api/classificacoes"
            tipo="RECEITA"
            campos={[{ nome: 'descricao', rotulo: 'Descrição', obrigatorio: true }]}
            colunas={[
              { chave: 'id', rotulo: 'ID' },
              { chave: 'descricao', rotulo: 'Descrição' },
              { chave: 'status', rotulo: 'Status' },
            ]}
          />
        )}
      </main>
    </div>
  );
}

export default App;
