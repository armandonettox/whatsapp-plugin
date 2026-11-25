"""Mostra onde ficam os dados do plugin: bancos da bridge, notas por contato e rascunhos do loop.

Uso: python caminhos.py

Serve para o agente (e para voce) nao precisar adivinhar caminhos. Cada pasta pode ser trocada
por uma variavel de ambiente: WHATSAPP_STORE_DIR, WHATSAPP_NOTES_DIR e WHATSAPP_DRAFTS_DIR.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comum as comum  # noqa: E402


def main() -> None:
    pastas = [
        ("bancos da bridge (store)", comum.pasta_store(), (comum.pasta_store() / "messages.db").exists()),
        ("notas por contato", comum.pasta_notas(), comum.pasta_notas().exists()),
        ("rascunhos do loop", comum.pasta_rascunhos(), comum.pasta_rascunhos().exists()),
    ]
    for nome, pasta, existe in pastas:
        print(f"{nome}: {pasta}  [{'existe' if existe else 'ainda nao existe'}]")


if __name__ == "__main__":
    main()
