import React, { useState } from 'react';
import { AlertCircle, Loader2, Lock } from 'lucide-react';
import { api, setToken } from '../api';
import type { Versao } from '../types';
import { CodigoAtualizacao } from './CodigoAtualizacao';

interface Props {
  versao: Versao | null;
  onEntrar: () => void;
}

export function Login({ versao, onEntrar }: Props) {
  const [login, setLogin] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  const entrar = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro(null);
    setCarregando(true);

    try {
      const r = await api<{ token: string }>('/api/login', {
        json: { login, senha },
      });

      setToken(r.token);
      onEntrar();
    } catch (err: any) {
      setErro(err.message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-sm space-y-4">
        <form
          onSubmit={entrar}
          className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4"
        >
          <div className="text-center space-y-1">
            <Lock className="w-8 h-8 text-emerald-600 mx-auto" />
            <h1 className="text-2xl font-bold text-slate-800">AgroSoft</h1>
            <p className="text-sm text-slate-600">Gestão Financeira Agrícola</p>
          </div>

          <label className="block text-sm font-medium text-slate-700">
            Login
            <input
              autoFocus
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
            />
          </label>

          <label className="block text-sm font-medium text-slate-700">
            Senha
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
            />
          </label>

          {erro && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {erro}
            </div>
          )}

          <button
            type="submit"
            disabled={!login || !senha || carregando}
            className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-medium rounded-lg flex items-center justify-center gap-2"
          >
            {carregando && <Loader2 className="w-4 h-4 animate-spin" />}
            Entrar
          </button>
        </form>

        <CodigoAtualizacao versao={versao} />
      </div>
    </div>
  );
}
