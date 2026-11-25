"""Lista os compromissos abertos de todos os contatos (secao "Compromissos abertos" de cada nota).

Compromisso e algo que o usuario prometeu fazer depois ("te retorno", "vou verificar"). Rodar
no inicio da sessao para nao deixar promessa esquecida. Registrar com:
    python criar_nota.py <chat_jid> --compromisso "texto"
e concluir com:
    python criar_nota.py <chat_jid> --concluir "trecho do texto"

Uso:
    python compromissos.py
"""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402

ABERTO = re.compile(r"^- \[ \] (\d{4}-\d{2}-\d{2}): (.+)$")


def listar() -> list:
    pasta = comum.pasta_notas()
    if not pasta.exists():
        return []
    abertos = []
    for arquivo in sorted(pasta.glob("*.md")):
        if arquivo.name.startswith("_"):
            continue
        texto = arquivo.read_text(encoding="utf-8")
        contato = re.search(r"^contato: (.+)$", texto, re.M)
        nome = contato.group(1) if contato else arquivo.stem
        for linha in texto.splitlines():
            achou = ABERTO.match(linha)
            if achou:
                desde = date.fromisoformat(achou.group(1))
                abertos.append(((date.today() - desde).days, nome, achou.group(2)))
    return sorted(abertos, reverse=True)


if __name__ == "__main__":
    abertos = listar()
    if not abertos:
        print("Nenhum compromisso aberto.")
    for dias, nome, texto in abertos:
        quando = "hoje" if dias == 0 else f"ha {dias} dia(s)"
        print(f"- {nome}: {texto} (prometido {quando})")
