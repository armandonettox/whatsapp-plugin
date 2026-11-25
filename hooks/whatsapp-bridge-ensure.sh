#!/usr/bin/env bash
# Garante que a bridge do WhatsApp esta rodando; se nao estiver, inicia.
# Por padrao usa a pasta bridge/ deste plugin. Para usar outra, defina WHATSAPP_BRIDGE_DIR.
# O binario e gerado com `go build` (ver README): main.exe no Windows, whatsapp-bridge nos demais.
AQUI="$(cd "$(dirname "$0")" && pwd)"
BRIDGE_DIR="${WHATSAPP_BRIDGE_DIR:-$AQUI/../bridge}"
BRIDGE_DIR="$(cd "$BRIDGE_DIR" 2>/dev/null && pwd)" || { echo "ERRO: pasta da bridge nao encontrada."; exit 1; }

if [ -f "$BRIDGE_DIR/main.exe" ]; then
  BIN="main.exe"
elif [ -f "$BRIDGE_DIR/whatsapp-bridge" ]; then
  BIN="whatsapp-bridge"
else
  echo "ERRO: binario da bridge nao encontrado em $BRIDGE_DIR. Compile com 'go build' (ver README)."
  exit 1
fi

# A bridge guarda os bancos em ../data/store (relativo a ela)
mkdir -p "$BRIDGE_DIR/../data/store"

if command -v tasklist >/dev/null 2>&1; then
  tasklist //FI "IMAGENAME eq $BIN" 2>/dev/null | grep -qi "$BIN" && JA_RODA=1
else
  pgrep -f "$BRIDGE_DIR/$BIN" >/dev/null 2>&1 && JA_RODA=1
fi

if [ -n "$JA_RODA" ]; then
  echo "Bridge ja esta rodando."
  exit 0
fi

cd "$BRIDGE_DIR" || exit 1
nohup "./$BIN" > ../data/bridge.log 2>&1 &
disown 2>/dev/null || true

# A bridge leva alguns segundos para conectar e reenviar o que ficou represado
sleep 8
echo "Bridge estava parada -- iniciei agora em $BRIDGE_DIR. Mensagens de quando ela ficou offline podem demorar a chegar ou nao chegar."
