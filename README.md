# AgroSoft - Gestão Financeira Agrícola

Sistema desenvolvido para auxiliar no controle financeiro de uma propriedade rural, automatizando o cadastro e a extração de informações de notas fiscais.

## Objetivo

O AgroSoft tem como objetivo reduzir o trabalho manual no controle financeiro de propriedades rurais, permitindo a leitura automática de documentos fiscais e a organização das informações extraídas.

## Funcionalidades

Atualmente, o projeto possui como principal funcionalidade:

- Upload de notas fiscais em formato PDF;
- Extração automática do texto do documento;
- Processamento das informações utilizando Inteligência Artificial;
- Identificação de dados do fornecedor e faturado;
- Extração do número e data da nota fiscal;
- Identificação dos produtos;
- Identificação do valor total e vencimento;
- Identificação da quantidade de parcelas;
- Classificação automática da despesa;
- Exibição dos dados extraídos na interface web.

### Categorias de despesas

A classificação automática utiliza as seguintes categorias:

1. Insumos Agrícolas
2. Manutenção e Operação
3. Recursos Humanos
4. Serviços Operacionais
5. Infraestrutura e Utilidades
6. Administrativas
7. Seguros e Proteção
8. Impostos e Taxas
9. Investimentos

## Tecnologias utilizadas

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Lucide React

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn
- pypdf
- python-dotenv
- Groq API

## Estrutura do projeto

```text
agrosoft-gestao/
├── backend/
│   ├── .env
│   ├── main.py
│   ├── requirements.txt
│   └── testar_groq.py
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── .gitignore
├── README.md
├── run.bat
└── run.sh
```

## Configuração

No arquivo `backend/.env`, configure a chave da API da Groq:

```env
GROQ_API_KEY=SUA_CHAVE_AQUI
GROQ_MODEL=openai/gpt-oss-20b
```

> O arquivo `.env` não deve ser enviado para o GitHub, pois contém informações privadas.

## Como executar

### Linux

Execute:

```bash
./run.sh
```

Ou, manualmente:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

### Windows

Execute:

```bat
run.bat
```

Ou, manualmente, inicie o backend:

```bat
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

E depois o frontend:

```bat
cd frontend
npm install
npm run dev
```

## Endpoints da API

### Testar conexão com a Groq

```http
GET /api/testar-groq
```

### Extrair dados da nota fiscal

```http
POST /api/extrair-nota
```

O endpoint recebe um arquivo PDF e retorna os dados extraídos e classificados pela Inteligência Artificial.

### Documentação da API

Com o backend em execução, a documentação pode ser acessada em:

```text
http://localhost:8000/docs
```

## Fluxo do sistema

```text
Usuário
   ↓
Upload da nota fiscal em PDF
   ↓
Frontend React
   ↓
API FastAPI
   ↓
Extração do texto do PDF
   ↓
Groq API
   ↓
Processamento e classificação dos dados
   ↓
Retorno em JSON
   ↓
Exibição das informações no Frontend
```

## Status do projeto

O projeto encontra-se em desenvolvimento. A funcionalidade de upload e processamento de notas fiscais com extração e classificação automática por Inteligência Artificial está implementada.

As demais funcionalidades previstas na documentação de requisitos serão desenvolvidas nas próximas etapas.

## Links

Link do Projeto hospedado:
[https://agrosoft-1-wo38.onrender.com]

Link do Youtube: [https://youtu.be/TRZcQpO6AOk]
