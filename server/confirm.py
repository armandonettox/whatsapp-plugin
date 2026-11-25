"""Confirma, ve ou descarta os rascunhos de envio. Roda so em terminal de verdade, fora do agente.

Uso (na pasta server/):
    python confirm.py list                lista os rascunhos esperando confirmacao
    python confirm.py show <id>           mostra o rascunho inteiro
    python confirm.py send <id>           mostra e pergunta; so envia se voce digitar "enviar"
    python confirm.py send <id1> <id2>    varias partes da mesma conversa, com uma so confirmacao
    python confirm.py discard <id>        descarta um rascunho
    python confirm.py discard --all       descarta todos

Este comando nao tem opcao para pular a pergunta e recusa rodar sem um terminal interativo.
Foi feito para ser a etapa que o agente nao faz sozinho (modo WHATSAPP_SEND_MODE=two-step).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seguranca  # noqa: E402

PALAVRA_DE_CONFIRMACAO = "enviar"


def nome_do_destinatario(destinatario: str):
    """Tenta achar o nome do contato nos bancos locais. Devolve None se nao achar."""
    try:
        import whatsapp

        jid = destinatario if "@" in destinatario else f"{destinatario}@s.whatsapp.net"
        nome = whatsapp.get_sender_name(jid)
        return nome if nome and nome != jid else None
    except Exception:
        return None


def descrever(registro: dict, nome=None, agora=None) -> str:
    agora = time.time() if agora is None else agora
    tipos = {"message": "mensagem de texto", "file": "arquivo", "audio": "áudio"}
    linhas = [f"Rascunho {registro['id']} ({tipos.get(registro['tipo'], registro['tipo'])})"]
    para = registro["destinatario"] + (f"  ({nome})" if nome else "")
    linhas.append(f"Para: {para}")
    criado = max(0, int((agora - registro["criado_em"]) // 60))
    restante = max(0, int((registro["expira_em"] - agora) // 60))
    linhas.append(f"Criado há {criado} min; expira em {restante} min")
    linhas.append("-" * 40)
    if registro["tipo"] == "message":
        linhas.append(registro["mensagem"])
    else:
        linhas.append(f"Arquivo: {registro['arquivo']}")
    linhas.append("-" * 40)
    return "\n".join(linhas)


def enviar_de_verdade(registro: dict):
    """Chama a bridge. Devolve (ok, texto)."""
    import whatsapp

    if registro["tipo"] == "message":
        return whatsapp.send_message(registro["destinatario"], registro["mensagem"])
    if registro["tipo"] == "file":
        return whatsapp.send_file(registro["destinatario"], registro["arquivo"])
    return whatsapp.send_audio_message(registro["destinatario"], registro["arquivo"])


def enviar_pendente(id_, confirmar, enviar=enviar_de_verdade, pasta=None, agora=None):
    """Envia um rascunho se, e so se, `confirmar(registro)` devolver True.

    Devolve (enviado, texto). `confirmar` e `enviar` entram como parametro para o teste nao
    precisar de terminal nem de bridge; o comando real passa a pergunta no terminal.
    """
    pasta = pasta or seguranca.pasta_de_pendentes()
    try:
        registro = seguranca.carregar_pendente(id_, pasta, agora)
    except seguranca.ErroDeRascunho as erro:
        return False, str(erro)
    if registro is None:
        return False, "Rascunho não encontrado, já enviado, descartado ou expirado."
    if not confirmar(registro):
        return False, "Cancelado. Nada foi enviado."
    ok, texto = enviar(registro)
    if ok:
        seguranca.marcar(pasta, id_, "sent")
        return True, texto
    return False, f"Falhou, o rascunho continua guardado: {texto}"


def confirmar_no_terminal(registro: dict) -> bool:
    print(descrever(registro, nome_do_destinatario(registro["destinatario"])))
    resposta = input(f'Digite "{PALAVRA_DE_CONFIRMACAO}" para enviar agora, ou Enter para cancelar: ')
    return resposta.strip().lower() == PALAVRA_DE_CONFIRMACAO


def enviar_varios(ids, confirmar, enviar=enviar_de_verdade, pasta=None, agora=None, pausa=2.0, dormir=time.sleep):
    """Envia varias partes, na ordem, com UMA confirmacao. Devolve (todas_enviadas, texto).

    Travas: todas as partes precisam existir e ser para o mesmo destinatario, senao nada e
    enviado; se uma parte falhar, as seguintes nao saem e as que sobraram continuam guardadas.
    """
    pasta = pasta or seguranca.pasta_de_pendentes()
    registros = []
    for id_ in ids:
        try:
            registro = seguranca.carregar_pendente(id_, pasta, agora)
        except seguranca.ErroDeRascunho as erro:
            return False, f"{erro} Nada foi enviado."
        if registro is None:
            return False, f"Rascunho {id_} não encontrado, já enviado, descartado ou expirado. Nada foi enviado."
        registros.append(registro)
    if len({r["destinatario"] for r in registros}) > 1:
        return False, "As partes são para destinatários diferentes. Envie cada destinatário separadamente. Nada foi enviado."
    if not confirmar(registros):
        return False, "Cancelado. Nada foi enviado."
    enviados = 0
    for posicao, registro in enumerate(registros):
        if posicao:
            dormir(pausa)
        ok, texto = enviar(registro)
        if not ok:
            restantes = len(registros) - enviados
            return False, f"Falhou na parte {posicao + 1}: {texto}. {enviados} enviada(s); {restantes} continua(m) guardada(s)."
        seguranca.marcar(pasta, registro["id"], "sent")
        enviados += 1
    return True, f"{enviados} mensagem(ns) enviada(s)."


def confirmar_varios_no_terminal(registros: list) -> bool:
    nome = nome_do_destinatario(registros[0]["destinatario"])
    for numero, registro in enumerate(registros, 1):
        print(f"--- Parte {numero} de {len(registros)} ---")
        print(descrever(registro, nome))
    pergunta = f'Digite "{PALAVRA_DE_CONFIRMACAO}" para enviar as {len(registros)} partes agora, ou Enter para cancelar: '
    return input(pergunta).strip().lower() == PALAVRA_DE_CONFIRMACAO


def terminal_interativo() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def comando_list() -> int:
    registros = seguranca.listar_pendentes()
    if not registros:
        print("Nenhum rascunho esperando confirmação.")
        return 0
    for registro in registros:
        trecho = (registro["mensagem"] or registro["arquivo"] or "").replace("\n", " ")[:50]
        print(f"{registro['id']}  {registro['tipo']:8}  para {registro['destinatario']}  |  {trecho}")
    return 0


def comando_show(id_: str) -> int:
    try:
        registro = seguranca.carregar_pendente(id_)
    except seguranca.ErroDeRascunho as erro:
        print(erro)
        return 1
    if registro is None:
        print("Rascunho não encontrado ou expirado.")
        return 1
    print(descrever(registro, nome_do_destinatario(registro["destinatario"])))
    return 0


def comando_send(ids: list) -> int:
    if not terminal_interativo():
        print("Recusado: este comando só roda em um terminal interativo, digitado por uma pessoa.")
        print("Ele existe para você conferir o texto e confirmar fora do agente.")
        return 2
    if len(ids) == 1:
        enviado, texto = enviar_pendente(ids[0], confirmar_no_terminal)
    else:
        enviado, texto = enviar_varios(ids, confirmar_varios_no_terminal)
    print(texto)
    return 0 if enviado else 1


def comando_discard(alvo: str) -> int:
    pasta = seguranca.pasta_de_pendentes()
    try:
        ids = [r["id"] for r in seguranca.listar_pendentes(pasta)] if alvo == "--all" else [alvo]
        descartados = 0
        for id_ in ids:
            if seguranca.carregar_pendente(id_, pasta):
                seguranca.marcar(pasta, id_, "discarded")
                descartados += 1
    except seguranca.ErroDeRascunho as erro:
        print(erro)
        return 1
    print(f"{descartados} rascunho(s) descartado(s).")
    return 0 if descartados else 1


def main(argv) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    comando, resto = argv[0], argv[1:]
    if comando == "list":
        return comando_list()
    if comando == "send" and resto:
        return comando_send(resto)
    if comando in ("show", "discard") and len(resto) == 1:
        return {"show": comando_show, "discard": comando_discard}[comando](resto[0])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
