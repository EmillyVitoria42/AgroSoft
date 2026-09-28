import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface DadosNota {
  numero: string;
  dataEmissao: string;
  fornecedor: {
    razaoSocial: string;
    nomeFantasia: string;
    cnpj: string;
  };
  faturado: {
    nomeCompleto: string;
    cpf: string;
  };
  produtos: string[];
  quantidadeParcelas: number;
  dataVencimento: string;
  valorTotal: number;
  classificacaoDespesa: string;
}

export function App() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState<DadosNota | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErro(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setErro("Por favor, selecione um arquivo PDF da Nota Fiscal.");
      return;
    }

    setLoading(true);
    setErro(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/extrair-nota', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Erro ao processar a nota fiscal.");
      }

      const data: DadosNota = await response.json();
      setDados(data);
    } catch (err: any) {
      setErro(err.message || "Falha ao conectar com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Cabeçalho */}
        <header className="border-b pb-4">
          <h1 className="text-3xl font-bold text-slate-800">AgroSoft - Módulo de Extração de NF-e</h1>
          <p className="text-slate-600">Envie o PDF do DANFE para extração automática via Inteligência Artificial.</p>
        </header>

        {/* Área de Upload */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
          <h2 className="text-xl font-semibold text-slate-700 flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-600" />
            Upload de Documento
          </h2>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-emerald-500 transition-colors">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
              <Upload className="w-10 h-10 text-slate-400" />
              <span className="text-slate-600 font-medium">
                {file ? file.name : "Clique para selecionar o PDF da Nota Fiscal"}
              </span>
              <span className="text-xs text-slate-400">Apenas arquivos no formato PDF</span>
            </label>
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || loading}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processando PDF com Gemini IA...
              </>
            ) : (
              "Extrair Dados da Nota"
            )}
          </button>

          {erro && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{erro}</span>
            </div>
          )}
        </div>

        {/* Exibição dos Dados Extraídos */}
        {dados && (
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-6">
            <div className="flex justify-between items-center border-b pb-4">
              <h2 className="text-xl font-semibold text-slate-700 flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                Dados Extraídos
              </h2>
              <span className="px-3 py-1 bg-emerald-100 text-emerald-800 font-semibold text-sm rounded-full">
                {dados.classificacaoDespesa}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 font-bold uppercase">Nota Fiscal</p>
                <p className="text-lg font-semibold text-slate-800">Nº {dados.numero}</p>
                <p className="text-sm text-slate-600">Emissão: {dados.dataEmissao}</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 font-bold uppercase">Valor & Pagamento</p>
                <p className="text-lg font-semibold text-emerald-700">
                  R$ {dados.valorTotal ? dados.valorTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '0,00'}
                </p>
                <p className="text-sm text-slate-600">Vencimento: {dados.dataVencimento} ({dados.quantidadeParcelas}x)</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 font-bold uppercase">Fornecedor</p>
                <p className="font-medium text-slate-800">{dados.fornecedor?.razaoSocial}</p>
                <p className="text-xs text-slate-500">CNPJ: {dados.fornecedor?.cnpj}</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 font-bold uppercase">Faturado</p>
                <p className="font-medium text-slate-800">{dados.faturado?.nomeCompleto}</p>
                <p className="text-xs text-slate-500">CPF/CNPJ: {dados.faturado?.cpf}</p>
              </div>
            </div>

            <div>
              <p className="text-xs text-slate-500 font-bold uppercase mb-2">Itens Detectados</p>
              <ul className="divide-y divide-slate-100 border rounded-lg overflow-hidden">
                {dados.produtos?.map((prod, index) => (
                  <li key={index} className="p-3 text-sm text-slate-700 bg-slate-50/50">
                    {prod}
                  </li>
                ))}
              </ul>
            </div>

            {/* Exibição do JSON Bruto */}
            <div>
              <p className="text-xs text-slate-500 font-bold uppercase mb-2">JSON Estruturado (Dev Output)</p>
              <pre className="p-4 bg-slate-900 text-emerald-400 rounded-lg text-xs overflow-x-auto font-mono">
                {JSON.stringify(dados, null, 2)}
              </pre>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;