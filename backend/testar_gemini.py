"""
Diagnóstico do Gemini — rode dentro da pasta backend, com o venv ativo:

    python testar_gemini.py "caminho/para/danfe.pdf"

Cada etapa mostra OK ou o erro EXATO. Cole a saída para quem for te ajudar
(a chave nunca é impressa por inteiro).
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

MODELO = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def etapa(nome):
    print(f"\n=== {nome} ===")


def erro(e):
    print(f"❌ {type(e).__name__}: {e}")


# 1) Chave -------------------------------------------------------------------
etapa("1. Chave no .env")
env_path = Path(__file__).parent / ".env"
print("Arquivo .env existe:", env_path.exists(), "->", env_path)
load_dotenv(env_path, override=True)
key = (os.getenv("GEMINI_API_KEY") or "").strip()
if not key:
    print("❌ GEMINI_API_KEY vazia ou não encontrada no .env")
    sys.exit(1)
print(f"✅ Chave lida: {key[:4]}...{key[-3:]}  ({len(key)} caracteres)")
if key != key.strip('"\''):
    print("⚠️  A chave parece estar entre aspas — remova as aspas no .env")

client = genai.Client(api_key=key)

# 2) Chave válida + modelo existe --------------------------------------------
etapa("2. Chave válida e modelo disponível")
try:
    nomes = [m.name for m in client.models.list()]
    print(f"✅ Chave aceita pelo Google ({len(nomes)} modelos visíveis)")
    achou = any(n.endswith("/" + MODELO) or n == MODELO for n in nomes)
    print(f"{'✅' if achou else '❌'} Modelo '{MODELO}' {'está' if achou else 'NÃO está'} na lista")
    if not achou:
        print("   Modelos 'flash' disponíveis para você:")
        for n in nomes:
            if "flash" in n:
                print("   -", n.replace("models/", ""))
except Exception as e:
    erro(e)

# 3) Texto simples -----------------------------------------------------------
etapa("3. Chamada simples (só texto)")
try:
    r = client.models.generate_content(model=MODELO, contents="Responda apenas: ok")
    print("✅ Resposta:", (r.text or "").strip()[:80])
except Exception as e:
    erro(e)

# 4) PDF ---------------------------------------------------------------------
etapa("4. Chamada com PDF")
if len(sys.argv) < 2:
    print("⏭️  Pulado (passe o caminho de um PDF como argumento)")
else:
    try:
        pdf = Path(sys.argv[1]).read_bytes()
        r = client.models.generate_content(
            model=MODELO,
            contents=[
                types.Part.from_bytes(data=pdf, mime_type="application/pdf"),
                'Devolva um JSON com {"numero": "...", "valorTotal": 0.0} desta nota.',
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        print("✅ Texto bruto devolvido pelo Gemini:")
        print(r.text)
    except Exception as e:
        erro(e)

print("\nFim do diagnóstico.")