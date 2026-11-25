"""Cria ou atualiza a nota <slug>.md de um contato (formato em references/formato-da-nota.md).

Cria o esqueleto (nome da agenda, jids, data) para so preencher o estilo e a relacao,
registra linhas em "Historico de decisoes" (mantendo as ultimas 10) e controla os
"Compromissos abertos" (o que o usuario prometeu fazer depois).

Uso:
    python criar_nota.py <chat_jid> [--slug nome] [--relacao "texto"]
                       [--decisao "texto"] [--compromisso "texto"] [--concluir "trecho"]

Exemplos:
    python criar_nota.py 5511999999999@s.whatsapp.net
    python criar_nota.py 5511999999999@s.whatsapp.net --decisao 'sugeri "X", confirmou sem mudar'
    python criar_nota.py 5511999999999@s.whatsapp.net --compromisso "verificar o pagamento com o financeiro"
    python criar_nota.py 5511999999999@s.whatsapp.net --concluir "verificar o pagamento"
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402

MAX_DECISOES = 10
SEC_COMPROMISSOS = "## Compromissos abertos\n"
SEC_DECISOES = "## Historico de decisoes\n"


def _esqueleto(nome: str, jids: list, relacao: str) -> str:
    return f"""---
contato: {nome}
jid: {" | ".join(jids)}
atualizado: {date.today().isoformat()}
---

## Estilo identificado
- (preencher com os sinais da skill escrever-como-humano: caixa, acentuacao, abreviacoes, apelidos, emojis, formalidade, como divide em mensagens)

## Relacao
- {relacao or "(quem e: amigo, colega de trabalho, familia, prestador de servico)"}

## Observacoes
- A conversa recente pode estar em so um dos jids acima; consultar todos

{SEC_COMPROMISSOS}
{SEC_DECISOES}"""


def _atualizar_data(texto: str) -> str:
    return re.sub(
        r"atualizado: .*", f"atualizado: {date.today().isoformat()}", texto, count=1
    )


def _garantir_secao_compromissos(texto: str) -> str:
    if SEC_COMPROMISSOS in texto:
        return texto
    return texto.replace(SEC_DECISOES, f"{SEC_COMPROMISSOS}\n{SEC_DECISOES}", 1)


def _adicionar_decisao(texto: str, decisao: str) -> str:
    cabecalho, _, resto = texto.partition(SEC_DECISOES)
    linhas = [l for l in resto.splitlines() if l.strip()]
    linhas.append(f"- {date.today().isoformat()}: {decisao}")
    return cabecalho + SEC_DECISOES + "\n".join(linhas[-MAX_DECISOES:]) + "\n"


def _adicionar_compromisso(texto: str, compromisso: str) -> str:
    texto = _garantir_secao_compromissos(texto)
    antes, _, depois = texto.partition(SEC_COMPROMISSOS)
    bloco, sep, resto = depois.partition("## ")
    linhas = [l for l in bloco.splitlines() if l.strip()]
    linhas.append(f"- [ ] {date.today().isoformat()}: {compromisso}")
    return antes + SEC_COMPROMISSOS + "\n".join(linhas) + "\n\n" + sep + resto


def _concluir_compromisso(texto: str, trecho: str):
    """Marca como concluido o primeiro compromisso aberto que contem o trecho."""
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if linha.startswith("- [ ] ") and trecho.lower() in linha.lower():
            linhas[i] = linha.replace("- [ ] ", "- [x] ", 1) + f" (concluido {date.today().isoformat()})"
            return "\n".join(linhas) + "\n", True
    return texto, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("chat_jid")
    parser.add_argument("--slug")
    parser.add_argument("--relacao", default="")
    parser.add_argument("--decisao")
    parser.add_argument("--compromisso")
    parser.add_argument("--concluir")
    args = parser.parse_args()

    jids = comum.jids_do_contato(args.chat_jid)
    existente = comum.achar_nota(jids)
    if existente:
        destino, acao = existente, "ja existia"
        texto = destino.read_text(encoding="utf-8")
    else:
        nome = comum.nome_da_agenda(jids)
        destino = comum.pasta_notas() / f"{args.slug or comum.slug(nome)}.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        texto, acao = _esqueleto(nome, jids, args.relacao), "criado"

    if args.decisao:
        texto = _adicionar_decisao(texto, args.decisao)
        acao += " + decisao registrada"
    if args.compromisso:
        texto = _adicionar_compromisso(texto, args.compromisso)
        acao += " + compromisso aberto"
    if args.concluir:
        texto, achou = _concluir_compromisso(texto, args.concluir)
        acao += " + compromisso concluido" if achou else " + compromisso NAO encontrado"

    destino.write_text(_atualizar_data(texto), encoding="utf-8")
    print(f"nota {acao}: {destino}")


if __name__ == "__main__":
    main()
