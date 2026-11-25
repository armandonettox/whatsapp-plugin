"""Banco sintetico no formato da bridge, para testes e para experimentar sem WhatsApp real.

Todos os nomes, numeros e mensagens sao inventados. As datas sao relativas a "agora", entao
o banco sempre parece recente.

Pessoas do cenario:
- Maria Silva: mesma pessoa em dois JIDs (@s.whatsapp.net e @lid); a ultima mensagem e dela
  (pendente de resposta) e esta no @lid.
- Joao Souza: a ultima mensagem e do usuario (nada pendente).
- Pedro Lima e Pedro Lima Filho: duas pessoas diferentes com nome parecido.
- Um grupo de promocoes (deve ser ignorado nas listas de conversas individuais).
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

FUSO = timezone(timedelta(hours=-3))

MARIA_PN = "5511999990001@s.whatsapp.net"
MARIA_LID = "11111111111111@lid"
JOAO_PN = "5511999990002@s.whatsapp.net"
PEDRO_PN = "5511999990003@s.whatsapp.net"
PEDRO_FILHO_PN = "5511999990004@s.whatsapp.net"
GRUPO = "120363000000000001@g.us"


def _ts(minutos_atras: int) -> str:
    """Timestamp no mesmo formato que a bridge grava (ISO com fuso)."""
    return (datetime.now(FUSO) - timedelta(minutes=minutos_atras)).isoformat(sep=" ", timespec="seconds")


def criar_banco(pasta: Path) -> Path:
    """Cria messages.db e whatsapp.db sinteticos em `pasta` e devolve a pasta."""
    pasta.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(pasta / "messages.db")
    con.executescript(
        """
        CREATE TABLE chats (jid TEXT PRIMARY KEY, name TEXT, last_message_time TIMESTAMP);
        CREATE TABLE messages (
            id TEXT, chat_jid TEXT, sender TEXT, content TEXT, timestamp TIMESTAMP,
            is_from_me BOOLEAN, media_type TEXT, filename TEXT, url TEXT,
            PRIMARY KEY (id, chat_jid)
        );
        """
    )
    mensagens = [
        # (chat, de_mim, texto, minutos atras)
        (MARIA_PN, 0, "oi, tudo bem?", 3000),
        (MARIA_PN, 1, "tudo sim, e voce?", 2990),
        (MARIA_LID, 0, "consegue me mandar o relatorio hoje?", 12),
        (JOAO_PN, 0, "reuniao amanha as 10h?", 60),
        (JOAO_PN, 1, "fechado, te vejo la", 55),
        (PEDRO_PN, 0, "bom dia, segue a proposta", 500),
        (PEDRO_FILHO_PN, 1, "obrigado pelo retorno", 800),
        (GRUPO, 0, "PROMOCAO imperdivel, so hoje", 5),
    ]
    for i, (chat, de_mim, texto, atras) in enumerate(mensagens):
        ts = _ts(atras)
        con.execute(
            "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me) VALUES (?,?,?,?,?,?)",
            (f"msg{i}", chat, "eu" if de_mim else chat.split("@")[0], texto, ts, de_mim),
        )
        con.execute(
            "INSERT INTO chats (jid, name, last_message_time) VALUES (?,?,?) "
            "ON CONFLICT(jid) DO UPDATE SET last_message_time = excluded.last_message_time",
            (chat, chat.split("@")[0], ts),
        )
    con.commit()
    con.close()

    con = sqlite3.connect(pasta / "whatsapp.db")
    con.executescript(
        """
        CREATE TABLE whatsmeow_contacts (
            our_jid TEXT, their_jid TEXT, first_name TEXT, full_name TEXT,
            push_name TEXT, business_name TEXT, redacted_phone TEXT
        );
        CREATE TABLE whatsmeow_lid_map (lid TEXT PRIMARY KEY, pn TEXT UNIQUE);
        """
    )
    contatos = [
        (MARIA_PN, "Maria", "Maria Silva", None),
        (MARIA_LID, None, None, "mari"),  # no @lid so existe o apelido que ela definiu
        (JOAO_PN, "Joao", "Joao Souza", None),
        (PEDRO_PN, "Pedro", "Pedro Lima (Cliente)", None),
        (PEDRO_FILHO_PN, "Pedro", "Pedro Lima Filho", None),
    ]
    for jid, primeiro, completo, push in contatos:
        con.execute(
            "INSERT INTO whatsmeow_contacts VALUES (?,?,?,?,?,?,?)",
            ("5511900000000:1@s.whatsapp.net", jid, primeiro, completo, push, None, None),
        )
    con.execute("INSERT INTO whatsmeow_lid_map VALUES (?,?)", ("11111111111111", "5511999990001"))
    con.commit()
    con.close()
    return pasta
