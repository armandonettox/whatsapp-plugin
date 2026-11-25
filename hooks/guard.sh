#!/usr/bin/env bash
# Executa o whatsapp-send-guard.py com o python que existir na maquina.
# Falha FECHADA: se nao achar um python que funcione, bloqueia o envio (saida 2) em vez de
# deixar passar -- um guardrail que libera quando nao consegue checar nao protege nada.
DIR="$(cd "$(dirname "$0")" && pwd)"

PY=""
for candidato in python3 python py; do
  if command -v "$candidato" >/dev/null 2>&1 && "$candidato" -c "import sys" >/dev/null 2>&1; then
    PY="$candidato"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "BLOQUEADO -- WhatsApp Send Guard: python nao encontrado, nao foi possivel verificar a confirmacao." >&2
  exit 2
fi

exec "$PY" "$DIR/whatsapp-send-guard.py"
