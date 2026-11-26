#!/usr/bin/env bash
# Instala o plugin de WhatsApp em um servidor com Podman (Quadlet), sem root.
#
# Uso, a partir de qualquer pasta, no usuario que roda o agente:
#   bash container/instalar-vps.sh                  prepara tudo e mostra o QR (rode primeiro)
#   bash container/instalar-vps.sh servidor         sobe o servidor MCP e liga o OpenBot a rede dele
#   bash container/instalar-vps.sh status           mostra o que esta rodando
#   bash container/instalar-vps.sh atualizar        vai para a ultima release e refaz as imagens
#
# Opcoes: --audio (imagem com transcricao de audio, bem maior), --sem-openbot (nao mexe no
# OpenBot), --openbot-arquivo <caminho> (padrao: openbot.container na pasta do Quadlet) e
# --sim (nao pergunta antes de editar o arquivo do OpenBot ou de atualizar).
#
# O que ele nunca faz: mostrar a senha da bridge, publicar porta, rodar como root, apagar nada.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pasta_quadlet="${HOME}/.config/containers/systemd"
segredo="whatsapp-bridge-token"
acao="preparar"
audio=0
mexe_no_openbot=1
arquivo_openbot=""
sim=0

while [ $# -gt 0 ]; do
  case "$1" in
    preparar|servidor|status|atualizar) acao="$1" ;;
    --audio) audio=1 ;;
    --sem-openbot) mexe_no_openbot=0 ;;
    --openbot-arquivo) shift; arquivo_openbot="${1:-}" ;;
    --sim) sim=1 ;;
    -h|--help) sed -n '2,14p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Opcao desconhecida: $1 (use --help)" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$arquivo_openbot" ] || arquivo_openbot="${pasta_quadlet}/openbot.container"

avisa() { printf '%s\n' "$*"; }
falha() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }

precisa() {
  command -v "$1" >/dev/null 2>&1 || falha "nao encontrei '$1'. $2"
}

confere_ambiente() {
  precisa podman "Instale o Podman (por exemplo: sudo apt install podman) e rode de novo."
  precisa systemctl "Este script usa o systemd do usuario."
  [ "$(id -u)" -ne 0 ] || falha "nao rode como root: os containers ficam no seu usuario, sem privilegios."
}

# Tag da imagem, lida dos proprios arquivos Quadlet, para nunca ficar diferente deles
imagem_de() {
  sed -n "s/^Image=//p" "${raiz}/container/quadlet/$1" | head -n 1
}

gera_segredo() {
  if podman secret inspect "$segredo" >/dev/null 2>&1; then
    avisa "Senha da bridge: ja existe (nao foi alterada)."
    return
  fi
  # O valor vai direto do gerador para o Podman e nunca passa pela tela
  if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" | podman secret create "$segredo" - >/dev/null
  elif command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 32 | tr -d '\n' | podman secret create "$segredo" - >/dev/null
  else
    falha "preciso do python3 ou do openssl para gerar a senha da bridge."
  fi
  avisa "Senha da bridge: criada como segredo do Podman (o valor nao e mostrado)."
}

construir_imagens() {
  avisa "Construindo a imagem da bridge (pode levar alguns minutos)..."
  podman build -f "${raiz}/container/bridge.Containerfile" -t "$(imagem_de whatsapp-bridge.container)" "$raiz"

  avisa "Construindo a imagem do servidor MCP..."
  if [ "$audio" -eq 1 ]; then
    podman build --build-arg INSTALL_AUDIO=1 -f "${raiz}/container/mcp.Containerfile" -t "$(imagem_de whatsapp-mcp.container)" "$raiz"
  else
    podman build -f "${raiz}/container/mcp.Containerfile" -t "$(imagem_de whatsapp-mcp.container)" "$raiz"
  fi
}

preparar() {
  confere_ambiente
  [ -f "${raiz}/container/bridge.Containerfile" ] || falha "rode de dentro do plugin clonado (nao achei container/bridge.Containerfile)."

  construir_imagens

  avisa "Senha da bridge..."
  gera_segredo

  avisa "Instalando os arquivos do Quadlet em ${pasta_quadlet}..."
  mkdir -p "$pasta_quadlet"
  cp "${raiz}"/container/quadlet/whatsapp-* "$pasta_quadlet"/
  systemctl --user daemon-reload

  avisa "Iniciando a bridge. O QR aparece abaixo."
  systemctl --user start whatsapp-bridge.service
  avisa ""
  avisa "No celular: WhatsApp > Aparelhos conectados > Conectar um aparelho, e leia o QR."
  avisa "Quando aparecer 'Connected to WhatsApp', aperte Ctrl+C: a bridge continua rodando."
  avisa "O QR vale por poucos segundos e se renova sozinho. Depois rode: bash container/instalar-vps.sh servidor"
  avisa ""
  podman logs -f whatsapp-bridge || true
}

confirma() {
  [ "$sim" -eq 1 ] && return 0
  if [ -r /dev/tty ] && [ -w /dev/tty ]; then
    local resposta=""
    printf '%s [s/N] ' "$1" >/dev/tty
    read -r resposta </dev/tty || resposta=""
    case "$resposta" in s|S|sim|SIM|Sim) return 0 ;; esac
  fi
  return 1
}

liga_o_openbot() {
  [ -f "$arquivo_openbot" ] || falha "nao achei ${arquivo_openbot}. Informe o caminho com --openbot-arquivo, ou use --sem-openbot."
  if grep -q '^Network=whatsapp-agente.network' "$arquivo_openbot"; then
    avisa "OpenBot: ja esta ligado a rede whatsapp-agente."
    return
  fi
  avisa ""
  avisa "Vou editar ${arquivo_openbot}: acrescentar 'Network=whatsapp-agente.network' e reiniciar o OpenBot."
  avisa "Uma copia fica em ${arquivo_openbot}.bak. O OpenBot fica fora do ar por alguns segundos."
  confirma "Posso continuar?" || falha "cancelado. Nada foi alterado no OpenBot."
  cp "$arquivo_openbot" "${arquivo_openbot}.bak"
  # Acrescenta a linha logo depois de [Container], sem tocar no resto do arquivo
  awk 'BEGIN{feito=0} {print} /^\[Container\][[:space:]]*$/ && !feito {print "Network=whatsapp-agente.network"; feito=1}' \
    "${arquivo_openbot}.bak" > "$arquivo_openbot"
  grep -q '^Network=whatsapp-agente.network' "$arquivo_openbot" || { cp "${arquivo_openbot}.bak" "$arquivo_openbot"; falha "o arquivo nao tem a secao [Container]; restaurei o original."; }
  systemctl --user daemon-reload
  systemctl --user restart openbot.service
  avisa "OpenBot: ligado a rede whatsapp-agente e reiniciado."
}

servidor() {
  confere_ambiente
  [ -f "${pasta_quadlet}/whatsapp-mcp.container" ] || falha "os arquivos do Quadlet nao estao instalados. Rode primeiro: bash container/instalar-vps.sh"
  systemctl --user start whatsapp-mcp.service
  avisa "Servidor MCP: iniciado."
  if [ "$mexe_no_openbot" -eq 1 ]; then
    liga_o_openbot
  fi
  avisa ""
  avisa "Falta cadastrar o servidor no OpenBot, por URL: http://whatsapp-mcp:8765/mcp"
  avisa "Modo de envio atual: somente leitura. Para mudar, veja docs/guia-de-uso.md."
}

status() {
  confere_ambiente
  for unidade in whatsapp-bridge whatsapp-mcp openbot; do
    estado="$(systemctl --user is-active "${unidade}.service" 2>/dev/null || true)"
    avisa "${unidade}: ${estado:-desconhecido}"
  done
  podman ps --format '{{.Names}}  {{.Status}}' 2>/dev/null | grep -E '^whatsapp-' || true
}

# Vai para a ultima release (tag vX.Y.Z), refaz as imagens e reinicia os servicos. Nao toca no
# volume com a sessao do WhatsApp, na senha (segredo do Podman) nem no arquivo do OpenBot.
atualizar() {
  confere_ambiente
  [ -d "${raiz}/.git" ] || falha "esta pasta nao e um clone do git. Clone o plugin de novo e rode 'preparar' nele."
  precisa git "Instale o git."
  [ -z "$(git -C "$raiz" status --porcelain)" ] || falha "ha alteracoes locais no plugin; guarde-as (git stash) e rode de novo. Nada foi mudado."
  git -C "$raiz" fetch --tags origin
  ultima="$(git -C "$raiz" tag --list 'v*' --sort=-v:refname | head -n 1)"
  [ -n "$ultima" ] || falha "nao achei nenhuma release (tag vX.Y.Z) no repositorio."
  if git -C "$raiz" merge-base --is-ancestor "$ultima" HEAD; then
    avisa "Ja esta na ultima release (${ultima})."
    return
  fi
  avisa "Vou atualizar para ${ultima}, refazer as imagens e reiniciar a bridge e o servidor MCP."
  avisa "A sessao do WhatsApp e a senha continuam como estao. A bridge fica fora por alguns segundos."
  confirma "Posso continuar?" || falha "cancelado. Nada foi alterado."
  git -C "$raiz" merge --ff-only "$ultima" || falha "nao consegui avancar sem misturar historicos. Nada foi mudado."
  construir_imagens
  mkdir -p "$pasta_quadlet"
  cp "${raiz}"/container/quadlet/whatsapp-* "$pasta_quadlet"/
  systemctl --user daemon-reload
  systemctl --user restart whatsapp-bridge.service
  systemctl --user restart whatsapp-mcp.service
  avisa "Atualizado para ${ultima}. O endereco do servidor MCP nao mudou: nao precisa recadastrar no agente."
  avisa "Reinicie o agente se ele nao reconectar sozinho. Confira com: bash container/instalar-vps.sh status"
}

case "$acao" in
  atualizar) atualizar ;;
  preparar) preparar ;;
  servidor) servidor ;;
  status) status ;;
esac
