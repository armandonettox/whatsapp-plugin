"""Modos de envio do servidor MCP e rascunhos pendentes.

O guarda de envio do plugin e um hook do Claude Code: em outros agentes ele nao existe. Para o
servidor ser seguro em qualquer agente, quem decide se uma mensagem sai e o proprio servidor,
pela variavel WHATSAPP_SEND_MODE:

  read-only  (padrao) as ferramentas de envio nem aparecem para o agente.
  two-step   as ferramentas de envio so criam um rascunho. Quem envia e a pessoa, no terminal,
             com "python confirm.py send <id>", fora do agente.
  hook       as ferramentas enviam direto. So use onde um hook confirma cada envio (o plugin no
             Claude Code liga esse modo sozinho).

O transporte (stdio ou HTTP) e escolhido por WHATSAPP_MCP_TRANSPORT; veja configuracao_de_transporte.

Valor desconhecido ou vazio cai em read-only, o mais seguro.

Este arquivo usa so a biblioteca padrao, para poder ser testado em qualquer lugar.
"""

import json
import os
import re
import secrets
import time
from pathlib import Path

MODOS = ("read-only", "two-step", "hook")
MODO_PADRAO = "read-only"

VALIDADE_PADRAO_SEGUNDOS = 30 * 60
MAXIMO_DE_PENDENTES = 20
TAMANHO_MAXIMO_DA_MENSAGEM = 10000
TIPOS = ("message", "file", "audio")

ID_VALIDO = re.compile(r"^[0-9a-f]{8}$")


def modo_de_envio(ambiente=None) -> str:
    """Le WHATSAPP_SEND_MODE. Qualquer valor fora da lista vira read-only."""
    ambiente = os.environ if ambiente is None else ambiente
    valor = (ambiente.get("WHATSAPP_SEND_MODE") or "").strip().lower().replace("_", "-")
    return valor if valor in MODOS else MODO_PADRAO


def pasta_de_pendentes(ambiente=None) -> Path:
    ambiente = os.environ if ambiente is None else ambiente
    pasta = ambiente.get("WHATSAPP_PENDING_DIR")
    if pasta:
        return Path(pasta)
    return Path(__file__).resolve().parents[1] / "data" / "pending"


def validade_em_segundos(ambiente=None) -> int:
    ambiente = os.environ if ambiente is None else ambiente
    try:
        valor = int(ambiente.get("WHATSAPP_PENDING_TTL_MINUTES", "") or 0) * 60
    except ValueError:
        valor = 0
    return valor if valor > 0 else VALIDADE_PADRAO_SEGUNDOS


TRANSPORTES = ("stdio", "streamable-http")
HOSTS_LOCAIS = ("127.0.0.1", "localhost", "::1")
PORTA_PADRAO_HTTP = 8765


class ErroDeConfiguracao(Exception):
    """Configuracao de transporte invalida ou insegura (mensagem para quem instalou)."""


def configuracao_de_transporte(ambiente=None) -> dict:
    """Le como o servidor MCP deve falar com o agente.

    WHATSAPP_MCP_TRANSPORT: stdio (padrao) ou streamable-http. Valor desconhecido da erro,
    porque cair em silencio num transporte aberto seria pior do que nao subir.
    WHATSAPP_MCP_HOST e WHATSAPP_MCP_PORT: endereco do modo HTTP (padrao 127.0.0.1:8765).
    WHATSAPP_MCP_ALLOWED_HOSTS: nomes aceitos no cabecalho Host, separados por virgula
    (por exemplo "whatsapp-mcp:8765"). Obrigatorio quando o host nao e local, que e o caso de um
    container: sem a lista o servidor se recusa a abrir, em vez de ficar aberto para qualquer nome.
    """
    ambiente = os.environ if ambiente is None else ambiente
    transporte = (ambiente.get("WHATSAPP_MCP_TRANSPORT") or "stdio").strip().lower().replace("_", "-")
    if transporte not in TRANSPORTES:
        raise ErroDeConfiguracao(
            f"WHATSAPP_MCP_TRANSPORT invalido: use {' ou '.join(TRANSPORTES)}."
        )
    config = {"transporte": transporte, "host": "127.0.0.1", "porta": PORTA_PADRAO_HTTP, "hosts_permitidos": []}
    if transporte == "stdio":
        return config
    config["host"] = (ambiente.get("WHATSAPP_MCP_HOST") or "127.0.0.1").strip()
    bruta = (ambiente.get("WHATSAPP_MCP_PORT") or "").strip()
    if bruta:
        if not bruta.isdigit() or not 1 <= int(bruta) <= 65535:
            raise ErroDeConfiguracao("WHATSAPP_MCP_PORT invalida: use um numero de 1 a 65535.")
        config["porta"] = int(bruta)
    config["hosts_permitidos"] = [
        h.strip() for h in (ambiente.get("WHATSAPP_MCP_ALLOWED_HOSTS") or "").split(",") if h.strip()
    ]
    if config["host"] not in HOSTS_LOCAIS and not config["hosts_permitidos"]:
        raise ErroDeConfiguracao(
            "O servidor HTTP foi pedido fora do computador (WHATSAPP_MCP_HOST) sem WHATSAPP_MCP_ALLOWED_HOSTS. "
            "Liste os nomes aceitos no cabecalho Host (por exemplo whatsapp-mcp:8765) e mantenha a rede isolada."
        )
    return config


class ErroDeRascunho(Exception):
    """Pedido de rascunho invalido (mensagem para o agente corrigir)."""


def _caminho(pasta: Path, id_: str, sufixo: str) -> Path:
    if not ID_VALIDO.match(id_ or ""):
        raise ErroDeRascunho("Identificador de rascunho invalido.")
    return pasta / f"{id_}.{sufixo}"


def criar_pendente(tipo, destinatario, mensagem=None, arquivo=None, pasta=None, agora=None, validade=None) -> dict:
    """Guarda um rascunho. Nao envia nada. Devolve o registro criado."""
    pasta = pasta or pasta_de_pendentes()
    agora = time.time() if agora is None else agora
    validade = validade or validade_em_segundos()

    if tipo not in TIPOS:
        raise ErroDeRascunho("Tipo de envio desconhecido.")
    destinatario = (destinatario or "").strip()
    if not destinatario:
        raise ErroDeRascunho("Informe o destinatario.")
    if tipo == "message":
        mensagem = mensagem or ""
        if not mensagem.strip():
            raise ErroDeRascunho("A mensagem esta vazia.")
        if len(mensagem) > TAMANHO_MAXIMO_DA_MENSAGEM:
            raise ErroDeRascunho(f"A mensagem passa de {TAMANHO_MAXIMO_DA_MENSAGEM} caracteres.")
    else:
        caminho = Path(arquivo or "")
        if not caminho.is_absolute():
            raise ErroDeRascunho("Informe o caminho absoluto do arquivo.")
        if not caminho.is_file():
            raise ErroDeRascunho("O arquivo nao existe.")
        arquivo = str(caminho)

    pasta.mkdir(parents=True, exist_ok=True)
    pendentes = listar_pendentes(pasta, agora)
    if len(pendentes) >= MAXIMO_DE_PENDENTES:
        raise ErroDeRascunho(
            f"Ja ha {MAXIMO_DE_PENDENTES} rascunhos esperando confirmacao. A pessoa precisa enviar ou descartar alguns."
        )

    id_ = secrets.token_hex(4)
    while _caminho(pasta, id_, "json").exists():
        id_ = secrets.token_hex(4)
    registro = {
        "id": id_,
        "tipo": tipo,
        "destinatario": destinatario,
        "mensagem": mensagem if tipo == "message" else None,
        "arquivo": arquivo if tipo != "message" else None,
        "criado_em": agora,
        "expira_em": agora + validade,
    }
    destino = _caminho(pasta, id_, "json")
    destino.write_text(json.dumps(registro, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass
    return registro


def carregar_pendente(id_, pasta=None, agora=None):
    """Devolve o rascunho, ou None se nao existir ou tiver expirado (e apaga o expirado)."""
    pasta = pasta or pasta_de_pendentes()
    agora = time.time() if agora is None else agora
    caminho = _caminho(pasta, id_, "json")
    if not caminho.is_file():
        return None
    try:
        registro = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if registro.get("expira_em", 0) <= agora:
        marcar(pasta, id_, "expired")
        return None
    return registro


def listar_pendentes(pasta=None, agora=None) -> list:
    pasta = pasta or pasta_de_pendentes()
    agora = time.time() if agora is None else agora
    if not pasta.is_dir():
        return []
    registros = []
    for arquivo in pasta.glob("*.json"):
        id_ = arquivo.stem
        if not ID_VALIDO.match(id_):
            continue
        registro = carregar_pendente(id_, pasta, agora)
        if registro:
            registros.append(registro)
    return sorted(registros, key=lambda r: r["criado_em"])


def marcar(pasta: Path, id_: str, estado: str) -> None:
    """Troca o rascunho por um marcador simples (sent, discarded, expired), sem guardar o texto."""
    caminho = _caminho(pasta, id_, "json")
    if caminho.exists():
        caminho.unlink()
    (pasta / f"{id_}.{estado}").write_text(str(int(time.time())), encoding="utf-8")


def estado_do_pendente(id_, pasta=None, agora=None) -> str:
    """pending, sent, discarded, expired ou unknown. Nao revela o conteudo."""
    pasta = pasta or pasta_de_pendentes()
    if not ID_VALIDO.match(id_ or ""):
        return "unknown"
    if carregar_pendente(id_, pasta, agora):
        return "pending"
    for estado in ("sent", "discarded", "expired"):
        if _caminho(pasta, id_, estado).exists():
            return estado
    return "unknown"
