"""Funcoes compartilhadas pelos scripts das skills triagem-whatsapp e notas-por-contato.

Este arquivo existe com o mesmo conteudo nas duas skills, para cada uma funcionar sozinha. Um
teste confere que as duas copias sao identicas: ao mudar uma, copie para a outra.

Onde ficam os dados (a primeira opcao que existir vence):
- banco da bridge (data/store): variavel WHATSAPP_STORE_DIR; senao data/store na raiz do plugin
- notas por contato: variavel WHATSAPP_NOTES_DIR; senao data/notas na raiz do plugin
- rascunhos do modo loop: variavel WHATSAPP_DRAFTS_DIR; senao data/rascunhos na raiz do plugin

A raiz do plugin e a pasta que tem o `data/store`: primeiro a que contem estes scripts e, se a
skill foi copiada para outro lugar (por exemplo, a biblioteca de skills de um agente), a pasta
atual do terminal, as de cima dela e uma pasta `whatsapp-plugin` dentro de cada uma.
"""

import os
import re
import sqlite3
import unicodedata
from pathlib import Path

_RAIZ_DO_SCRIPT = Path(__file__).resolve().parents[3]


def _achar_raiz_do_plugin() -> Path:
    """Raiz do plugin: onde existe data/store/messages.db. Sem achar, a raiz relativa ao script."""
    atual = Path.cwd().resolve()
    candidatos = [_RAIZ_DO_SCRIPT]
    for pasta in [atual, *list(atual.parents)[:4]]:
        candidatos += [pasta, pasta / "whatsapp-plugin"]
    for pasta in candidatos:
        if (pasta / "data" / "store" / "messages.db").is_file():
            return pasta
    return _RAIZ_DO_SCRIPT


_RAIZ_DO_PLUGIN = _achar_raiz_do_plugin()


def pasta_store() -> Path:
    """Pasta data/store da bridge (onde ficam messages.db e whatsapp.db)."""
    candidatos = []
    env = os.environ.get("WHATSAPP_STORE_DIR")
    if env:
        candidatos.append(Path(env))
    candidatos.append(_RAIZ_DO_PLUGIN / "data" / "store")
    for pasta in candidatos:
        if (pasta / "messages.db").exists():
            return pasta
    return candidatos[0]


def pasta_notas() -> Path:
    """Pasta das notas por contato."""
    env = os.environ.get("WHATSAPP_NOTES_DIR")
    return Path(env) if env else _RAIZ_DO_PLUGIN / "data" / "notas"


def pasta_rascunhos() -> Path:
    """Pasta onde o modo loop salva as respostas sugeridas, para a pessoa revisar depois."""
    env = os.environ.get("WHATSAPP_DRAFTS_DIR")
    return Path(env) if env else _RAIZ_DO_PLUGIN / "data" / "rascunhos"


STORE_DIR = pasta_store()
DB_PATH = STORE_DIR / "messages.db"
CONTACTS_DB_PATH = STORE_DIR / "whatsapp.db"


def rotulo_de_midia(media_type, filename=None) -> str:
    """Texto curto para uma mensagem de midia: [document: contrato.pdf] ou so [image]."""
    if not media_type:
        return ""
    return f"[{media_type}: {filename}]" if filename else f"[{media_type}]"


def abrir_ro(caminho: Path) -> sqlite3.Connection:
    """Abre o sqlite so para leitura, para nunca atrapalhar a bridge."""
    return sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)


def jids_do_contato(chat_jid: str) -> list:
    """O mesmo contato pode ter dois JIDs (@lid e @s.whatsapp.net). Usa a tabela
    whatsmeow_lid_map para devolver os dois, para nao ler uma conversa vazia."""
    jids = [chat_jid]
    if not CONTACTS_DB_PATH.exists():
        return jids
    con = abrir_ro(CONTACTS_DB_PATH)
    try:
        numero = chat_jid.split("@")[0]
        for lid, pn in con.execute(
            "SELECT lid, pn FROM whatsmeow_lid_map WHERE lid = ? OR pn = ?", (numero, numero)
        ):
            for jid in (f"{lid}@lid", f"{pn}@s.whatsapp.net"):
                if jid not in jids:
                    jids.append(jid)
    finally:
        con.close()
    return jids


def nome_da_agenda(jids: list, cur_chats=None) -> str:
    """Nome para exibir: nome salvo na agenda, depois push_name (nome que a propria pessoa
    definiu), depois chats.name (ignorando quando e so numero), senao o primeiro jid."""
    linhas = []
    if CONTACTS_DB_PATH.exists():
        con = abrir_ro(CONTACTS_DB_PATH)
        try:
            linhas = [
                con.execute(
                    "SELECT full_name, push_name FROM whatsmeow_contacts WHERE their_jid = ?",
                    (jid,),
                ).fetchone()
                for jid in jids
            ]
        finally:
            con.close()
    for row in linhas:
        if row and row[0]:
            return row[0]
    for row in linhas:
        if row and row[1]:
            return row[1]
    if cur_chats is not None:
        marcas = ",".join("?" * len(jids))
        for (nome,) in cur_chats.execute(
            f"SELECT name FROM chats WHERE jid IN ({marcas}) AND name IS NOT NULL", jids
        ):
            if nome and not nome.isdigit():
                return nome
    return jids[0]


def slug(nome: str) -> str:
    """Nome em minusculo, sem acento, sem o que vem entre parenteses, espacos viram hifen."""
    nome = re.sub(r"\(.*?\)", "", nome).strip()
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-") or "contato"


def achar_nota(jids: list):
    """Procura nas notas uma que cite algum dos jids no cabecalho. Devolve o Path ou None.
    Assim a nota e achada mesmo que o slug do nome tenha mudado."""
    pasta = pasta_notas()
    if not pasta.exists():
        return None
    for arquivo in sorted(pasta.glob("*.md")):
        if arquivo.name.startswith("_"):
            continue
        cabecalho = arquivo.read_text(encoding="utf-8")[:600]
        if any(jid in cabecalho for jid in jids):
            return arquivo
    return None
