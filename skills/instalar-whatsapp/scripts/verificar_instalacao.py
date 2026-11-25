"""Verifica a instalacao do plugin de WhatsApp e diz o que falta, na ordem em que deve ser feito.

Uso:
    python verificar_instalacao.py                       confere a instalacao nativa (padrao)
    python verificar_instalacao.py --caminho container   confere os pre-requisitos de container
    python verificar_instalacao.py --json                saida em JSON, para um agente ler

So le: nao instala nada, nao altera arquivos e nunca mostra o valor da senha da bridge.
Cada linha tem um estado: OK (pronto), FALTA (precisa ser feito), AVISO (funciona, mas revise)
ou INFO (so informacao). Sai com codigo 1 se algo obrigatorio faltar.
"""

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PORTA_DA_BRIDGE = 8081
VERSAO_MINIMA_DO_GO = (1, 25)
VERSAO_MINIMA_DO_PYTHON = (3, 11)
MODOS = ("read-only", "two-step", "hook")


def linha(estado: str, nome: str, detalhe: str = "", proximo: str = "") -> dict:
    return {"estado": estado, "nome": nome, "detalhe": detalhe, "proximo": proximo}


def versao_de(comando: list, padrao: str = r"(\d+)\.(\d+)(?:\.(\d+))?"):
    """Roda `comando` e devolve (major, minor) da primeira versao que aparecer, ou None."""
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    achado = re.search(padrao, saida.stdout + saida.stderr)
    return (int(achado.group(1)), int(achado.group(2))) if achado else None


def modo_de_envio(ambiente: dict) -> str:
    """Mesma regra do servidor: valor desconhecido ou vazio vira read-only."""
    valor = (ambiente.get("WHATSAPP_SEND_MODE") or "").strip().lower().replace("_", "-")
    return valor if valor in MODOS else "read-only"


def verificar_ferramentas(caminho: str, procurar=shutil.which, versao=versao_de) -> list:
    linhas = []
    atual = sys.version_info[:2]
    if atual >= VERSAO_MINIMA_DO_PYTHON:
        linhas.append(linha("OK", "Python", f"{atual[0]}.{atual[1]}"))
    else:
        linhas.append(linha("FALTA", "Python", f"{atual[0]}.{atual[1]}", "Instale o Python 3.11 ou superior."))

    if caminho == "container":
        motor = procurar("podman") or procurar("docker")
        if motor:
            linhas.append(linha("OK", "Podman ou Docker", Path(motor).stem))
        else:
            linhas.append(linha("FALTA", "Podman ou Docker", "", "Instale o Podman ou o Docker para rodar os containers."))
        return linhas

    if procurar("uv"):
        linhas.append(linha("OK", "uv", "roda o servidor MCP"))
    else:
        linhas.append(linha("FALTA", "uv", "", "Instale o uv (https://docs.astral.sh/uv/)."))

    if procurar("go"):
        encontrada = versao(["go", "version"], r"go(\d+)\.(\d+)")
        if encontrada and encontrada >= VERSAO_MINIMA_DO_GO:
            linhas.append(linha("OK", "Go", f"{encontrada[0]}.{encontrada[1]}"))
        else:
            texto = f"{encontrada[0]}.{encontrada[1]}" if encontrada else "versao nao reconhecida"
            linhas.append(linha("FALTA", "Go", texto, "Atualize o Go para a versao 1.25 ou superior."))
    else:
        linhas.append(linha("FALTA", "Go", "", "Instale o Go 1.25 ou superior (https://go.dev/dl/)."))

    if procurar("gcc") or procurar("cc") or procurar("clang"):
        linhas.append(linha("OK", "Compilador C", "necessario para o SQLite da bridge"))
    else:
        linhas.append(linha("FALTA", "Compilador C", "", "Instale um compilador C (no Windows, MSYS2 com o pacote mingw-w64-x86_64-gcc)."))

    if procurar("ffmpeg"):
        linhas.append(linha("OK", "ffmpeg", "opcional: audios"))
    else:
        linhas.append(linha("INFO", "ffmpeg", "ausente", "So e preciso para transcrever audios e enviar mensagens de voz."))
    return linhas


def verificar_bridge(raiz: Path) -> list:
    pasta = raiz / "bridge"
    binarios = [pasta / "main.exe", pasta / "whatsapp-bridge"]
    existente = next((b for b in binarios if b.is_file()), None)
    if existente:
        return [linha("OK", "Bridge compilada", existente.name)]
    return [linha("FALTA", "Bridge compilada", "", "Baixe a pronta: python skills/instalar-whatsapp/scripts/baixar_bridge.py (sem Go nem compilador). Se nao houver para o seu sistema, compile: cd bridge && go build -o main.exe . (Windows) ou go build -o whatsapp-bridge . (outros)")]


def sessao_pareada(pasta_store: Path):
    """True se o banco da sessao tem um aparelho pareado, False se esta vazio, None se nao existe."""
    banco = pasta_store / "whatsapp.db"
    if not banco.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
        try:
            return con.execute("SELECT COUNT(*) FROM whatsmeow_device").fetchone()[0] > 0
        finally:
            con.close()
    except sqlite3.Error:
        return None


def verificar_sessao(raiz: Path, ambiente: dict) -> list:
    pasta = Path(ambiente.get("WHATSAPP_STORE_DIR") or raiz / "data" / "store")
    estado = sessao_pareada(pasta)
    if estado is True:
        return [linha("OK", "WhatsApp pareado", "a sessao existe")]
    return [linha("FALTA", "WhatsApp pareado", "ainda nao", "Peca a pessoa para rodar a bridge em um terminal dela e ler o QR no celular (Aparelhos conectados).")]


def porta_aceita(host: str, porta: int, tempo: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, porta), timeout=tempo):
            return True
    except OSError:
        return False


def verificar_bridge_rodando(ambiente: dict, aceita=porta_aceita, enderecos_da_maquina=None, pareada=True) -> list:
    if not aceita("127.0.0.1", PORTA_DA_BRIDGE):
        return [linha("INFO", "Bridge rodando", "nao esta escutando agora", "Inicie a bridge (o hook do Claude Code faz isso sozinho; nos outros agentes, inicie a mao).")]
    if pareada:
        linhas = [linha("OK", "Bridge rodando", f"porta {PORTA_DA_BRIDGE} no proprio computador")]
    else:
        # Algo escuta na porta, mas este plugin ainda nao tem sessao: provavelmente e outra bridge
        linhas = [linha("AVISO", f"Porta {PORTA_DA_BRIDGE} ocupada por outro processo",
                        "este plugin ainda nao esta pareado, entao nao e a bridge dele",
                        "Nao feche o processo sozinho: pergunte a pessoa de quem e. Duas bridges disputam a mesma sessao e a mesma porta.")]
    if enderecos_da_maquina is None:
        try:
            enderecos_da_maquina = [a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
        except OSError:
            enderecos_da_maquina = []
    expostos = [e for e in enderecos_da_maquina if not e.startswith("127.") and aceita(e, PORTA_DA_BRIDGE)]
    senha = bool((ambiente.get("WHATSAPP_BRIDGE_TOKEN") or "").strip())
    if expostos and not senha:
        linhas.append(linha("FALTA", "Bridge exposta na rede", "aceita conexao fora do computador, sem senha",
                            "Feche a bridge e inicie a versao deste plugin, que escuta so em 127.0.0.1, ou defina WHATSAPP_BRIDGE_TOKEN."))
    elif expostos:
        linhas.append(linha("AVISO", "Bridge escutando fora do computador", "protegida pela senha", "Confirme que e de proposito (container)."))
    return linhas


def verificar_envio(ambiente: dict) -> list:
    modo = modo_de_envio(ambiente)
    senha = bool((ambiente.get("WHATSAPP_BRIDGE_TOKEN") or "").strip())
    linhas = [linha("INFO", "Modo de envio", modo)]
    if modo == "hook":
        linhas.append(linha("AVISO", "Modo hook", "envia direto", "So use no Claude Code, onde o guarda confirma cada envio."))
    linhas.append(linha("OK" if senha else "INFO", "Senha da bridge", "definida" if senha else "nao definida",
                        "" if senha else "Em containers a senha e obrigatoria. Fora deles, um agente com terminal consegue ler a senha: nesse caso prefira o caminho de containers."))
    return linhas


def verificar_dados(raiz: Path) -> list:
    pasta = raiz / "data"
    if pasta.exists():
        return [linha("OK" if os.access(pasta, os.W_OK) else "FALTA", "Pasta data/", "existe" if os.access(pasta, os.W_OK) else "sem permissao de escrita")]
    return [linha("INFO", "Pasta data/", "ainda nao existe", "Sera criada na primeira execucao.")]


def mcp_no_ambiente_do_servidor(raiz: Path) -> bool:
    """True se o ambiente que o uv criou em server/.venv tem o pacote mcp."""
    venv = raiz / "server" / ".venv"
    pacotes = [venv / "Lib" / "site-packages"] + sorted(venv.glob("lib/python*/site-packages"))
    return any((p / "mcp").is_dir() for p in pacotes)


def verificar_pacote_mcp(raiz: Path = RAIZ) -> list:
    if mcp_no_ambiente_do_servidor(raiz):
        return [linha("OK", "Pacote mcp do servidor", "instalado no ambiente do uv (server/.venv)")]
    if importlib.util.find_spec("mcp") is not None:
        return [linha("INFO", "Pacote mcp neste Python", "instalado (o uv usa o ambiente proprio do servidor)")]
    return [linha("INFO", "Pacote mcp do servidor", "ainda nao instalado", "Normal antes da primeira execucao: o uv instala as dependencias do servidor no ambiente dele.")]


def verificar(raiz: Path = RAIZ, ambiente=None, caminho: str = "nativo") -> list:
    ambiente = dict(os.environ if ambiente is None else ambiente)
    linhas = verificar_ferramentas(caminho)
    if caminho == "nativo":
        linhas += verificar_bridge(raiz)
        sessao = verificar_sessao(raiz, ambiente)
        linhas += sessao
        linhas += verificar_bridge_rodando(ambiente, pareada=all(l["estado"] == "OK" for l in sessao))
        linhas += verificar_pacote_mcp(raiz)
    linhas += verificar_envio(ambiente)
    linhas += verificar_dados(raiz)
    return linhas


def resumo(linhas: list) -> dict:
    faltam = [l for l in linhas if l["estado"] == "FALTA"]
    return {"pronto": not faltam, "faltam": len(faltam), "proximo": faltam[0]["proximo"] if faltam else ""}


def formatar(linhas: list) -> str:
    saida = [f"Sistema: {platform.system()} {platform.machine()}", ""]
    for l in linhas:
        texto = f"[{l['estado']:5}] {l['nome']}"
        if l["detalhe"]:
            texto += f": {l['detalhe']}"
        saida.append(texto)
        if l["estado"] in ("FALTA", "AVISO") and l["proximo"]:
            saida.append(f"        -> {l['proximo']}")
    r = resumo(linhas)
    saida.append("")
    saida.append("Tudo o que e obrigatorio esta pronto." if r["pronto"] else f"Faltam {r['faltam']} item(ns). Comece por: {r['proximo']}")
    return "\n".join(saida)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--caminho", choices=("nativo", "container"), default="nativo")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    linhas = verificar(caminho=args.caminho)
    if args.json:
        print(json.dumps({"linhas": linhas, **resumo(linhas)}, ensure_ascii=False))
    else:
        print(formatar(linhas))
    return 0 if resumo(linhas)["pronto"] else 1


if __name__ == "__main__":
    sys.exit(main())
