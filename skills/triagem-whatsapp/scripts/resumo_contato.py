"""Resumo compacto do historico de um contato, direto do sqlite da bridge.

Substitui chamar mcp__whatsapp__list_messages pra ler historico -- isso evita
gastar tokens de ida-e-volta com a ferramenta MCP so pra extrair texto puro
que um script resolve sozinho. So chamar o MCP depois, se precisar baixar
midia especifica (audio/imagem) que aparece aqui como placeholder.

O contato pode ter dois JIDs (@lid e @s.whatsapp.net): os dois sao lidos juntos.

Uso:
    python resumo_contato.py <chat_jid> [--limite 40]

Exemplo:
    python resumo_contato.py 5511999999999@s.whatsapp.net --limite 30
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402


def resumo(chat_jid: str, limite: int = 40) -> str:
    if not comum.DB_PATH.exists():
        return f"Banco nao encontrado em {comum.DB_PATH}."

    con = comum.abrir_ro(comum.DB_PATH)
    cur = con.cursor()

    jids = comum.jids_do_contato(chat_jid)
    marcas = ",".join("?" * len(jids))
    nome = comum.nome_da_agenda(jids, cur)

    cur.execute(
        f"""
        SELECT timestamp, is_from_me, content, media_type, filename
        FROM messages
        WHERE chat_jid IN ({marcas})
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (*jids, limite),
    )
    linhas = cur.fetchall()
    con.close()

    if not linhas:
        return f"Nenhuma mensagem encontrada com {nome} ({', '.join(jids)})."

    linhas.reverse()  # cronologico (mais antiga primeiro)

    partes = [f"=== Historico com {nome} ({chat_jid}) -- {len(linhas)} mensagens ==="]
    for timestamp, is_from_me, content, media_type, filename in linhas:
        quem = "EU" if is_from_me else "ELE(A)"
        hora = timestamp[:16].replace("T", " ") if "T" in str(timestamp) else str(timestamp)[:16]
        if media_type:
            texto = comum.rotulo_de_midia(media_type, filename)
            if content:
                texto += " " + content.replace("\n", " ")[:300]
        elif content:
            texto = content.replace("\n", " ")[:300]
        else:
            continue
        partes.append(f"[{hora}] {quem}: {texto}")

    return "\n".join(partes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("chat_jid")
    parser.add_argument("--limite", type=int, default=40)
    args = parser.parse_args()

    print(resumo(args.chat_jid, args.limite))
