"""Verificador de privacidade: procura dados pessoais e segredos nos arquivos do repositorio.

Uso:
    python scripts/check-privacy.py              confere todos os arquivos do repositorio
    python scripts/check-privacy.py --staged     confere so o que esta na area de staging do git
    python scripts/check-privacy.py caminho ...  confere arquivos ou pastas especificos

Sai com codigo 1 se achar algo. Mostra so trechos mascarados, porque a saida pode ir para logs.

Excecao justificada: coloque o valor exato, um por linha, no arquivo .privacy-allow da raiz, ou
escreva "privacy:ignore" no fim da linha.
"""

import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

PASTAS_IGNORADAS = {".git", ".venv", "node_modules", "__pycache__", "data"}
ARQUIVOS_IGNORADOS = {"uv.lock", "go.sum", "package-lock.json", "poetry.lock"}
EXTENSOES_BINARIAS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".exe", ".db", ".zip", ".pdf"}

# Valores ficticios usados nos exemplos do proprio projeto
VALORES_FICTICIOS = {
    "5511999999999",
    "5511999999999@s.whatsapp.net",
    "120363000000000000@g.us",
}
USUARIOS_GENERICOS = {"usuario", "user", "seu-usuario", "seu_usuario", "nome", "name", "voce", "you", "<usuario>"}
DOMINIOS_DE_EXEMPLO = ("example.com", "example.org", "example.net", "users.noreply.github.com", "noreply.github.com")
# Os IDs do WhatsApp tem formato de e-mail; quem trata deles e a regra de id_whatsapp
DOMINIOS_DO_WHATSAPP = ("s.whatsapp.net", "g.us")
# Numeros que so podem ser de exemplo: sequencia 12345678 ou o mesmo digito repetido
NUMERO_DE_EXEMPLO = re.compile(r"12345678|99999999|00000000|11111111|88888888")

IPV4 = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d]|\.\d)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
TELEFONE_BR = re.compile(r"(?<!\d)(?:\+?55\s?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}|55\d{10,11})(?!\d)")
JID_WHATSAPP = re.compile(r"\d{8,}(?::\d+)?@(?:s\.whatsapp\.net|lid|g\.us)")
CPF = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
CNPJ = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")
# Padroes que DETECTAM chaves e tokens; nao ha chave de verdade aqui
TOKEN = re.compile(  # allow_seguranca
    r"gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}"  # allow_seguranca
    r"|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}"  # allow_seguranca
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"  # allow_seguranca
)
CAMINHO_WINDOWS = re.compile(r"[A-Za-z]:\\Users\\([A-Za-z0-9._-]+)\\")
CAMINHO_UNIX = re.compile(r"(?:/Users|/home)/([A-Za-z0-9._-]+)/")


def ip_e_reservado(texto: str) -> bool:
    """True para IP que nao identifica ninguem: local, privado, de exemplo ou invalido."""
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return True  # nao e um IP (por exemplo, um numero de versao com valores acima de 255)
    return not ip.is_global


def mascarar(valor: str, regra: str) -> str:
    if regra == "ip_publico":
        partes = valor.split(".")
        return f"{partes[0]}.{partes[1]}.x.x"
    if regra == "email":
        usuario, _, dominio = valor.partition("@")
        return f"{usuario[:1]}***@{dominio}"
    return valor[:4] + "***"


def procurar_na_linha(linha: str):
    """Devolve (regra, valor) para cada dado sensivel achado na linha."""
    for m in IPV4.finditer(linha):
        if not ip_e_reservado(m.group(1)):
            yield "ip_publico", m.group(1)
    for m in EMAIL.finditer(linha):
        if not m.group(0).lower().endswith(DOMINIOS_DE_EXEMPLO + DOMINIOS_DO_WHATSAPP):
            yield "email", m.group(0)
    for m in TELEFONE_BR.finditer(linha):
        if not NUMERO_DE_EXEMPLO.search(re.sub(r"\D", "", m.group(0))):
            yield "telefone", m.group(0)
    for m in JID_WHATSAPP.finditer(linha):
        if not NUMERO_DE_EXEMPLO.search(re.sub(r"\D", "", m.group(0))):
            yield "id_whatsapp", m.group(0)
    for m in CPF.finditer(linha):
        yield "cpf", m.group(0)
    for m in CNPJ.finditer(linha):
        yield "cnpj", m.group(0)
    for m in TOKEN.finditer(linha):
        yield "token_ou_chave", m.group(0)
    for m in CAMINHO_WINDOWS.finditer(linha):
        if m.group(1).lower() not in USUARIOS_GENERICOS:
            yield "caminho_com_usuario", m.group(0)
    for m in CAMINHO_UNIX.finditer(linha):
        if m.group(1).lower() not in USUARIOS_GENERICOS:
            yield "caminho_com_usuario", m.group(0)


def ler_permitidos(raiz: Path) -> set:
    arquivo = raiz / ".privacy-allow"
    if not arquivo.exists():
        return set()
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    return {l.strip() for l in linhas if l.strip() and not l.lstrip().startswith("#")}


def conferir_arquivo(caminho: Path, permitidos: set):
    """Devolve a lista de (linha, regra, valor) de um arquivo de texto."""
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    achados = []
    for numero, linha in enumerate(texto.splitlines(), 1):
        if "privacy:ignore" in linha:
            continue
        for regra, valor in procurar_na_linha(linha):
            if valor in permitidos or valor in VALORES_FICTICIOS:
                continue
            achados.append((numero, regra, valor))
    return achados


def listar_arquivos(raiz: Path, caminhos, so_staged: bool):
    if so_staged:
        saida = subprocess.run(
            ["git", "-C", str(raiz), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, encoding="utf-8",
        ).stdout
        return [raiz / linha for linha in saida.splitlines() if linha]
    pontos = [Path(c) for c in caminhos] or [raiz]
    arquivos = []
    for ponto in pontos:
        if ponto.is_file():
            arquivos.append(ponto)
            continue
        for pasta, subpastas, nomes in os.walk(ponto):
            subpastas[:] = [d for d in subpastas if d not in PASTAS_IGNORADAS]
            arquivos.extend(Path(pasta) / n for n in nomes)
    return arquivos


def executar(raiz: Path, caminhos=(), so_staged: bool = False) -> list:
    """Devolve a lista de (arquivo, linha, regra, valor mascarado)."""
    permitidos = ler_permitidos(raiz)
    resultado = []
    for arquivo in listar_arquivos(raiz, caminhos, so_staged):
        if arquivo.name in ARQUIVOS_IGNORADOS or arquivo.suffix.lower() in EXTENSOES_BINARIAS:
            continue
        if not arquivo.is_file():
            continue
        for linha, regra, valor in conferir_arquivo(arquivo, permitidos):
            try:
                nome = str(arquivo.relative_to(raiz))
            except ValueError:
                nome = str(arquivo)
            resultado.append((nome, linha, regra, mascarar(valor, regra)))
    return resultado


def main(argv) -> int:
    so_staged = "--staged" in argv
    caminhos = [a for a in argv if not a.startswith("--")]
    achados = executar(RAIZ, caminhos, so_staged)
    if not achados:
        print("Verificador de privacidade: nada encontrado.")
        return 0
    print("Verificador de privacidade: dados que nao devem ir para o repositorio:")
    for arquivo, linha, regra, valor in achados:
        print(f"  {arquivo}:{linha}  [{regra}]  {valor}")
    print("Remova o dado. Se for um exemplo ficticio, ponha o valor em .privacy-allow ou 'privacy:ignore' na linha.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
