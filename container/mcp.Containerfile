# Servidor MCP do WhatsApp em container, falando por HTTP.
# Construir a partir da raiz do plugin:
#   podman build -f container/mcp.Containerfile -t localhost/whatsapp-mcp:0.1.0 .
#   Com transcricao de audio (imagem bem maior): acrescente --build-arg INSTALL_AUDIO=1
#   (com Docker: docker build -f container/mcp.Containerfile -t whatsapp-mcp:0.1.0 .)

FROM docker.io/library/python:3.12-slim-bookworm
ARG INSTALL_AUDIO=0
RUN pip install --no-cache-dir uv \
    && useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin whatsapp \
    && mkdir -p /app/server /app/data \
    && chown -R whatsapp:whatsapp /app
WORKDIR /app/server
COPY --chown=whatsapp:whatsapp server/pyproject.toml server/uv.lock ./
USER whatsapp
RUN uv sync --frozen --no-dev --no-install-project
USER root
RUN if [ "$INSTALL_AUDIO" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends ffmpeg \
      && rm -rf /var/lib/apt/lists/* \
      && su whatsapp -s /bin/sh -c "cd /app/server && uv sync --frozen --no-dev --no-install-project --extra audio"; \
    fi
COPY --chown=whatsapp:whatsapp server/ ./
USER whatsapp
ENV PATH="/app/server/.venv/bin:${PATH}" \
    WHATSAPP_MCP_TRANSPORT=streamable-http \
    WHATSAPP_MCP_HOST=0.0.0.0 \
    WHATSAPP_MCP_PORT=8765 \
    WHATSAPP_MCP_ALLOWED_HOSTS="whatsapp-mcp:8765,127.0.0.1:8765,localhost:8765" \
    WHATSAPP_API_BASE_URL="http://whatsapp-bridge:8081/api" \
    WHATSAPP_SEND_MODE=read-only
VOLUME ["/app/data"]
EXPOSE 8765
ENTRYPOINT ["python", "main.py"]
