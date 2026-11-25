"""Sugere como dividir uma resposta em varias mensagens curtas, como uma pessoa escreveria.

Nao muda nenhuma palavra: so decide onde cortar. Cumprimento curto sai sozinho, a pergunta final
sai por ultimo, e links, numeros decimais, horas e abreviacoes nunca sao cortados no meio.

Uso:
    python dividir_mensagem.py "texto da resposta" [--max-chars 160] [--max-partes 5] [--json]
    echo "texto" | python dividir_mensagem.py -
"""

import argparse
import json
import re
import sys

MAX_CHARS_PADRAO = 160
MAX_PARTES_PADRAO = 5

CUMPRIMENTO = re.compile(
    r"^(bom dia|boa tarde|boa noite|oi+|ol[aá]|opa|e a[ií]|fala|salve|hey|hello|hi|hola|buenos d[ií]as)\b[^.!?]{0,30}[.!?,]*$",
    re.IGNORECASE,
)
ABREVIACOES = {"dr", "dra", "sr", "sra", "srta", "prof", "profa", "etc", "ex", "obs", "tel", "av", "apt", "no", "pag", "cel", "ltda"}
PROTEGIDOS = re.compile(
    r"https?://\S+|www\.\S+|\S+@\S+\.\S+|\d+[.,:]\d+|\b(?:" + "|".join(sorted(ABREVIACOES)) + r")\.",
    re.IGNORECASE,
)
# Pontos de corte: depois de virgula ou ponto e virgula (a pontuacao fica na parte da esquerda) e
# antes de conectores. Nenhum caractere do texto e descartado.
CONECTORES = re.compile(r"(?<=[,;])\s+|\s+(?=(?:mas|porque|por[eé]m|ent[aã]o|e|ou|que|pra|para)\s)", re.IGNORECASE)


def _proteger(texto: str):
    """Troca trechos que nao podem ser cortados por marcadores, e devolve como desfazer."""
    guardados = []

    def trocar(m):
        guardados.append(m.group(0))
        return f"\u0000{len(guardados) - 1}\u0000"

    return PROTEGIDOS.sub(trocar, texto), guardados


def _restaurar(texto: str, guardados: list) -> str:
    return re.sub(r"\u0000(\d+)\u0000", lambda m: guardados[int(m.group(1))], texto)


def frases(texto: str) -> list:
    """Divide em frases, respeitando linhas do texto e trechos protegidos."""
    protegido, guardados = _proteger(texto)
    resultado = []
    for linha in re.split(r"\n+", protegido):
        linha = linha.strip()
        if not linha:
            continue
        for pedaco in re.split(r"(?<=[.!?…])\s+", linha):
            if pedaco.strip():
                resultado.append(_restaurar(pedaco.strip(), guardados))
    return resultado


def _cortar_frase_longa(frase: str, limite: int) -> list:
    """Corta uma frase maior que o limite em virgulas e conectores; em ultimo caso, em espacos."""
    if len(frase) <= limite:
        return [frase]
    protegido, guardados = _proteger(frase)
    pedacos = [p for p in CONECTORES.split(protegido) if p and p.strip()]
    partes, atual = [], ""
    for pedaco in pedacos:
        candidato = (atual + " " + pedaco).strip() if atual else pedaco
        if len(_restaurar(candidato, guardados)) <= limite or not atual:
            atual = candidato
        else:
            partes.append(atual)
            atual = pedaco
    if atual:
        partes.append(atual)
    final = []
    for parte in (_restaurar(p, guardados).strip() for p in partes):
        while len(parte) > limite:
            corte = parte.rfind(" ", 0, limite + 1)
            if corte <= 0:
                corte = parte.find(" ")  # palavra ou link maior que o limite: nunca corta no meio
            if corte <= 0:
                break
            final.append(parte[:corte].strip())
            parte = parte[corte:].strip()
        if parte:
            final.append(parte)
    return final


def dividir(texto: str, max_chars: int = MAX_CHARS_PADRAO, max_partes: int = MAX_PARTES_PADRAO):
    """Devolve (partes, avisos). Juntar as partes com espaco reproduz o texto, sem mudar palavras."""
    texto = (texto or "").strip()
    avisos = []
    if not texto:
        return [], ["Texto vazio."]
    unidades = []
    for frase in frases(texto):
        unidades.extend(_cortar_frase_longa(frase, max_chars))

    partes = []
    cumprimento_sozinho = bool(len(unidades) > 1 and CUMPRIMENTO.match(unidades[0]))
    if cumprimento_sozinho:
        partes.append(unidades[0])
        unidades = unidades[1:]

    pergunta_final = None
    if len(unidades) > 1 and unidades[-1].rstrip().endswith("?"):
        pergunta_final = unidades[-1]
        unidades = unidades[:-1]

    atual = ""
    for unidade in unidades:
        candidato = f"{atual} {unidade}".strip() if atual else unidade
        if atual and len(candidato) > max_chars:
            partes.append(atual)
            atual = unidade
        else:
            atual = candidato
    if atual:
        partes.append(atual)
    if pergunta_final:
        partes.append(pergunta_final)

    while len(partes) > max_partes:
        menor = min(range(len(partes) - 1), key=lambda i: len(partes[i]) + len(partes[i + 1]))
        partes[menor:menor + 2] = [f"{partes[menor]} {partes[menor + 1]}"]
        avisos.append("Houve partes unidas para respeitar o limite de partes; algumas passam do limite de caracteres.")
    if any(len(parte) > max_chars for parte in partes):
        avisos.append("Alguma parte passa do limite de caracteres: tem um link ou palavra que nao pode ser cortado, ou foi unida pelo limite de partes.")
    return partes, sorted(set(avisos))


def pausas_sugeridas(partes: list) -> list:
    """Pausa em segundos antes de cada parte, parecida com o tempo de digitar (a primeira sai logo)."""
    return [0.0] + [round(min(5.0, max(1.0, 0.8 + len(p) / 40)), 1) for p in partes[1:]]


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("texto", help='texto a dividir, ou "-" para ler da entrada padrao')
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS_PADRAO)
    parser.add_argument("--max-partes", type=int, default=MAX_PARTES_PADRAO)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    texto = sys.stdin.read() if args.texto == "-" else args.texto
    partes, avisos = dividir(texto, args.max_chars, args.max_partes)
    if args.json:
        print(json.dumps({"partes": partes, "pausas_segundos": pausas_sugeridas(partes), "avisos": avisos}, ensure_ascii=False))
        return 0 if partes else 1
    if not partes:
        print("Texto vazio.")
        return 1
    for numero, parte in enumerate(partes, 1):
        print(f"[{numero}/{len(partes)}] {parte}")
    for aviso in avisos:
        print(f"AVISO: {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
