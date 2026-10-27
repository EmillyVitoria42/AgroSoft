#!/bin/bash
echo "=========================================="
echo "Iniciando AgroSoft - Backend e Frontend"
echo "=========================================="

cd backend
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual venv..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Instalando dependencias do Backend..."
pip install -r requirements.txt

echo "Iniciando servidor Backend..."
uvicorn main:app --reload --port 8000 &

cd ../frontend
echo "Instalando dependencias do Frontend..."
npm install

echo "Iniciando servidor Frontend..."
npm run dev