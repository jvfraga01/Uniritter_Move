"""Hook PostToolUse: roda pytest sozinho toda vez que o Claude Code edita
ou cria um arquivo .py neste projeto.

Como funciona: o Claude Code manda pra este script (via stdin) um JSON
descrevendo qual ferramenta rodou e em qual arquivo. A gente ignora
qualquer coisa que não seja .py (README, JSON de estado, etc não
precisam rodar teste). Se for .py, roda `pytest`:

- Passou -> sai com código 0 (silencioso, o Claude nem percebe).
- Falhou -> sai com código 2. Esse código específico faz o Claude Code
  BLOQUEAR e mostrar o erro pro Claude dentro da mesma sessão, como se
  fosse ele mesmo que tivesse batido nesse erro -- então ele já tenta
  corrigir, sem você precisar colar o resultado do pytest manualmente.
"""
from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Não conseguimos ler o payload -- não arrisca bloquear à toa.
        return 0

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return 0

    result = subprocess.run(["pytest"])

    if result.returncode != 0:
        print(
            "\n[hook] pytest falhou depois dessa edição -- corrija antes "
            "de considerar a tarefa pronta.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
