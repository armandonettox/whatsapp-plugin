"""Busca no WhatsApp o historico antigo de um contato, ate o banco parar de crescer.

A bridge so guarda o que chegou enquanto estava ligada. Para uma conversa mais antiga, ela pede
ao celular as N mensagens anteriores a mais antiga que ja existe no banco (endpoint
/api/sync-history). Cada pedido recua um pouco; este script repete ate nao vir mais nada.

Usar quando o historico de um contato parecer curto demais para entender o assunto (ex: so
algumas semanas, mas a conversa e antiga). Precisa da bridge rodando e do celular conectado.

Uso:
    python aprofundar_historico.py <chat_jid> [--count 200] [--rodadas 8] [--espera 20]
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402

PORTA = os.environ.get("WHATSAPP_BRIDGE_PORT", "8081")


def _contar(jids: list) -> tuple:
    """(total de mensagens, timestamp da mais antiga) somando todos os jids do contato."""
    con = comum.abrir_ro(comum.DB_PATH)
    try:
        marcas = ",".join("?" * len(jids))
        return con.execute(
            f"SELECT COUNT(*), MIN(timestamp) FROM messages WHERE chat_jid IN ({marcas})", jids
        ).fetchone()
    finally:
        con.close()


def _cabecalhos() -> dict:
    """Cabecalhos da chamada a bridge; com WHATSAPP_BRIDGE_TOKEN definido, manda a senha."""
    cabecalhos = {"Content-Type": "application/json"}
    token = os.environ.get("WHATSAPP_BRIDGE_TOKEN", "").strip()
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    return cabecalhos


def _pedir(jid: str, count: int) -> str:
    """Pede o historico anterior de um jid. Devolve '' se deu certo, ou o motivo da falha."""
    corpo = json.dumps({"chat_jid": jid, "count": count}).encode()
    pedido = urllib.request.Request(
        f"http://127.0.0.1:{PORTA}/api/sync-history",
        data=corpo, headers=_cabecalhos(), method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=15) as resposta:
            return "" if json.load(resposta).get("success") else "a bridge recusou o pedido"
    except urllib.error.HTTPError as erro:
        try:
            return json.load(erro).get("message", str(erro))
        except ValueError:
            return str(erro)
    except OSError as erro:
        return f"bridge fora do ar na porta {PORTA} ({erro})"


def aprofundar(chat_jid: str, count: int, rodadas: int, espera: int) -> str:
    if not comum.DB_PATH.exists():
        return f"Banco nao encontrado em {comum.DB_PATH}. A bridge ja rodou alguma vez?"

    jids = comum.jids_do_contato(chat_jid)
    total, mais_antiga = _contar(jids)
    inicial = total
    for rodada in range(1, rodadas + 1):
        falhas = [m for m in (_pedir(jid, count) for jid in jids) if m]
        if len(falhas) == len(jids):
            return f"Nao deu para pedir o historico: {falhas[0]}"

        # o celular responde em alguns segundos; espera o banco crescer ou o tempo acabar
        limite = time.time() + espera
        novo_total = total
        while time.time() < limite and novo_total == total:
            time.sleep(2)
            novo_total, mais_antiga = _contar(jids)

        print(f"rodada {rodada}: {total} -> {novo_total} mensagens (mais antiga: {mais_antiga[:10]})")
        if novo_total == total:
            break
        total = novo_total

    return (
        f"Historico de {jids[0]}: {inicial} -> {total} mensagens, da mais antiga em "
        f"{mais_antiga[:10] if mais_antiga else 'n/d'}. Ler com resumo_contato.py --limite 200."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("chat_jid")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--rodadas", type=int, default=8)
    parser.add_argument("--espera", type=int, default=20)
    args = parser.parse_args()
    print(aprofundar(args.chat_jid, args.count, args.rodadas, args.espera))
