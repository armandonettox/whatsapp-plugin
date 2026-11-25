"""Baixa a bridge ja compilada da release do GitHub e confere o SHA-256.

Uso (a partir da pasta do plugin):
    python skills/instalar-whatsapp/scripts/baixar_bridge.py [--forcar] [--versao 0.1.1]

Evita instalar Go e um compilador C: a release traz a bridge pronta para Windows, Linux e macOS
(amd64 e arm64). O arquivo e gravado em bridge/main.exe (Windows) ou bridge/whatsapp-bridge
(Linux e macOS), os mesmos nomes que `go build` produz, e o resto do plugin nao percebe a
diferenca. Sem binario para o sistema, ou sem rede, o script diz isso e a pessoa compila.

Codigos de saida: 0 baixou e conferiu; 1 ja existia (use --forcar); 2 sem binario para este
sistema; 3 o SHA-256 nao confere (nada e gravado); 4 falha de rede ou arquivo ausente na release.
"""

import argparse
import hashlib
import json
import os
import platform
import stat
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
REPO_PADRAO = "armandonettox/whatsapp-plugin"
SISTEMAS = {"windows": "windows", "linux": "linux", "darwin": "darwin"}
ARQUITETURAS = {"amd64": "amd64", "x86_64": "amd64", "x64": "amd64", "arm64": "arm64", "aarch64": "arm64"}
# Combinacoes que a release publica (o fluxo de release gera exatamente estas)
DISPONIVEIS = {("windows", "amd64"), ("linux", "amd64"), ("linux", "arm64"), ("darwin", "arm64"), ("darwin", "amd64")}


class SemBinario(Exception):
    pass


class ErroDeSoma(Exception):
    pass


class ErroDeRede(Exception):
    pass


def nome_do_arquivo(sistema: str, maquina: str) -> str:
    """Nome do binario na release para o sistema e a arquitetura dados."""
    so = SISTEMAS.get(sistema.lower())
    arq = ARQUITETURAS.get(maquina.lower())
    if not so or not arq or (so, arq) not in DISPONIVEIS:
        raise SemBinario(f"nao ha bridge pronta para {sistema} {maquina}")
    return f"whatsapp-bridge-{so}-{arq}" + (".exe" if so == "windows" else "")


def nome_no_disco(sistema: str) -> str:
    return "main.exe" if sistema.lower() == "windows" else "whatsapp-bridge"


def soma_esperada(texto: str, nome: str) -> str:
    """Le o SHA-256 de `nome` num arquivo no formato do sha256sum ('<hash>  <arquivo>')."""
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) == 2 and partes[1].lstrip("*") == nome:
            soma = partes[0].lower()
            if len(soma) == 64 and all(c in "0123456789abcdef" for c in soma):
                return soma
    raise ErroDeSoma(f"{nome} nao aparece em SHA256SUMS")


def versao_do_plugin(raiz: Path = RAIZ) -> str:
    return json.loads((raiz / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def _baixar(url: str, tempo: int = 120) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=tempo) as r:  # noqa: S310 (https do GitHub ou http local nos testes)
            return r.read()
    except (urllib.error.URLError, OSError) as erro:
        raise ErroDeRede(f"nao consegui baixar {url}: {erro}") from erro


def baixar_bridge(raiz: Path, versao: str, url_base: str, sistema: str, maquina: str, forcar: bool = False) -> Path:
    destino = raiz / "bridge" / nome_no_disco(sistema)
    if destino.exists() and not forcar:
        raise FileExistsError(str(destino))
    arquivo = nome_do_arquivo(sistema, maquina)
    base = f"{url_base.rstrip('/')}/v{versao}"
    somas = _baixar(f"{base}/SHA256SUMS").decode("utf-8", "replace")
    esperada = soma_esperada(somas, arquivo)
    dados = _baixar(f"{base}/{arquivo}")
    if hashlib.sha256(dados).hexdigest() != esperada:
        raise ErroDeSoma(f"o SHA-256 de {arquivo} nao confere com o publicado")
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Grava em um temporario na mesma pasta e troca, para nunca deixar um binario pela metade
    fd, temporario = tempfile.mkstemp(dir=destino.parent, prefix=".bridge-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
        os.chmod(temporario, os.stat(temporario).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(temporario, destino)
    finally:
        if os.path.exists(temporario):
            os.remove(temporario)
    return destino


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--versao", help="versao da release (padrao: a do plugin.json)")
    parser.add_argument("--repo", default=REPO_PADRAO)
    parser.add_argument("--url-base", help="endereco base das releases (padrao: GitHub)")
    parser.add_argument("--forcar", action="store_true", help="substitui a bridge que ja existe")
    args = parser.parse_args(argv)

    versao = (args.versao or versao_do_plugin()).lstrip("v")
    url_base = args.url_base or f"https://github.com/{args.repo}/releases/download"
    try:
        destino = baixar_bridge(RAIZ, versao, url_base, platform.system(), platform.machine(), args.forcar)
    except FileExistsError as e:
        print(f"A bridge ja existe em {e}. Use --forcar para trocar.")
        return 1
    except SemBinario as e:
        print(f"{e}. Compile a bridge (passo 'compilar' da skill): cd bridge && go build .")
        return 2
    except ErroDeSoma as e:
        print(f"ERRO de verificacao: {e}. Nada foi gravado. Nao use este arquivo.")
        return 3
    except ErroDeRede as e:
        print(f"{e}. Confira a rede e se a release v{versao} existe; senao, compile a bridge.")
        return 4
    print(f"Bridge v{versao} baixada e conferida (SHA-256): {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
