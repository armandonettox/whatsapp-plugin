"""Busca um contato por nome ou numero e mostra tudo que importa de uma vez.

Junta os JIDs da mesma pessoa (@lid e @s.whatsapp.net), mostra quem falou por ultimo e se ja
existe nota por contato. Substitui varias chamadas de search_contacts / list_chats / mapa de LIDs.

Uso:
    python buscar_contato.py <nome ou numero>

Exemplo:
    python buscar_contato.py maria
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402


def _jids_que_batem(consulta: str) -> list:
    """Todos os jids de contatos cujo nome (agenda ou push_name) ou numero contem a consulta."""
    achados = []
    termo = f"%{consulta}%"
    if comum.CONTACTS_DB_PATH.exists():
        con = comum.abrir_ro(comum.CONTACTS_DB_PATH)
        try:
            for (jid,) in con.execute(
                "SELECT their_jid FROM whatsmeow_contacts "
                "WHERE full_name LIKE ? OR push_name LIKE ? OR first_name LIKE ? OR their_jid LIKE ?",
                (termo, termo, termo, termo),
            ):
                achados.append(jid)
        finally:
            con.close()
    if comum.DB_PATH.exists():
        con = comum.abrir_ro(comum.DB_PATH)
        try:
            for (jid,) in con.execute(
                "SELECT jid FROM chats WHERE (name LIKE ? OR jid LIKE ?) "
                "AND jid NOT LIKE '%@g.us' AND jid NOT LIKE '%@newsletter'",
                (termo, termo),
            ):
                achados.append(jid)
        finally:
            con.close()
    return [j for j in dict.fromkeys(achados) if not j.endswith("@g.us")]


def buscar(consulta: str) -> list:
    if not comum.DB_PATH.exists():
        print(f"Banco nao encontrado em {comum.DB_PATH}.")
        return []

    pessoas = {}
    for jid in _jids_que_batem(consulta):
        jids = comum.jids_do_contato(jid)
        pessoas.setdefault(tuple(sorted(jids)), jids)

    con = comum.abrir_ro(comum.DB_PATH)
    cur = con.cursor()
    resultado = []
    for jids in pessoas.values():
        marcas = ",".join("?" * len(jids))
        cur.execute(
            f"SELECT timestamp, is_from_me, content, media_type FROM messages "
            f"WHERE chat_jid IN ({marcas}) ORDER BY timestamp DESC LIMIT 1",
            jids,
        )
        ultima = cur.fetchone()
        nota = comum.achar_nota(jids)
        resultado.append((comum.nome_da_agenda(jids, cur), jids, ultima, nota))
    con.close()

    resultado.sort(key=lambda r: r[2][0] if r[2] else "", reverse=True)
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("consulta")
    args = parser.parse_args()

    achados = buscar(args.consulta)
    if not achados:
        print(f"Nenhum contato encontrado para '{args.consulta}'.")
    for i, (nome, jids, ultima, nota) in enumerate(achados, 1):
        print(f"[{i}] {nome}")
        print(f"    jids: {' | '.join(jids)}")
        if ultima:
            timestamp, is_from_me, content, media_type = ultima
            quem = "EU" if is_from_me else "ELE(A)"
            texto = f"[{media_type}]" if media_type else (content or "").replace("\n", " ")[:90]
            print(f"    ultima: {str(timestamp)[:16]} {quem}: {texto}")
        else:
            print("    ultima: sem mensagens no banco (conversa pode estar em outro jid)")
        print(f"    nota: {nota.name if nota else 'nao existe'}")
    if len(achados) > 1:
        print(
            "\nMais de um resultado: pode ser a mesma pessoa em outro numero ou pessoas "
            "diferentes com nome parecido. Confirmar com o usuario antes de assumir."
        )
