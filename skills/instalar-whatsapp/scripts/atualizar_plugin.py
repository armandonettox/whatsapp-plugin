"""Atualiza o plugin de WhatsApp para a ultima release, sem reinstalar nada.

Uso (a partir da pasta do plugin):
    python skills/instalar-whatsapp/scripts/atualizar_plugin.py             # so verifica, nao altera nada
    python skills/instalar-whatsapp/scripts/atualizar_plugin.py --aplicar   # atualiza

O que faz com --aplicar, nesta ordem:
1. confere que a pasta e um clone do git e que voce nao tem alteracoes locais em arquivos do plugin;
2. busca as tags e avanca para a ultima release sem criar commit de mistura (`merge --ff-only`);
3. mostra o que mudou (as secoes do CHANGELOG mais novas que a sua versao);
4. atualiza as dependencias do servidor com o arquivo de travas (`uv sync --frozen`);
5. avisa se a bridge ou os containers mudaram e o que fazer, e troca a bridge pela da release
   so se voce pedir com --bridge e ela estiver fechada.

O que nunca toca: a pasta data/ (sessao do WhatsApp, mensagens, notas), arquivos .env, senhas e
o modo de envio. Depois de atualizar, reinicie o agente para ele carregar o servidor novo.

Codigos de saida: 0 ok (ou ja estava atualizado); 2 a pasta nao e um clone do git; 3 ha
alteracoes locais; 4 nao foi possivel avancar sem misturar historicos; 5 falha de rede.
"""

import argparse
import importlib.util
import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
REPO_PADRAO = "armandonettox/whatsapp-plugin"
PORTA_DA_BRIDGE = 8081


class ErroDeAtualizacao(Exception):
    def __init__(self, mensagem: str, codigo: int):
        super().__init__(mensagem)
        self.codigo = codigo


def como_tupla(versao: str) -> tuple:
    partes = re.findall(r"\d+", versao.split("-")[0])
    return tuple(int(p) for p in partes[:3]) + (0,) * (3 - len(partes[:3]))


def versao_atual(raiz: Path = RAIZ) -> str:
    return json.loads((raiz / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def consultar_release(repo: str, url_api: str, tempo: int = 30) -> dict:
    """Ultima release publicada: {'versao': sem o 'v', 'notas': texto da release}."""
    url = f"{url_api.rstrip('/')}/repos/{repo}/releases/latest"
    try:
        with urllib.request.urlopen(url, timeout=tempo) as r:  # noqa: S310
            dados = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as erro:
        raise ErroDeAtualizacao(f"nao consegui consultar a ultima release ({erro})", 5) from erro
    return {"versao": str(dados["tag_name"]).lstrip("v"), "notas": str(dados.get("body") or "").strip()}


def ultima_versao(repo: str, url_api: str) -> str:
    return consultar_release(repo, url_api)["versao"]


def git(raiz: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise ErroDeAtualizacao(f"git {' '.join(args)} falhou: {(r.stderr or r.stdout).strip()}", 4)
    return r.stdout.strip()


def e_clone_do_git(raiz: Path) -> bool:
    if not (raiz / ".git").exists() or shutil.which("git") is None:
        return False
    return subprocess.run(["git", "-C", str(raiz), "rev-parse", "--git-dir"], capture_output=True).returncode == 0


def alteracoes_locais(raiz: Path) -> list:
    """Arquivos modificados ou novos que o git acompanha. Pastas ignoradas (data/, .venv) nao contam."""
    saida = git(raiz, "status", "--porcelain")
    return [linha for linha in saida.splitlines() if linha.strip()]


def notas_mais_novas(raiz: Path, atual: str, ate: str) -> str:
    """Secoes do CHANGELOG com versao maior que `atual` e ate `ate`."""
    arquivo = raiz / "CHANGELOG.md"
    if not arquivo.is_file():
        return ""
    texto = arquivo.read_text(encoding="utf-8")
    secoes = re.split(r"(?m)^## \[", texto)[1:]
    escolhidas = []
    for secao in secoes:
        m = re.match(r"([\d.]+)\]", secao)
        if m and como_tupla(atual) < como_tupla(m.group(1)) <= como_tupla(ate):
            escolhidas.append("## [" + secao.rstrip())
    return "\n\n".join(escolhidas)


def mudou(raiz: Path, de: str, para: str, pasta: str) -> bool:
    return bool(git(raiz, "diff", "--name-only", de, para, "--", pasta, check=False))


def comandos_de_dependencias(raiz: Path) -> list:
    """Comando do uv para as dependencias do servidor; com o extra de audio se ele ja estava instalado."""
    comando = ["uv", "sync", "--project", str(raiz / "server"), "--frozen"]
    venv = raiz / "server" / ".venv"
    pacotes = [venv / "Lib" / "site-packages"] + sorted(venv.glob("lib/python*/site-packages"))
    if any((p / "whisper").is_dir() for p in pacotes):
        comando += ["--extra", "audio"]
    return comando


def bridge_rodando(aceita=None) -> bool:
    def padrao(host, porta):
        try:
            with socket.create_connection((host, porta), timeout=1):
                return True
        except OSError:
            return False

    return (aceita or padrao)("127.0.0.1", PORTA_DA_BRIDGE)


def carregar_baixar_bridge():
    caminho = Path(__file__).resolve().parent / "baixar_bridge.py"
    spec = importlib.util.spec_from_file_location("baixar_bridge", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def verificar(raiz: Path, repo: str, url_api: str, saida=print) -> tuple:
    atual = versao_atual(raiz)
    release = consultar_release(repo, url_api)
    nova = release["versao"]
    saida(f"Versao instalada: {atual}")
    saida(f"Ultima release:   {nova}")
    if como_tupla(nova) > como_tupla(atual) and release["notas"]:
        saida("\nNotas da release:\n\n" + release["notas"] + "\n")
    return atual, nova


def aplicar(raiz: Path, repo: str, url_api: str, com_bridge: bool, url_base_bridge: str | None,
            rodar=subprocess.run, bridge_aberta=bridge_rodando, saida=print) -> int:
    if not e_clone_do_git(raiz):
        raise ErroDeAtualizacao(
            "esta pasta nao e um clone do git, entao nao da para atualizar por aqui. "
            "No Claude Code instalado pelo catalogo, use /plugin marketplace update e /plugin update. "
            "Em outro caso, baixe a release nova e troque a pasta (mantenha a pasta data/).", 2)
    atual, nova = verificar(raiz, repo, url_api, saida)
    if como_tupla(nova) <= como_tupla(atual):
        saida("Ja esta na ultima versao. Nada a fazer.")
        return 0

    locais = alteracoes_locais(raiz)
    if locais:
        mostra = "\n".join("  " + l for l in locais[:15])
        raise ErroDeAtualizacao(
            "ha alteracoes locais em arquivos do plugin; nada foi mudado.\n" + mostra +
            "\nGuarde ou descarte essas alteracoes (por exemplo, `git stash`) e rode de novo. "
            "Se foram correcoes que a versao nova ja traz, pode descarta-las.", 3)

    antes = git(raiz, "rev-parse", "HEAD")
    saida(f"Buscando a versao {nova}...")
    git(raiz, "fetch", "--tags", "origin")
    try:
        git(raiz, "merge", "--ff-only", f"v{nova}")
    except ErroDeAtualizacao as erro:
        raise ErroDeAtualizacao(
            f"nao consegui avancar para v{nova} sem misturar historicos ({erro}). "
            "Nada foi mudado. O historico do repositorio pode ter sido reescrito: "
            "faca um clone novo e copie a pasta data/ para ele.", 4) from erro
    depois = git(raiz, "rev-parse", "HEAD")
    saida(f"Codigo atualizado para v{nova}.")

    notas = notas_mais_novas(raiz, atual, nova)
    if notas:
        saida("\nO que mudou:\n\n" + notas)

    saida("\nDependencias do servidor...")
    if shutil.which(comandos_de_dependencias(raiz)[0]) is None and rodar is subprocess.run:
        saida("  uv nao encontrado: instale o uv e rode `uv sync --project server --frozen`.")
    else:
        r = rodar(comandos_de_dependencias(raiz), capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            saida("  dependencias em dia.")
        else:
            saida("  AVISO: o uv falhou; rode `uv sync --project server --frozen` e veja o erro.")

    if mudou(raiz, antes, depois, "bridge"):
        if com_bridge:
            if bridge_aberta():
                saida("\nBridge: mudou nesta versao, mas ela esta rodando. Feche-a (pergunte de quem e se nao for a deste plugin) "
                      "e rode de novo com --bridge. Nada foi trocado.")
            else:
                modulo = carregar_baixar_bridge()
                import platform

                base = url_base_bridge or f"https://github.com/{repo}/releases/download"
                try:
                    destino = modulo.baixar_bridge(raiz, nova, base, platform.system(), platform.machine(), forcar=True)
                    saida(f"\nBridge v{nova} baixada e conferida: {destino}")
                except (modulo.SemBinario, modulo.ErroDeSoma, modulo.ErroDeRede) as erro:
                    saida(f"\nBridge: nao troquei ({erro}). Compile a nova: cd bridge && go build .")
        else:
            saida("\nBridge: o codigo dela mudou nesta versao. Feche a bridge e rode de novo com --bridge "
                  "(ou compile: cd bridge && go build .).")
    else:
        saida("\nBridge: sem mudancas nesta versao. Nao precisa trocar nem reiniciar.")

    if mudou(raiz, antes, depois, "container"):
        saida("Containers: os arquivos mudaram. Se voce usa containers, rode `bash container/instalar-vps.sh atualizar` "
              "(servidor) ou reconstrua as imagens com o compose.")

    saida(f"\nPronto: {atual} -> {nova}. Reinicie o agente para carregar o servidor e as skills novos. "
          "Depois rode skills/instalar-whatsapp/scripts/verificar_instalacao.py para conferir.")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--aplicar", action="store_true", help="atualiza (sem isso, so verifica)")
    parser.add_argument("--bridge", action="store_true", help="troca a bridge pela da release, se mudou e estiver fechada")
    parser.add_argument("--repo", default=REPO_PADRAO)
    parser.add_argument("--url-api", default="https://api.github.com")
    parser.add_argument("--url-base-bridge", help="endereco base das releases da bridge (padrao: GitHub)")
    args = parser.parse_args(argv)
    try:
        if args.aplicar:
            return aplicar(RAIZ, args.repo, args.url_api, args.bridge, args.url_base_bridge)
        atual, nova = verificar(RAIZ, args.repo, args.url_api)
        if como_tupla(nova) > como_tupla(atual):
            print("Tem versao nova. Para atualizar: python skills/instalar-whatsapp/scripts/atualizar_plugin.py --aplicar")
        else:
            print("Ja esta na ultima versao.")
        return 0
    except ErroDeAtualizacao as erro:
        print(f"ERRO: {erro}")
        return erro.codigo


if __name__ == "__main__":
    sys.exit(main())
