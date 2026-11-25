"""Espera o backlog da bridge terminar de chegar depois de ela ser reiniciada.

Quando a bridge fica parada, as mensagens desse periodo sao reenviadas aos poucos (em ordem
cronologica) assim que ela reconecta. Concluir "nao tem mensagem nova" antes disso da resposta
errada. Este script sai quando:
- a mensagem mais recente do banco e recente (a bridge ja esta em dia), ou
- o numero de mensagens para de crescer por um tempo (o replay estabilizou), ou
- o tempo maximo acaba.

Uso:
    python aguardar_backlog.py [--max 180] [--estavel 25] [--recente 10]
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import _comum as comum  # noqa: E402


def _estado() -> tuple:
    con = comum.abrir_ro(comum.DB_PATH)
    try:
        return con.execute("SELECT MAX(timestamp), COUNT(*) FROM messages").fetchone()
    finally:
        con.close()


def _minutos_desde(timestamp: str) -> float:
    ultima = datetime.fromisoformat(timestamp)
    return (datetime.now(ultima.tzinfo) - ultima).total_seconds() / 60


def aguardar(maximo: int, estavel: int, recente: int) -> str:
    if not comum.DB_PATH.exists():
        return f"Banco nao encontrado em {comum.DB_PATH}. A bridge ja rodou alguma vez?"

    ultima, total = _estado()
    if ultima and _minutos_desde(ultima) <= recente:
        return f"Banco em dia: ultima mensagem de {ultima[:16]}."

    inicio = time.time()
    sem_mudar_desde = time.time()
    while time.time() - inicio < maximo:
        time.sleep(5)
        ultima, novo_total = _estado()
        if ultima and _minutos_desde(ultima) <= recente:
            return f"Backlog chegou ate agora: ultima mensagem de {ultima[:16]}."
        if novo_total != total:
            total, sem_mudar_desde = novo_total, time.time()
        elif time.time() - sem_mudar_desde >= estavel:
            return (
                f"Replay estabilizou em {ultima[:16] if ultima else 'sem mensagens'} "
                f"(sem mensagens novas ha {estavel}s). Se for bem antes de agora, o que "
                f"passou enquanto a bridge estava parada pode nao voltar."
            )
    return (
        f"Tempo maximo ({maximo}s) acabou; ultima mensagem no banco: "
        f"{ultima[:16] if ultima else 'nenhuma'}. O backlog pode ainda estar chegando."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=180)
    parser.add_argument("--estavel", type=int, default=25)
    parser.add_argument("--recente", type=int, default=10)
    args = parser.parse_args()

    print(aguardar(args.max, args.estavel, args.recente))
