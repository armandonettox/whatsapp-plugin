"""
whatsapp-send-guard.py
Hook PreToolUse em mcp__whatsapp__send_message|send_file|send_audio_message -
bloqueia o envio se a ultima mensagem do usuario no transcript nao for uma
confirmacao explicita e direta. Ver skills/usar-whatsapp-mcp/references/confirmacao-de-envio.md.
"""

import json
import re
import sys
import unicodedata

SUFIXOS_DE_ENVIO = ("__send_message", "__send_file", "__send_audio_message")


def eh_ferramenta_de_envio(nome: str) -> bool:
    """True para as ferramentas de envio do MCP de WhatsApp.

    O nome muda conforme a instalacao: mcp__whatsapp__send_message (MCP avulso) ou
    mcp__plugin_<plugin>_whatsapp__send_message (MCP vindo de um plugin). Por isso olha o
    comeco e o fim do nome, nao o nome inteiro.
    """
    return nome.startswith("mcp__") and "whatsapp" in nome and nome.endswith(SUFIXOS_DE_ENVIO)

# Confirmacao e uma frase curta feita SO de palavras de confirmacao ou de enchimento, com pelo
# menos uma palavra de confirmacao e nenhuma palavra de edicao, duvida ou recusa. Palavra
# desconhecida bloqueia (falha fechada): a IA entao mostra o texto de novo e pergunta outra vez,
# o que e melhor do que enviar uma mensagem a um contato por uma confirmacao mal entendida.
# Vale em portugues, ingles e espanhol, porque o plugin roda em qualquer agente.
MAX_PALAVRAS = 8

CONFIRMADORES = {
    # portugues
    "sim", "ok", "okay", "okey", "oki", "manda", "mandar", "mande", "envia", "enviar", "envie",
    "pode", "vai", "bora", "partiu", "vamos", "confirma", "confirmar", "confirmado", "confirmo",
    "fechado", "fechou", "beleza", "blz", "bele", "certo", "certeza", "perfeito", "positivo",
    "afirmativo", "uhum", "aham", "segue", "seguir", "claro", "combinado", "libera", "liberado",
    "autorizo", "autorizado", "aprovo", "aprovado", "dispara", "disparar", "solta", "isso", "ver",
    "show", "top", "joia", "massa", "tranquilo", "otimo", "excelente", "exato", "exatamente",
    "correto", "concordo", "bacana",
    # ingles
    "yes", "yeah", "yep", "yup", "yea", "sure", "confirm", "confirmed", "approve", "approved",
    "send", "go", "proceed", "absolutely", "definitely", "certainly", "correct", "agreed",
    "affirmative", "lgtm", "fine", "good", "great", "perfect", "cool", "nice", "alright", "right",
    # espanhol
    "si", "sip", "dale", "vale", "listo", "adelante", "envialo", "enviala", "mandalo", "mandala",
    "aprobado", "correcto", "perfecto", "genial",
    # frase fixa reconhecida (ver FRASES)
    "<frase>",
}
ENCHIMENTO = {
    # portugues
    "assim", "ai", "logo", "ja", "mesmo", "essa", "essas", "esse", "esses", "tudo", "ta", "esta",
    "bom", "bem", "e", "entao", "por", "favor", "pf", "pfv", "mais", "uma", "um", "vez", "agora",
    "doutor", "doutora", "dr", "amigo", "parceiro", "a", "o", "as", "os", "la", "ali", "nessa",
    "nesse", "de", "do", "da", "mensagem", "mensagens", "texto", "resposta", "tambem", "obrigado",
    "obrigada", "valeu", "vlw", "brigado", "gracas",
    # ingles
    "it", "now", "ahead", "the", "message", "text", "reply", "thanks", "thank", "you", "then",
    "away", "please", "and", "looks", "that", "this", "is", "its", "all", "sounds", "me", "to",
    # espanhol
    "ya", "ahora", "todo", "el", "la", "lo", "mensaje", "gracias", "entonces", "ahi", "asi",
}
RECUSA_OU_EDICAO = {
    # portugues
    "nao", "nunca", "mas", "espera", "espere", "calma", "pera", "antes", "depois", "muda", "mude",
    "mudar", "troca", "troque", "trocar", "tira", "tire", "tirar", "adiciona", "adicione",
    "coloca", "coloque", "ainda", "cancela", "cancelar", "cancele", "para", "pare", "talvez", "so",
    "apenas", "se", "porem", "sem", "negativo", "jamais", "nem", "altera", "altere", "alterar",
    "corrige", "corrija", "corrigir", "edita", "edite", "editar", "reescreve", "reescreva",
    "refaz", "refaca", "refazer", "remove", "remova", "apaga", "apague", "exclui", "exclua",
    "segura", "segure", "aguarda", "aguarde", "aguardar", "pausa", "pause", "pausar", "outra",
    "outro", "diferente",
    # ingles
    "no", "not", "dont", "wont", "cant", "wait", "stop", "hold", "cancel", "change", "edit", "fix",
    "but", "however", "only", "if", "unless", "later", "never", "nope", "nah", "maybe", "perhaps",
    "before", "after", "except", "wrong", "remove", "delete", "skip", "different", "another",
    # espanhol
    "pero", "solo", "sin", "despues", "todavia", "aun", "cambia", "cambiar", "quita", "quitar",
    "borra", "borrar", "quizas", "esperate",
}
# Frases fixas (sem acento, so letras): valem como confirmacao mesmo quando uma das palavras
# sozinha bloquearia (como "sem" em "sem problema"). Podem vir junto de palavras de confirmacao.
FRASES = {
    # portugues
    "com certeza", "sem problema", "sem problemas", "sem duvida", "sem duvidas", "pode crer",
    "manda bala", "manda ver", "pode ir", "de acordo", "estou de acordo", "esta bom", "ta bom",
    "tudo certo", "tudo bem", "isso mesmo", "isso ai", "exatamente isso", "claro que sim",
    "claro que pode", "pode sim", "quero sim", "pode soltar", "pode disparar", "vai la", "ta ok",
    "ta certo", "esta certo", "ta joia", "ta otimo", "ta perfeito", "bora la", "vamos nessa",
    "vamos la", "faz isso", "faca isso", "pode fazer", "pode fazer isso", "pode enviar isso",
    "pode mandar isso", "isso e tudo", "manda sem medo", "envia sem medo",
    # ingles
    "do it", "go for it", "go ahead", "send it", "send it now", "sounds good", "looks good",
    "looks good to me", "all good", "that is right", "thats right", "thats correct", "of course",
    "for sure", "by all means", "why not", "fire away", "ship it", "yes please", "please do",
    "please send", "please send it", "go ahead and send it", "no problem at all",
    # espanhol
    "de acuerdo", "por supuesto", "claro que si", "hazlo", "sin problema", "sin problemas",
    "todo bien", "esta bien", "esta perfecto", "envialo ya", "mandalo ya",
}
# Emojis que confirmam, dados por codigo para o arquivo nao ter emoji: polegar para cima, ok com a
# mao, marca verde, marca, caixa marcada, botao ok, maos para cima, braco forte, aperto de mao e
# foguete. Qualquer outro simbolo (inclusive os de recusa, como o polegar para baixo) bloqueia.
EMOJIS_QUE_CONFIRMAM = {
    chr(c) for c in (0x1F44D, 0x1F44C, 0x2705, 0x2714, 0x2611, 0x1F197, 0x1F64C, 0x1F4AA, 0x1F91D, 0x1F680)
}
# Modificadores que nao mudam o sentido: seletor de variacao, juntador e tons de pele
MODIFICADORES = {chr(0xFE0F), chr(0x200D)} | {chr(c) for c in range(0x1F3FB, 0x1F400)}
# Ponto de interrogacao comum, de largura total e o invertido do espanhol
INTERROGACOES = ("?", chr(0xFF1F), chr(0xBF))
APOSTROFO_CURVO = chr(0x2019)


def separar_emojis(texto: str):
    """Tira os emojis que confirmam. Devolve (texto, quantos confirmam, achou simbolo que bloqueia)."""
    resto = []
    confirmam = 0
    for caractere in texto:
        if caractere in MODIFICADORES:
            continue
        if caractere in EMOJIS_QUE_CONFIRMAM:
            confirmam += 1
            continue
        if unicodedata.category(caractere) == "So":
            return texto, 0, True
        resto.append(caractere)
    return "".join(resto), confirmam, False


def normalizar(texto: str) -> str:
    """Minusculas, sem acento, sem apostrofo, so letras separadas por um espaco."""
    texto = texto.lower().replace("'", "").replace(APOSTROFO_CURVO, "")
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z]+", " ", sem_acento)).strip()


def eh_confirmacao(texto: str) -> bool:
    """True se a mensagem inteira do usuario e uma confirmacao curta e direta."""
    if any(sinal in texto for sinal in INTERROGACOES):
        return False
    texto, emojis, bloqueia = separar_emojis(texto)
    if bloqueia:
        return False
    normal = normalizar(texto)
    if not normal:
        return emojis > 0
    # frase fixa vira uma unica palavra de confirmacao; "<frase>" nao sai da normalizacao,
    # entao ninguem consegue digita-la
    for frase in sorted(FRASES, key=len, reverse=True):
        normal = re.sub(r"(?<![a-z])" + re.escape(frase) + r"(?![a-z])", " <frase> ", normal)
    palavras = normal.split()
    if not palavras or len(palavras) > MAX_PALAVRAS:
        return False
    if any(p in RECUSA_OU_EDICAO for p in palavras):
        return False
    if not all(p in CONFIRMADORES or p in ENCHIMENTO for p in palavras):
        return False
    return any(p in CONFIRMADORES for p in palavras)


PONTUACAO_FINAL = re.compile(r"[.!?\s]+$")


def ultima_mensagem_do_usuario(transcript_path: str) -> str | None:
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except Exception:
        return None

    for linha in reversed(linhas):
        linha = linha.strip()
        if not linha:
            continue
        try:
            entrada = json.loads(linha)
        except Exception:
            continue

        if entrada.get("type") != "user":
            continue

        mensagem = entrada.get("message", {})
        conteudo = mensagem.get("content")

        if isinstance(conteudo, str):
            texto = conteudo.strip()
            if texto:
                return texto
            continue

        if isinstance(conteudo, list):
            # se tiver tool_result, essa entrada e resultado de ferramenta, nao
            # fala real do usuario -- continua procurando pra tras
            if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in conteudo):
                continue
            partes = [
                b.get("text", "") for b in conteudo
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            texto = " ".join(p for p in partes if p).strip()
            if texto:
                return texto

    return None


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if not eh_ferramenta_de_envio(dados.get("tool_name", "")):
        sys.exit(0)

    transcript_path = dados.get("transcript_path")
    if not transcript_path:
        # sem transcript pra verificar -- falha FECHADO (bloqueia), nunca aberto.
        # um guardrail de seguranca que libera quando nao consegue checar nao protege nada.
        print("BLOQUEADO -- WhatsApp Send Guard: sem transcript_path pra verificar confirmacao.", file=sys.stderr)
        sys.exit(2)

    ultima = ultima_mensagem_do_usuario(transcript_path)

    if ultima is None:
        texto_normalizado = ""
    else:
        texto_normalizado = PONTUACAO_FINAL.sub("", ultima.strip())

    # O "?" no fim some quando a pontuacao final e removida, entao a pergunta e checada antes:
    # "pode mandar agora?" e uma duvida, nao uma confirmacao
    eh_pergunta = "?" in (ultima or "")

    if not texto_normalizado or eh_pergunta or not eh_confirmacao(texto_normalizado):
        print("BLOQUEADO -- WhatsApp Send Guard:", file=sys.stderr)
        print(f"  Ultima mensagem do usuario: \"{ultima or '(nenhuma)'}\"", file=sys.stderr)
        print("  Isso nao parece uma confirmacao explicita e direta (sim, manda, pode, pode seguir, envia, confirma...).", file=sys.stderr)
        print("  Mostre o texto EXATO que vai ser enviado e o destinatario, e peca confirmacao", file=sys.stderr)
        print("  explicita antes de chamar essa ferramenta de novo.", file=sys.stderr)
        print("  Ver skills/usar-whatsapp-mcp/references/confirmacao-de-envio.md", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
