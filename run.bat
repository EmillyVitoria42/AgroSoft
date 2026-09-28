@echo off
echo ==========================================
echo Iniciando AgroSoft - Backend e Frontend
echo ==========================================

cd backend
if not exist "venv" (
    echo Criando ambiente virtual venv...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo Instalando dependencias do Backend...
pip install -r requirements.txt

echo Iniciando servidor Backend (FastAPI)...
start cmd /k "uvicorn main:app --reload --port 8000"

cd ..\frontend
echo Instalando dependencias do Frontend...
call npm install

echo Iniciando servidor Frontend (Vite/React)...
npm run dev