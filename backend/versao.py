"""
Código da última atualização no GitHub (hash do commit).

Esse código é exibido na tela principal do sistema.

Ordem de busca:
1. Variáveis de ambiente do host (Render: RENDER_GIT_COMMIT)
2. `git rev-parse HEAD` / `git log` (rodando localmente)
3. Arquivo backend/version.json (opcional, gerado no deploy)
"""

import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent


def _git(*args: str) -> str | None:

    try:
        saida = subprocess.run(
            ["git", *args],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if saida.returncode == 0:
            return saida.stdout.strip() or None

    except Exception:
        pass

    return None


@lru_cache(maxsize=1)
def obter_versao() -> dict:

    commit = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GIT_COMMIT")
        or os.getenv("COMMIT_SHA")
        or os.getenv("SOURCE_VERSION")
    )

    data = None

    mensagem = None

    if not commit:

        commit = _git("rev-parse", "HEAD")

        data = _git("log", "-1", "--format=%cI")

        mensagem = _git("log", "-1", "--format=%s")

    if not commit:

        arquivo = Path(__file__).parent / "version.json"

        if arquivo.is_file():

            try:
                info = json.loads(arquivo.read_text(encoding="utf-8"))

                commit = info.get("commit")
                data = info.get("data")
                mensagem = info.get("mensagem")

            except Exception:
                pass

    return {
        "commit": commit or "indisponível",
        "commitCurto": (commit or "indisponível")[:7],
        "data": data,
        "mensagem": mensagem,
        "repositorio": "https://github.com/EmillyVitoria42/AgroSoft",
    }
