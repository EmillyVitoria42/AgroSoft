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

### Banco de dados

- **PostgreSQL** (acesso via psycopg2)
- Produção: **Neon** (PostgreSQL gerenciado, região São Paulo)
- Desenvolvimento: PostgreSQL local ou Neon

## Estrutura do projeto

```text
AgroSoft/
├── backend/
│   ├── main.py              # app FastAPI + extração com IA (Groq)
│   ├── models.py            # modelos Pydantic da nota fiscal
│   ├── db.py                # PostgreSQL: tabelas e conexão
│   ├── servicos.py          # regras de negócio (cadastros, contas, análise/lançamento)
│   ├── rotas.py             # rotas HTTP
│   ├── auth.py              # login (token assinado)
│   ├── versao.py            # código da última atualização (commit do GitHub)
│   ├── testar_servicos.py   # teste das regras de negócio
│   ├── .env.example
│   └── requirements.txt
├── frontend/                # React + Vite + Tailwind
│   └── src/components/      # Login, ExtrairNota, CrudPage, Contas, ...
├── docker-compose.yml       # (opcional) PostgreSQL local via Docker
├── Dockerfile               # (opcional) hospedagem em um único serviço
├── run.sh / run.bat
└── README.md
```

### Entidades do banco

| Tabela                    | Observações                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------- |
| `pessoas`                 | tipo `CLIENTE-FORNECEDOR` ou `FATURADO` (razão social, fantasia, CNPJ/CPF, status) |
| `classificacao`           | tipo `DESPESA` ou `RECEITA` (descrição, status)                                    |
| `movimento_contas`        | tipo `APAGAR` ou `ARECEBER`                                                        |
| `movimento_classificacao` | liga o movimento a uma ou mais classificações                                      |
| `parcela_contas`          | identificação `ÚNICA`, `1/3`, `2/3`... com vencimento e valor                      |

Valores monetários usam `NUMERIC(14,2)` e datas usam `DATE`. As tabelas e a função de busca
`norm()` (maiúsculas, sem acentos) são criadas automaticamente quando o backend sobe.

## Configuração

Copie `backend/.env.example` para `backend/.env` e preencha:

```env
GROQ_API_KEY=SUA_CHAVE_AQUI
GROQ_MODEL=openai/gpt-oss-20b
AUTH_LOGIN=admin
AUTH_PASSWORD=agrosoft123
DATABASE_URL=postgresql://agrosoft:agrosoft123@localhost:5432/agrosoft
```

> O arquivo `.env` não deve ser enviado para o GitHub, pois contém informações privadas
> (chave da IA e senha do banco).

### Banco de dados (PostgreSQL)

O sistema exige um PostgreSQL: sem `DATABASE_URL` o backend não sobe. Escolha **uma** das opções
abaixo e coloque a URL correspondente no `backend/.env`.

**Opção A – Neon (nuvem, a mesma usada em produção)**

1. Crie um projeto em [neon.tech](https://neon.tech) (plano gratuito).
2. Clique em **Connect**, deixe _Connection pooling_ desmarcado e copie a connection string:

```env
DATABASE_URL=postgresql://USUARIO:SENHA@ep-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require
```

> Para rodar `testar_servicos.py`, use a string **direta** (sem pooling), pois o teste usa um
> schema temporário.

**Opção B – PostgreSQL instalado na máquina (Ubuntu/Debian)**

```bash
sudo apt update
sudo apt install -y postgresql
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER agrosoft WITH PASSWORD 'agrosoft123';"
sudo -u postgres psql -c "CREATE DATABASE agrosoft OWNER agrosoft;"
```

Use `DATABASE_URL=postgresql://agrosoft:agrosoft123@localhost:5432/agrosoft`.

**Opção C – Docker (se o Docker estiver instalado e rodando)**

```bash
docker compose up -d
```

Sobe um PostgreSQL 16 com o mesmo usuário, senha e banco da opção B.

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

| Método              | Rota                     | Função                                            |
| ------------------- | ------------------------ | ------------------------------------------------- |
| POST                | `/api/login`             | autentica e devolve o token                       |
| GET                 | `/api/versao`            | código (hash) da última atualização no GitHub     |
| POST                | `/api/extrair-nota`      | PDF → dados extraídos pela IA                     |
| POST                | `/api/analisar-nota`     | consulta o banco: EXISTE (ID) / NÃO EXISTE        |
| POST                | `/api/lancar-nota`       | cria o que falta + movimento + parcela(s)         |
| GET/POST/PUT/DELETE | `/api/pessoas`           | fornecedor/cliente e faturado (DELETE = inativar) |
| GET/POST/PUT/DELETE | `/api/classificacoes`    | tipos de despesa e de receita                     |
| GET/POST/DELETE     | `/api/movimentos`        | contas a pagar / a receber                        |
| POST                | `/api/.../{id}/reativar` | reativa um registro INATIVO                       |

Documentação interativa (com o backend rodando): `http://localhost:8000/docs`

## Fluxo do sistema

```text
Usuário → Login
   ↓
Upload da nota fiscal (PDF)
   ↓
FastAPI: pypdf extrai o texto → Groq (IA) devolve JSON
   ↓
Consulta no banco (PostgreSQL): FORNECEDOR / FATURADO / DESPESA
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

Usa um _schema_ temporário no PostgreSQL indicado em `DATABASE_URL` (apagado ao final, então os
dados reais não são tocados) e valida: análise EXISTE/NÃO EXISTE, criação do que falta, parcelas,
duplicidade de nota, inativar/reativar, busca por vários termos e contas a receber.

Resultado esperado: `TODOS OS TESTES PASSARAM`.

## Hospedagem

O FastAPI entrega o site compilado (`frontend/dist`) **e** a API, então basta **um** serviço web
(Render) e **um** banco (Neon).

### Site (Render)

**Opção 1 – Docker** (usa o `Dockerfile` da raiz): crie um _Web Service_ com ambiente **Docker**.

**Opção 2 – Python nativo:**

- Build: `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build`
- Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

Variáveis de ambiente do Web Service: `GROQ_API_KEY`, `GROQ_MODEL`, `AUTH_LOGIN`, `AUTH_PASSWORD`
e `DATABASE_URL` (a connection string do Neon, terminada em `?sslmode=require`).
O código da última atualização vem de `RENDER_GIT_COMMIT` (o Render define automaticamente).

> No plano gratuito, o Render "dorme" após 15 minutos sem acessos e leva cerca de 1 minuto para
> acordar. Abra o site alguns minutos antes de qualquer apresentação.

### Banco de dados (Neon)

O banco fica no **Neon**, e não no PostgreSQL gratuito do Render, porque este último é apagado
30 dias após a criação. No Neon os dados persistem entre deploys e reinícios do site.

1. Crie o projeto no Neon (região _AWS South America East 1 – São Paulo_).
2. Copie a connection string (**Connect** no painel do projeto).
3. Cole em `DATABASE_URL` no Render e faça o deploy. As tabelas são criadas sozinhas.

> A primeira requisição após um período parado pode demorar alguns segundos, pois o Neon
> "acorda" o banco automaticamente.

### Backup

Antes de cada entrega, guarde uma cópia dos dados:

```bash
pg_dump "$DATABASE_URL" -Fc -f backup_agrosoft.dump
```

Para restaurar em um banco vazio:

```bash
pg_restore --no-owner -d "$DATABASE_URL" backup_agrosoft.dump
```

> O `pg_dump` precisa ser da mesma versão do servidor ou mais novo. Se der erro de versão
> (_server version mismatch_), faça o backup pelo painel do Neon, em **Backup & Restore**.
> Nunca envie o arquivo de backup para o GitHub: ele contém os dados do sistema.

## Evolução do banco nas próximas etapas

As tabelas são criadas com `CREATE TABLE IF NOT EXISTS`, o que **não altera** tabelas já
existentes. Se uma etapa futura precisar de uma coluna nova, **não apague o banco**: acrescente a
alteração em `backend/db.py`, por exemplo:

```sql
ALTER TABLE movimento_contas ADD COLUMN IF NOT EXISTS observacao TEXT;
```

Assim os dados já lançados são preservados.

## Status do projeto

- Etapa 1: upload e extração/classificação de notas fiscais com IA.
- Etapa 2: análise no banco (EXISTE / NÃO EXISTE), criação de fornecedor/faturado/despesa, lançamento
  do movimento e parcela, cadastros com inativação/reativação, contas a pagar/receber, login e código
  da última atualização na tela principal. Banco de dados em **PostgreSQL** (Neon).

## Links

Link do Projeto hospedado:
[https://agrosoft-1-wo38.onrender.com]

Link do Youtube: [https://youtu.be/TRZcQpO6AOk]
