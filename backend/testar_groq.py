import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# Localiza o arquivo .env
ENV_PATH = Path(__file__).parent / ".env"

# Carrega as variáveis do .env
load_dotenv(ENV_PATH, override=True)


# Pega a chave da Groq
api_key = os.getenv("GROQ_API_KEY")


print("=== Diagnóstico Groq ===")


# Verifica se a chave existe
if not api_key:
    print("❌ GROQ_API_KEY não encontrada no .env")
    exit()


print(f"✅ Chave encontrada: {api_key[:5]}...{api_key[-4:]}")
print(f"   Tamanho: {len(api_key)} caracteres")


# Cria o cliente apontando para a API da Groq
client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)


try:

    print("\n=== Testando chamada à API ===")

    response = client.responses.create(
        model="openai/gpt-oss-20b",
        input="Responda apenas: OK"
    )

    print("✅ GROQ respondeu:")
    print(response.output_text)


except Exception as e:

    print("❌ Erro:")
    print(type(e).__name__)
    print(e)