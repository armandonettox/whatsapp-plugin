"""Resumo das mensagens novas desde a ultima sessao, para rodar no inicio de cada sessao.

Chamado pelo hook SessionStart do projeto. Ele conta quantas mensagens recebidas (de conversas
individuais) chegaram desde a ultima vez que a skill rodou, e quantas pessoas estao por tras
delas. Com --aguardar, antes disso espera o backlog da bridge chegar (use quando a bridge acabou
de ser iniciada).

A janela de contagem fica guardada em .whatsapp-ultima-sessao.json ao lado do banco. Se a sessao
for retomada em menos de 30 minutos, a mesma janela e reaproveitada, para o resumo nao zerar.

Uso:
    python resumo_sessao.py [--aguardar] [--json]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402
from aguardar_backlog import aguardar  # noqa: E402

ARQUIVO_ESTADO = comum.STORE_DIR / ".whatsapp-ultima-sessao.json"
REUSO_MINUTOS = 30
JANELA_INICIAL_HORAS = 24


def _ler_estado():
    try:
        return json.loads(ARQUIVO_ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _janela(agora: datetime) -> datetime:
    """Inicio da janela de contagem. Grava o estado so quando comeca uma janela nova."""
    estado = _ler_estado()
    if estado:
        marcado_em = datetime.fromisoformat(estado["marcado_em"])
        if agora - marcado_em < timedelta(minutes=REUSO_MINUTOS):
            return datetime.fromisoformat(estado["janela_inicio"])
        inicio = marcado_em
    else:
        inicio = agora - timedelta(hours=JANELA_INICIAL_HORAS)
    try:
        ARQUIVO_ESTADO.write_text(
            json.dumps({"janela_inicio": inicio.isoformat(), "marcado_em": agora.isoformat()}),
            encoding="utf-8",
        )
    except OSError:
        pass
    return inicio


def contar_novas(inicio: datetime):
    """(total de mensagens recebidas, numero de conversas) desde `inicio`, so chats individuais."""
    con = comum.abrir_ro(comum.DB_PATH)
    try:
        linhas = con.execute(
            "SELECT chat_jid, timestamp FROM messages "
            "WHERE is_from_me = 0 AND chat_jid NOT LIKE '%@g.us' "
            "AND chat_jid NOT LIKE '%@newsletter' AND chat_jid != 'status@broadcast' "
            "ORDER BY timestamp DESC LIMIT 5000"
        ).fetchall()
    finally:
        con.close()

    chats, total = set(), 0
    for chat_jid, timestamp in linhas:
        try:
            quando = datetime.fromisoformat(timestamp)
        except ValueError:
            continue
        if quando.astimezone() <= inicio.astimezone():
            break
        total += 1
        chats.add(chat_jid)
    return total, len(chats)


def montar_resumo(aguardar_backlog: bool) -> str:
    if not comum.DB_PATH.exists():
        return f"Banco da bridge nao encontrado em {comum.DB_PATH}. A bridge ja rodou alguma vez?"

    partes = []
    if aguardar_backlog:
        partes.append(aguardar(60, 15, 10))

    inicio = _janela(datetime.now().astimezone())
    total, conversas = contar_novas(inicio)
    desde = inicio.astimezone().strftime("%d/%m %H:%M")
    if total:
        partes.append(
            f"WhatsApp: {total} mensagem(ns) nova(s) em {conversas} conversa(s) individual(is) "
            f"desde {desde}. Rodar listar_pendentes.py para ver quem espera resposta."
        )
    else:
        partes.append(f"WhatsApp: nenhuma mensagem nova em conversa individual desde {desde}.")
    return " ".join(partes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aguardar", action="store_true", help="espera o backlog da bridge chegar")
    parser.add_argument("--json", action="store_true", help="saida no formato do hook SessionStart")
    args = parser.parse_args()

    texto = montar_resumo(args.aguardar)
    if args.json:
        print(json.dumps({
            "systemMessage": texto,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": texto},
        }, ensure_ascii=False))
    else:
        print(texto)
