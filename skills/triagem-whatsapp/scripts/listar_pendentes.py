"""Lista conversas individuais do WhatsApp com mensagem pendente de resposta.

Le direto do sqlite da bridge (mais rapido que paginar list_chats via MCP).
So mostra chats individuais (@s.whatsapp.net ou @lid de pessoa) onde a
ultima mensagem nao foi enviada por "Me".

O mesmo contato pode ter dois JIDs (@lid e @s.whatsapp.net). Aqui eles sao
agrupados pelo mapa whatsmeow_lid_map e a ultima mensagem considerada e a mais
recente entre os dois.

Uso:
    python listar_pendentes.py [--limite 20]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402


def _carregar_mapa_lid(con_contacts) -> dict:
    """Devolve {lid@lid: numero@s.whatsapp.net} a partir de whatsmeow_lid_map."""
    linhas = con_contacts.execute("SELECT lid, pn FROM whatsmeow_lid_map").fetchall()
    return {f"{lid}@lid": f"{pn}@s.whatsapp.net" for lid, pn in linhas}


def listar_pendentes(limite: int = 20):
    if not comum.DB_PATH.exists():
        print(f"Banco nao encontrado em {comum.DB_PATH}. A bridge ja rodou pelo menos uma vez?")
        return []

    con = comum.abrir_ro(comum.DB_PATH)
    cur = con.cursor()

    mapa_lid = {}
    if comum.CONTACTS_DB_PATH.exists():
        con_contacts = comum.abrir_ro(comum.CONTACTS_DB_PATH)
        mapa_lid = _carregar_mapa_lid(con_contacts)
        con_contacts.close()

    # jids de cada pessoa, agrupados pelo numero (@s.whatsapp.net) quando existe mapa
    jids_por_pessoa = {}
    for lid, pn in mapa_lid.items():
        jids_por_pessoa.setdefault(pn, [pn]).append(lid)

    cur.execute(
        """
        SELECT c.jid
        FROM chats c
        WHERE c.jid NOT LIKE '%@g.us'
          AND c.jid NOT LIKE '%@newsletter'
          AND c.jid != 'status@broadcast'
        ORDER BY c.last_message_time DESC
        LIMIT ?
        """,
        (limite * 6,),
    )
    chats = [jid for (jid,) in cur.fetchall()]

    pendentes = []
    vistos = set()
    for jid in chats:
        pessoa = mapa_lid.get(jid, jid)
        if pessoa in vistos:
            continue
        vistos.add(pessoa)

        jids = jids_por_pessoa.get(pessoa, [jid])
        marcas = ",".join("?" * len(jids))
        cur.execute(
            f"SELECT chat_jid, is_from_me, content, media_type, timestamp FROM messages "
            f"WHERE chat_jid IN ({marcas}) ORDER BY timestamp DESC LIMIT 1",
            jids,
        )
        row = cur.fetchone()
        if not row:
            continue
        jid_ativo, is_from_me, content, media_type, ultima = row
        if is_from_me:
            continue

        preview = content if content else f"[{media_type}]" if media_type else ""
        pendentes.append((jid_ativo, comum.nome_da_agenda(jids, cur), ultima, preview))
        if len(pendentes) >= limite:
            break

    con.close()
    return pendentes


def _checar_frescor(cur, horas_limite: int = 6) -> None:
    """Avisa se a mensagem mais recente de QUALQUER chat (incluindo grupos) e mais
    antiga que horas_limite. A bridge so recupera mensagens novas via push em tempo
    real -- se ela ficou offline, o sync sob demanda so busca historico MAIS ANTIGO que
    uma ancora, nunca mensagens novas que passaram enquanto estava desconectada
    (limitacao do proprio protocolo, ver references/problemas-da-bridge.md da skill usar-whatsapp-mcp). Sem esse
    aviso, a lista pode parecer o estado atual quando a bridge parou de atualizar."""
    cur.execute("SELECT MAX(timestamp) FROM messages")
    row = cur.fetchone()
    if not row or not row[0]:
        return
    try:
        ultima = datetime.fromisoformat(row[0])
    except ValueError:
        return
    agora = datetime.now(ultima.tzinfo)
    horas_desde = (agora - ultima).total_seconds() / 3600
    if horas_desde > horas_limite:
        print(
            f"AVISO: a mensagem mais recente no banco (qualquer chat) e de "
            f"{row[0]}, ha {horas_desde:.1f}h. Isso pode indicar que a bridge ficou "
            f"offline e nao recuperou mensagens novas ao reconectar. NAO tratar a "
            f"lista abaixo como estado atual sem confirmar que a bridge esta "
            f"recebendo mensagens ao vivo. Se a bridge acabou de reiniciar, rodar "
            f"scripts/aguardar_backlog.py e depois esta lista de novo.\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=20)
    args = parser.parse_args()

    if comum.DB_PATH.exists():
        con_check = comum.abrir_ro(comum.DB_PATH)
        _checar_frescor(con_check.cursor())
        con_check.close()

    resultado = listar_pendentes(args.limite)
    if not resultado:
        print("Nenhuma conversa individual pendente encontrada.")
    for jid, name, last_time, preview in resultado:
        print(f"[{last_time}] {name or jid} ({jid})\n  -> {preview}\n")
