# Bridge do WhatsApp em container.
# Construir a partir da raiz do plugin:
#   podman build -f container/bridge.Containerfile -t localhost/whatsapp-bridge:0.1.2 .
#   (com Docker: docker build -f container/bridge.Containerfile -t whatsapp-bridge:0.1.2 .)

FROM docker.io/library/golang:1.25-bookworm AS build
WORKDIR /src
COPY bridge/go.mod bridge/go.sum ./
RUN go mod download
COPY bridge/ ./
# CGO e necessario para o SQLite
RUN CGO_ENABLED=1 go build -trimpath -ldflags="-s -w" -o /out/whatsapp-bridge .

FROM docker.io/library/debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin whatsapp \
    && mkdir -p /app/bridge /app/data/store \
    && chown -R whatsapp:whatsapp /app
COPY --from=build /out/whatsapp-bridge /app/bridge/whatsapp-bridge
USER whatsapp
# A bridge usa caminhos relativos (../data/store): precisa rodar de dentro de /app/bridge
WORKDIR /app/bridge
# Dentro do container a API precisa escutar fora de 127.0.0.1 para o servidor MCP alcancar.
# Por isso a senha (WHATSAPP_BRIDGE_TOKEN) e obrigatoria: sem ela a bridge se recusa a abrir.
ENV WHATSAPP_BRIDGE_ADDR=0.0.0.0
VOLUME ["/app/data"]
EXPOSE 8081
ENTRYPOINT ["/app/bridge/whatsapp-bridge"]
