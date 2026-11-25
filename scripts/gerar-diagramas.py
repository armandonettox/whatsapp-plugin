"""Gera as imagens em ingles a partir das em portugues e os fluxos novos (pt e en).

As imagens em portugues arquitetura.svg, fluxo-envio.svg e fluxo-envio-animado.svg sao a fonte:
as versoes em ingles (architecture.svg, send-flow.svg, send-flow-animated.svg) sao traduzidas
dela por mapeamento exato de texto. Os fluxos novos (modos de envio, isolamento com containers e
instalacao por agente) saem direto deste script, nos dois idiomas, com a paleta do projeto.

Uso: python scripts/gerar-diagramas.py docs
Depois de mudar um texto, rode de novo: o teste confere que as imagens do repositorio sao
exatamente as que este script gera.
"""

import html
import re
import sys
from pathlib import Path

DOCS = Path(sys.argv[1])
BASE = (DOCS / "fluxo-envio.svg").read_text(encoding="utf-8")
STYLE = re.search(r"<style>(.*?)</style>", BASE, re.S).group(1)
DEFS = re.search(r"<defs>(.*?)</defs>", BASE, re.S).group(1)
EXTRA_STYLE = (
    ".band{fill:var(--comp);fill-opacity:.07;stroke:var(--comp);stroke-width:1.5;stroke-dasharray:7 5}"
    ".lna{stroke:var(--guard);stroke-width:2.2;fill:none;marker-end:url(#aa)}"
    ".lnx{stroke:var(--blockt);stroke-width:2.2;fill:none;stroke-dasharray:7 5;marker-end:url(#ab)}"
    ".lnd{stroke:var(--dim);stroke-width:1.7;fill:none;stroke-dasharray:6 4}"
    ".tg{font-size:11.5px;font-weight:600;fill:var(--guard)}.tb{font-size:12.5px;font-weight:600;fill:var(--blockt)}"
    ".tf{font-size:12.5px;font-weight:600;fill:var(--flowt)}"
)
EXTRA_DEFS = (
    '<marker id="aa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
    '<path d="M0,0 L10,5 L0,10 z" style="fill:var(--guard)"/></marker>'
)


def esc(t):
    return html.escape(t, quote=False)


def svg(w, h, lang, title, desc, body):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d" lang="{lang}">\n'
        f'  <title id="t">{esc(title)}</title>\n  <desc id="d">{esc(desc)}</desc>\n'
        f"  <style>{STYLE}{EXTRA_STYLE}</style>\n  <defs>{DEFS}{EXTRA_DEFS}</defs>\n"
        f'  <rect width="{w}" height="{h}" style="fill:var(--bg)"/>\n{body}</svg>\n'
    )


def tx(x, y, texto, cls="t2", anchor="middle", extra=""):
    return f'  <text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{extra}>{esc(texto)}</text>\n'


def box(x, y, w, h, t1, t2="", t3="", cls="box", rx=14):
    cx = x + w / 2
    out = f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>\n'
    linhas = [(t1, "t1")] + ([(t2, "t2")] if t2 else []) + ([(t3, "t3")] if t3 else [])
    topo = y + (h - 20 * len(linhas)) / 2 + 15
    for i, (texto, c) in enumerate(linhas):
        out += tx(cx, topo + i * 20, texto, c)
    return out


def cabecalho(titulo, sub):
    return tx(30, 40, titulo, "h", "start") + tx(30, 62, sub, "s", "start")


EN_ARQUITETURA = {
    "Arquitetura do WhatsApp para agentes de IA": "Architecture of WhatsApp for AI agents",
    "Como funciona": "How it works",
    "Mensagens e bancos ficam no seu computador; o que o agente l\u00ea \u00e9 enviado ao modelo que voc\u00ea usa.":
        "Messages and databases stay on your computer; what the agent reads is sent to the model you use.",
    "Guarda": "Guard", "Seu agente": "Your agent", "qualquer um com MCP": "any agent with MCP",
    "Servidor MCP": "MCP server", "13 ferramentas \u00b7 modo de envio": "13 tools \u00b7 send mode",
    "envio e download": "send and download", "multidispositivo": "multi-device", "seu n\u00famero": "your number",
    "SQLite, s\u00f3 no seu computador": "SQLite, only on your computer", "l\u00ea direto": "reads directly",
    "(somente leitura)": "(read-only)", "grava as mensagens": "stores the messages",
    "que chegam e saem": "coming in and going out", "triagem, notas, escrita e partes": "triage, notes, writing and parts",
    "ajudam a responder no seu tom": "help reply in your voice", "carregada pelo agente": "loaded by the agent",
    "l\u00ea o hist\u00f3rico (somente leitura)": "reads the history (read-only)", "Hook de in\u00edcio": "Start hook",
    "liga a bridge sozinho": "starts the bridge by itself", "s\u00f3 no Claude Code": "Claude Code only",
    "inicia": "starts", "fluxo de mensagens": "message flow", "leitura ou inicializa\u00e7\u00e3o": "read or start",
    "guarda de seguran\u00e7a": "safety guard", "componentes": "components",
    "O agente chama o servidor MCP. No Claude Code, um guarda confere cada envio; em qualquer agente, o modo de envio do servidor decide se as ferramentas de envio existem. O servidor le os bancos locais direto e envia pela bridge, que fala com o WhatsApp e grava as mensagens nos bancos. As skills leem os bancos em modo somente leitura e, no Claude Code, um hook liga a bridge no inicio da sessao.":
        "The agent calls the MCP server. In Claude Code, a guard checks every send; in any agent, the server's send mode decides whether send tools exist. The server reads the local databases directly and sends through the bridge, which talks to WhatsApp and stores the messages in the databases. Skills read the databases read-only and, in Claude Code, a hook starts the bridge when the session begins.",
}
EN_FLUXO = {
    "Fluxo do envio com o guarda": "Send flow with the guard",
    "Fluxo do envio com o guarda (animado)": "Send flow with the guard (animated)",
    "O que acontece quando o agente tenta enviar": "What happens when the agent tries to send",
    "Nada sai sem uma confirma\u00e7\u00e3o expl\u00edcita sua. Se houver d\u00favida, o guarda bloqueia.":
        "Nothing is sent without your explicit confirmation. When in doubt, the guard blocks.",
    "Agente pede": "Agent asks", "Guarda de envio": "Send guard", "l\u00ea a \u00faltima mensagem": "reads the last message",
    "que voc\u00ea escreveu": "you wrote", "\u00e9 uma": "is it a", "confirma\u00e7\u00e3o": "direct", "direta?": "confirmation?",
    "sim": "yes", "Servidor MCP": "MCP server", "envia pelo WhatsApp": "sends via WhatsApp", "Enviada": "Sent",
    "depois de voc\u00ea": "after you", "confirmar": "confirm", "n\u00e3o, edi\u00e7\u00e3o ou d\u00favida": "no, edit or doubt",
    "BLOQUEADO": "BLOCKED", "mostra o texto exato e o destinat\u00e1rio": "shows the exact text and recipient",
    "e pede a confirma\u00e7\u00e3o de novo": "and asks for confirmation again", "Confirmam:": "Confirm:",
    " sim, manda, pode, confirma, envia, beleza": " yes, send it, go ahead, confirm, sounds good",
    "Bloqueiam:": "Block:", ' n\u00e3o, mas, troca, espera, "sim, mas troca o oi",': ' no, but, change, wait, "yes, but change the hi",',
    "qualquer pergunta e frases longas": "any question and long sentences", "Falha fechada:": "Fails closed:",
    " se n\u00e3o der para verificar, bloqueia.": " if it cannot check, it blocks.",
    "sem confirma\u00e7\u00e3o: barrado no guarda": "no confirmation: stopped at the guard",
    "com confirma\u00e7\u00e3o: chega ao WhatsApp": "with confirmation: reaches WhatsApp",
    "O agente pede para enviar. O guarda le a ultima mensagem do usuario. Se for uma confirmacao direta, o servidor envia pela bridge para o WhatsApp. Se for edicao, duvida ou recusa, o envio e bloqueado e o agente pede confirmacao de novo.":
        "The agent asks to send. The guard reads the user's last message. If it is a direct confirmation, the server sends through the bridge to WhatsApp. If it is an edit, a doubt or a refusal, the send is blocked and the agent asks for confirmation again.",
}


def traduzir(origem, destino, mapa):
    t = (DOCS / origem).read_text(encoding="utf-8")

    def trocar(m):
        texto = m.group(2)
        return m.group(1) + esc(mapa[texto]) + m.group(3) if texto in mapa else m.group(0)

    novo = re.sub(r"(<(?:text|tspan|title|desc)\b[^>]*>)([^<]+)(</(?:text|tspan|title|desc)>)", trocar, t)
    # texto solto depois de um </tspan>, ainda dentro do <text>
    novo = re.sub(r"(</tspan>)([^<]+)(</text>)", trocar, novo)
    faltando = []
    corpo = novo.split("</defs>", 1)[1]
    for texto in re.findall(r">([^<>]*[^<>\s][^<>]*)<", corpo):
        if re.search(r"[\u00e1\u00e9\u00ed\u00f3\u00fa\u00e2\u00ea\u00f4\u00e3\u00f5\u00e7\u00c1\u00c9\u00cd\u00d3\u00da\u00c7]|\b(voc\u00ea|sim|n\u00e3o|envio|agente pede)\b", texto):
            faltando.append(texto)
    novo = novo.replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg xmlns="http://www.w3.org/2000/svg" lang="en"', 1)
    (DOCS / destino).write_text(novo, encoding="utf-8", newline="")
    return faltando


TXT_MODOS = {
    "en": dict(
        titulo="Send modes", sub="WHATSAPP_SEND_MODE decides what the agent can do. Without it, the safe default applies.",
        agente="Agent", agente2="any agent with MCP", servidor="MCP server", servidor2="WHATSAPP_SEND_MODE",
        ve="Agent sees", envia="Who sends", usar="Use for",
        modos=[
            ("read-only", "default", "no send tools", "nobody", "any agent, no setup"),
            ("two-step", "send with your OK", "send tools save a draft", "you, in your terminal", "agents without the guard"),
            ("hook", "Claude Code only", "send tools send directly", "the agent, after the guard", "Claude Code"),
        ],
        rodape="Unknown, misspelled or empty value falls back to read-only.",
        desc="The agent talks to the MCP server. The send mode decides what happens next. In read-only, the default, send tools do not exist. In two-step, send tools only save a draft and the person confirms in their own terminal. In hook, send tools send directly and only the Claude Code guard confirms each send.",
        arquivo="send-modes.svg", lang="en",
    ),
    "pt": dict(
        titulo="Modos de envio", sub="WHATSAPP_SEND_MODE decide o que o agente pode fazer. Sem ela, vale o padr\u00e3o seguro.",
        agente="Agente", agente2="qualquer um com MCP", servidor="Servidor MCP", servidor2="WHATSAPP_SEND_MODE",
        ve="O agente v\u00ea", envia="Quem envia", usar="Use para",
        modos=[
            ("read-only", "padr\u00e3o", "nenhuma ferramenta de envio", "ningu\u00e9m", "qualquer agente, sem configurar"),
            ("two-step", "envia com o seu OK", "envio s\u00f3 guarda um rascunho", "voc\u00ea, no seu terminal", "agentes sem o guarda"),
            ("hook", "s\u00f3 no Claude Code", "envio vai direto", "o agente, depois do guarda", "Claude Code"),
        ],
        rodape="Valor desconhecido, com erro de digita\u00e7\u00e3o ou vazio cai em read-only.",
        desc="O agente fala com o servidor MCP. O modo de envio decide o que acontece depois. Em read-only, o padr\u00e3o, as ferramentas de envio n\u00e3o existem. Em two-step, as ferramentas de envio s\u00f3 guardam um rascunho e a pessoa confirma no pr\u00f3prio terminal. Em hook, as ferramentas enviam direto e s\u00f3 o guarda do Claude Code confirma cada envio.",
        arquivo="modos-de-envio.svg", lang="pt-BR",
    ),
}


def modos(lang):
    t = TXT_MODOS[lang]
    b = cabecalho(t["titulo"], t["sub"])
    b += box(420, 90, 200, 60, t["agente"], t["agente2"])
    b += '  <line x1="520" y1="150" x2="520" y2="188" class="lnn"/>\n'
    b += box(380, 190, 280, 70, t["servidor"], t["servidor2"])
    estilos = [("boxf", "ln"), ("box", "lnn"), ("boxg", "lna")]
    xs = [30, 360, 690]
    caminhos = ["M520,260 V290 H190 V318", "M520,260 V318", "M520,260 V290 H850 V318"]
    for (nome, tag, ve, quem, uso), (cls, ln), x, caminho in zip(t["modos"], estilos, xs, caminhos):
        b += f'  <path d="{caminho}" class="{ln}"/>\n'
        b += f'  <rect x="{x}" y="320" width="320" height="160" rx="14" class="{cls}"/>\n'
        b += tx(x + 18, 350, nome, "t1", "start")
        b += tx(x + 18, 370, tag, {"boxf": "tf", "box": "t3", "boxg": "tg"}[cls], "start")
        for i, (rot, val) in enumerate([(t["ve"], ve), (t["envia"], quem), (t["usar"], uso)]):
            y = 405 + i * 26
            b += tx(x + 18, y, rot, "t3", "start")
            b += tx(x + 112, y, val, "t2", "start", ' style="fill:var(--text)"')
    b += tx(520, 508, t["rodape"], "t3")
    return svg(1040, 524, t["lang"], t["titulo"], t["desc"], b), t["arquivo"]


TXT_ISOLAMENTO = {
    "en": dict(
        titulo="Isolation with containers", sub="The agent only reaches the MCP server. It never sees the bridge, the password or the session.",
        rede1="network: whatsapp-agente", rede2="network: whatsapp-back",
        agente="Agent container", agente2="e.g. OpenBot, with a terminal",
        servidor="MCP server", servidor2="send mode: read-only or two-step",
        bridge="Bridge", bridge2="API protected by a password",
        volume="volume whatsapp-data", volume2="session and databases",
        bloqueio="no route: the agent cannot reach the bridge",
        senha="password", nota="The password lives only in the bridge and MCP server containers.",
        net="outbound internet", leg_ok="allowed path", leg_no="blocked path", leg_vol="data access",
        desc="The agent container and the MCP server share the network whatsapp-agente. The MCP server and the bridge share the network whatsapp-back. The agent has no route to the bridge. The bridge API needs a password that only the bridge and the MCP server know. The volume with the WhatsApp session and databases is mounted only by the bridge and the MCP server.",
        arquivo="container-isolation.svg", lang="en",
    ),
    "pt": dict(
        titulo="Isolamento com containers", sub="O agente s\u00f3 alcan\u00e7a o servidor MCP. Ele nunca v\u00ea a bridge, a senha nem a sess\u00e3o.",
        rede1="rede: whatsapp-agente", rede2="rede: whatsapp-back",
        agente="Container do agente", agente2="ex.: OpenBot, com terminal",
        servidor="Servidor MCP", servidor2="modo: read-only ou two-step",
        bridge="Bridge", bridge2="API protegida por senha",
        volume="volume whatsapp-data", volume2="sess\u00e3o e bancos",
        bloqueio="sem rota: o agente n\u00e3o alcan\u00e7a a bridge",
        senha="senha", nota="A senha existe s\u00f3 nos containers da bridge e do servidor MCP.",
        net="sa\u00edda para a internet", leg_ok="caminho permitido", leg_no="caminho bloqueado", leg_vol="acesso aos dados",
        desc="O container do agente e o servidor MCP compartilham a rede whatsapp-agente. O servidor MCP e a bridge compartilham a rede whatsapp-back. O agente n\u00e3o tem rota at\u00e9 a bridge. A API da bridge exige uma senha que s\u00f3 a bridge e o servidor MCP conhecem. O volume com a sess\u00e3o do WhatsApp e os bancos s\u00f3 \u00e9 montado pela bridge e pelo servidor MCP.",
        arquivo="isolamento-containers.svg", lang="pt-BR",
    ),
}


def isolamento(lang):
    t = TXT_ISOLAMENTO[lang]
    b = cabecalho(t["titulo"], t["sub"])
    b += '  <rect x="20" y="120" width="640" height="190" rx="18" class="band"/>\n'
    b += '  <rect x="380" y="120" width="640" height="190" rx="18" class="band"/>\n'
    b += tx(36, 142, t["rede1"], "t3", "start")
    b += tx(1004, 142, t["rede2"], "t3", "end")
    b += box(50, 170, 220, 90, t["agente"], t["agente2"])
    b += box(430, 170, 220, 90, t["servidor"], t["servidor2"])
    b += box(790, 170, 200, 90, t["bridge"], t["bridge2"])
    b += '  <line x1="270" y1="215" x2="428" y2="215" class="ln"/>\n'
    b += '  <line x1="650" y1="215" x2="788" y2="215" class="ln"/>\n'
    b += tx(719, 205, t["senha"], "tf")
    b += '  <path d="M160,168 C160,70 890,70 890,168" class="lnx"/>\n'
    b += tx(525, 86, t["bloqueio"], "tb")
    b += box(430, 350, 220, 70, t["volume"], t["volume2"], cls="boxg")
    b += '  <line x1="540" y1="260" x2="540" y2="348" class="lnd"/>\n'
    b += '  <path d="M890,260 V385 H652" class="lnd"/>\n'
    b += tx(905, 285, t["net"], "t3", "start")
    b += tx(905, 303, "\u2191 WhatsApp", "t3", "start")
    b += tx(30, 458, t["nota"], "t3", "start")
    b += '  <g transform="translate(30,490)">\n'
    b += '    <line x1="0" y1="0" x2="26" y2="0" class="ln" style="marker-end:none"/>' + tx(34, 4, t["leg_ok"], "t3", "start")
    b += '    <line x1="190" y1="0" x2="216" y2="0" class="lnx" style="marker-end:none"/>' + tx(224, 4, t["leg_no"], "t3", "start")
    b += '    <line x1="400" y1="0" x2="426" y2="0" class="lnd"/>' + tx(434, 4, t["leg_vol"], "t3", "start")
    b += "  </g>\n"
    return svg(1040, 510, t["lang"], t["titulo"], t["desc"], b), t["arquivo"]


TXT_INSTALACAO = {
    "en": dict(
        titulo="Install with an agent", sub="You paste one short prompt. The agent does the rest and stops where only you can act.",
        passos=[
            ("1  You paste the prompt", "short text from the README", True),
            ("2  Agent reads the skill", "instalar-whatsapp", False),
            ("3  Diagnostic", "read-only, after every step", False),
            ("4  Asks every choice at once", "path, audio, skills", False),
            ("5  Gets the bridge", "ready-made, SHA-256 checked", False),
            ("6  You scan the QR", "WhatsApp, Linked devices", True),
            ("7  Registers the MCP server", "asks before editing config", False),
            ("8  Proves it works", "lists one chat, never sends", False),
            ("9  You choose the send mode", "installed as read-only", True),
        ],
        leg_voce="you act or decide", leg_agente="the agent acts",
        desc="Nine steps. You paste a short prompt. The agent reads the install skill, runs a read-only diagnostic after every step, asks every choice in one message, installs what is missing asking first, gets the ready-made bridge (or builds it), then stops so you can scan the QR code. It registers the MCP server, proves it works by listing one chat without sending anything, and stops again so you choose the send mode. The install ends with sending disabled.",
        arquivo="install-flow.svg", lang="en",
    ),
    "pt": dict(
        titulo="Instalar com um agente", sub="Voc\u00ea cola um prompt curto. O agente faz o resto e para onde s\u00f3 voc\u00ea pode agir.",
        passos=[
            ("1  Voc\u00ea cola o prompt", "texto curto do README", True),
            ("2  O agente l\u00ea a skill", "instalar-whatsapp", False),
            ("3  Diagn\u00f3stico", "s\u00f3 l\u00ea, depois de cada passo", False),
            ("4  Pergunta tudo de uma vez", "caminho, \u00e1udio e skills", False),
            ("5  Obt\u00e9m a bridge", "pronta, com SHA-256 conferido", False),
            ("6  Voc\u00ea l\u00ea o QR", "WhatsApp, Aparelhos conectados", True),
            ("7  Registra o servidor MCP", "pergunta antes de editar a config", False),
            ("8  Prova que funciona", "lista um chat, nunca envia", False),
            ("9  Voc\u00ea escolhe o envio", "instalado como read-only", True),
        ],
        leg_voce="voc\u00ea age ou decide", leg_agente="o agente age",
        desc="Nove passos. Voc\u00ea cola um prompt curto. O agente l\u00ea a skill de instala\u00e7\u00e3o, roda um diagn\u00f3stico que s\u00f3 l\u00ea depois de cada passo, pergunta todas as escolhas em uma mensagem, instala o que falta perguntando antes, obt\u00e9m a bridge pronta (ou compila), e para para voc\u00ea ler o QR. Ele registra o servidor MCP, prova que funciona listando um chat sem enviar nada, e para de novo para voc\u00ea escolher o modo de envio. A instala\u00e7\u00e3o termina com o envio desligado.",
        arquivo="fluxo-instalacao.svg", lang="pt-BR",
    ),
}


def instalacao(lang):
    t = TXT_INSTALACAO[lang]
    b = cabecalho(t["titulo"], t["sub"])
    largura, folga, h = 188, 20, 92
    linha1 = [26 + i * (largura + folga) for i in range(5)]
    linha2 = [26 + i * (largura + folga) for i in range(4)]
    y1, y2 = 100, 270
    posicoes = [(x, y1) for x in linha1] + [(x, y2) for x in linha2]
    for (titulo, sub, humano), (x, y) in zip(t["passos"], posicoes):
        cls = "boxg" if humano else "box"
        b += f'  <rect x="{x}" y="{y}" width="{largura}" height="{h}" rx="14" class="{cls}"/>\n'
        b += tx(x + largura / 2, y + 38, titulo, "t1", "middle", ' style="font-size:13.5px"')
        b += tx(x + largura / 2, y + 62, sub, "t3")
    for i in range(4):
        x = linha1[i] + largura
        b += f'  <line x1="{x}" y1="{y1 + h / 2}" x2="{x + folga - 2}" y2="{y1 + h / 2}" class="lnn"/>\n'
    for i in range(3):
        x = linha2[i] + largura
        b += f'  <line x1="{x}" y1="{y2 + h / 2}" x2="{x + folga - 2}" y2="{y2 + h / 2}" class="lnn"/>\n'
    cx5, cx6 = linha1[4] + largura / 2, linha2[0] + largura / 2
    b += f'  <path d="M{cx5},{y1 + h} V{y1 + h + 38} H{cx6} V{y2 - 2}" class="lnn"/>\n'
    b += '  <g transform="translate(30,400)">\n'
    b += '    <rect x="0" y="-8" width="22" height="14" rx="4" class="boxg"/>' + tx(32, 4, t["leg_voce"], "t3", "start")
    b += '    <rect x="190" y="-8" width="22" height="14" rx="4" class="box"/>' + tx(222, 4, t["leg_agente"], "t3", "start")
    b += "  </g>\n"
    return svg(1040, 424, t["lang"], t["titulo"], t["desc"], b), t["arquivo"]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sobras = []
    sobras += traduzir("arquitetura.svg", "architecture.svg", EN_ARQUITETURA)
    sobras += traduzir("fluxo-envio.svg", "send-flow.svg", EN_FLUXO)
    sobras += traduzir("fluxo-envio-animado.svg", "send-flow-animated.svg", EN_FLUXO)
    for lang in ("en", "pt"):
        for fabrica in (modos, isolamento, instalacao):
            conteudo, nome = fabrica(lang)
            (DOCS / nome).write_text(conteudo, encoding="utf-8", newline="")
    print("gerados. textos em portugues que sobraram nas versoes em ingles:", sobras or "nenhum")


main()