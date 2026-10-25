// Mesmo domínio em produção; em dev o Vite faz proxy de /api.
// Para apontar para outro servidor: VITE_API_URL=https://meu-backend
const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

const CHAVE_TOKEN = 'agrosoft_token';

export const getToken = () => localStorage.getItem(CHAVE_TOKEN);

export const setToken = (token: string | null) => {
  if (token) localStorage.setItem(CHAVE_TOKEN, token);
  else localStorage.removeItem(CHAVE_TOKEN);
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface Opcoes {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  json?: unknown;
  form?: FormData;
}

function mensagemDeErro(detail: unknown, padrao: string): string {
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d?.msg === 'string' ? d.msg : ''))
      .filter(Boolean)
      .join(' ') || padrao;
  }

  return padrao;
}

export async function api<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();

  if (token) headers.Authorization = `Bearer ${token}`;
  if (opcoes.json !== undefined) headers['Content-Type'] = 'application/json';

  let resposta: Response;

  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method: opcoes.method ?? (opcoes.json || opcoes.form ? 'POST' : 'GET'),
      headers,
      body: opcoes.form ?? (opcoes.json !== undefined ? JSON.stringify(opcoes.json) : undefined),
    });
  } catch {
    throw new ApiError('Falha ao conectar com o servidor.', 0);
  }

  if (!resposta.ok) {
    let detail: unknown;

    try {
      detail = (await resposta.json()).detail;
    } catch {
      /* resposta sem JSON */
    }

    if (resposta.status === 401 && caminho !== '/api/login') {
      setToken(null);
      window.dispatchEvent(new Event('agrosoft:logout'));
    }

    throw new ApiError(
      mensagemDeErro(detail, `Erro ${resposta.status} ao processar a requisição.`),
      resposta.status,
    );
  }

  return resposta.json() as Promise<T>;
}

export const moeda = (v: number | null | undefined) =>
  (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const dataBR = (iso: string | null | undefined) => {
  if (!iso) return '—';
  const [a, m, d] = iso.split('-');
  return d && m && a ? `${d}/${m}/${a}` : iso;
};
