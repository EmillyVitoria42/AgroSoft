# AgroSoft - Gestão Financeira Agrícola

Sistema desenvolvido para auxiliar no controle financeiro de uma propriedade rural, automatizando o cadastro e a extração de informações de notas fiscais.

## Objetivo

O AgroSoft tem como objetivo reduzir o trabalho manual no controle financeiro de propriedades rurais, permitindo a leitura automática de documentos fiscais e a organização das informações extraídas.

## Funcionalidades

- **Login** (usuário e senha configuráveis);
- **Código da última atualização no GitHub** (hash do commit) exibido na tela principal;
- **Lançar NF-e**: upload do PDF do DANFE → extração com IA → **consulta ao banco** informando se
  FORNECEDOR, FATURADO e DESPESA **EXISTEM (com ID) ou NÃO EXISTEM** → ao confirmar, o sistema cria o
  que faltar, registra o movimento (conta a pagar) com sua parcela e avisa que foi lançado com sucesso;
- **Manter Fornecedor / Cliente**, **Manter Faturado**, **Manter Tipo de Despesa**,
  **Manter Tipo de Receita**;
- **Contas a Pagar** e **Contas a Receber**, com uma ou mais classificações e uma ou mais parcelas
  (vencimentos distintos);
- Regras: cadastros **nunca são excluídos** — são **INATIVADOS** e podem ser **REATIVADOS**.

### Layout das telas de cadastro

- tabela começa vazia; os dados chegam pela **Busca** (vários termos, ex.: `iguaçu maquinas 0001`) ou
  por **TODOS** (carrega os registros com STATUS = ATIVO);
- clique no título da coluna para ordenar;
- ações: **Editar** / **Excluir** (lógico → STATUS = INATIVO) e **Reativar**;
- o campo STATUS é oculto: no cadastro nasce ATIVO.

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
- SQLite (banco de dados)

## Estrutura do projeto

```text
AgroSoft/
├── backend/
│   ├── main.py              # app FastAPI + extração com IA (Groq)
│   ├── models.py            # modelos Pydantic da nota fiscal
│   ├── db.py                # SQLite: tabelas e conexão
│   ├── servicos.py          # regras de negócio (cadastros, contas, análise/lançamento)
│   ├── rotas.py             # rotas HTTP
│   ├── auth.py              # login (token assinado)
│   ├── versao.py            # código da última atualização (commit do GitHub)
│   ├── testar_servicos.py   # teste das regras de negócio
│   ├── .env.example
│   └── requirements.txt
├── frontend/                # React + Vite + Tailwind
│   └── src/components/      # Login, ExtrairNota, CrudPage, Contas, ...
├── Dockerfile               # (opcional) hospedagem em um único serviço
├── run.sh / run.bat
└── README.md
```

### Entidades do banco

| Tabela | Observações |
| --- | --- |
| `pessoas` | tipo `CLIENTE-FORNECEDOR` ou `FATURADO` (razão social, fantasia, CNPJ/CPF, status) |
| `classificacao` | tipo `DESPESA` ou `RECEITA` (descrição, status) |
| `movimento_contas` | tipo `APAGAR` ou `ARECEBER` |
| `movimento_classificacao` | liga o movimento a uma ou mais classificações |
| `parcela_contas` | identificação `ÚNICA`, `1/3`, `2/3`... com vencimento e valor |

## Configuração

Copie `backend/.env.example` para `backend/.env` e preencha:

```env
GROQ_API_KEY=SUA_CHAVE_AQUI
GROQ_MODEL=openai/gpt-oss-20b
AUTH_LOGIN=admin
AUTH_PASSWORD=agrosoft123
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

Todos exigem login (`Authorization: Bearer <token>`), exceto `POST /api/login` e `GET /api/versao`.

| Método | Rota | Função |
| --- | --- | --- |
| POST | `/api/login` | autentica e devolve o token |
| GET | `/api/versao` | código (hash) da última atualização no GitHub |
| POST | `/api/extrair-nota` | PDF → dados extraídos pela IA |
| POST | `/api/analisar-nota` | consulta o banco: EXISTE (ID) / NÃO EXISTE |
| POST | `/api/lancar-nota` | cria o que falta + movimento + parcela(s) |
| GET/POST/PUT/DELETE | `/api/pessoas` | fornecedor/cliente e faturado (DELETE = inativar) |
| GET/POST/PUT/DELETE | `/api/classificacoes` | tipos de despesa e de receita |
| GET/POST/DELETE | `/api/movimentos` | contas a pagar / a receber |
| POST | `/api/.../{id}/reativar` | reativa um registro INATIVO |

Documentação interativa (com o backend rodando): `http://localhost:8000/docs`

## Fluxo do sistema

```text
Usuário → Login
   ↓
Upload da nota fiscal (PDF)
   ↓
FastAPI: pypdf extrai o texto → Groq (IA) devolve JSON
   ↓
Consulta no banco: FORNECEDOR / FATURADO / DESPESA
   → "EXISTE – ID: n" ou "NÃO EXISTE"
   ↓
Usuário confirma
   ↓
Cria fornecedor / faturado / despesa (se for o caso)
+ movimento (APAGAR) + parcela → "Registro lançado com sucesso!"
```

## Testes

```bash
cd backend
python testar_servicos.py
```

Usa um banco temporário e valida: análise EXISTE/NÃO EXISTE, criação do que falta, parcelas,
duplicidade de nota, inativar/reativar, busca por vários termos e contas a receber.

## Hospedagem (Render)

O FastAPI entrega o site compilado (`frontend/dist`) **e** a API, então basta **um** serviço.

**Opção 1 – Docker** (usa o `Dockerfile` da raiz): crie um *Web Service* com ambiente **Docker**.

**Opção 2 – Python nativo:**

- Build: `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build`
- Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

Variáveis de ambiente: `GROQ_API_KEY`, `GROQ_MODEL`, `AUTH_LOGIN`, `AUTH_PASSWORD`.
O código da última atualização vem de `RENDER_GIT_COMMIT` (o Render define automaticamente).
 
 O codigo da ultima atualizacao (hash do commit) aparece no topo da tela
  principal e na tela de login. Ele e lido do proprio GitHub/Render
  (variavel RENDER_GIT_COMMIT) a cada deploy.
- Fluxo da Etapa 2: "Lancar NF-e" -> enviar o PDF do DANFE -> o sistema
  mostra FORNECEDOR / FATURADO / DESPESA com "EXISTE - ID: n" ou
  "NAO EXISTE" -> "Confirmar e lancar" cria o que faltar, registra o
  movimento (APAGAR) e a parcela e informa que foi lancado com sucesso.
- Cadastros nunca sao excluidos: "Excluir" INATIVA e "Reativar" volta a
  ATIVO.

> **Atenção:** o banco é um arquivo SQLite. No plano gratuito do Render o disco é temporário: os dados
> são perdidos a cada novo deploy/reinício. Para manter os dados, use um *Persistent Disk* e defina
> `DATABASE_PATH=/var/data/agrosoft.db`, ou migre para PostgreSQL.

## Status do projeto

- Etapa 1: upload e extração/classificação de notas fiscais com IA.
- Etapa 2: análise no banco (EXISTE / NÃO EXISTE), criação de fornecedor/faturado/despesa, lançamento
  do movimento e parcela, cadastros com inativação/reativação, contas a pagar/receber, login e código
  da última atualização na tela principal.

## Login
**Login:** admin
**Senha:** agrosoft123

## Links

Link do Projeto hospedado:
https://agrosoft-praticasdesoft.onrender.com
Key (LLM): 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


Link do Youtube: [https://youtu.be/TRZcQpO6AOk]
