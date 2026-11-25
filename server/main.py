import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media
)
from transcricao import transcrever_audio
import seguranca

# Modo de envio (WHATSAPP_SEND_MODE): read-only (padrao), two-step ou hook. Ver seguranca.py.
MODO_DE_ENVIO = seguranca.modo_de_envio()

INSTRUCOES_POR_MODO = {
    "read-only": (
        "Sending is DISABLED in this server (WHATSAPP_SEND_MODE=read-only, the safe default). "
        "You can search contacts, read chats and messages, download media and transcribe audio. "
        "If the person wants to send a message, tell them to set WHATSAPP_SEND_MODE=two-step "
        "(you save drafts and they confirm in their own terminal) or hook (only in Claude Code "
        "with this plugin's send guard). Do not try to send by other means."
    ),
    "two-step": (
        "Sending is TWO-STEP. send_message, send_file and send_audio_message only SAVE A DRAFT; "
        "nothing is sent. After saving, show the person the exact text and recipient and give them "
        "the command from how_to_send to run in their own terminal. If you split a reply into "
        "several messages, save each part in order and give the person ONE command with every "
        "pending_id: python confirm.py send <id1> <id2> <id3>. Never say a message was sent: "
        "use check_pending_send to see whether the person confirmed it."
    ),
    "hook": (
        "Sending is direct. Before any send tool, show the person the exact text and the "
        "recipient and wait for their explicit confirmation in this conversation."
    ),
}

# Initialize FastMCP server
try:
    TRANSPORTE = seguranca.configuracao_de_transporte()
except seguranca.ErroDeConfiguracao as erro:
    raise SystemExit(f"Configuracao invalida: {erro}")

_argumentos_http = {}
if TRANSPORTE["transporte"] == "streamable-http":
    from mcp.server.transport_security import TransportSecuritySettings

    _argumentos_http = {"host": TRANSPORTE["host"], "port": TRANSPORTE["porta"]}
    if TRANSPORTE["hosts_permitidos"]:
        _argumentos_http["transport_security"] = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=TRANSPORTE["hosts_permitidos"],
            allowed_origins=[],
        )

mcp = FastMCP("whatsapp", instructions=INSTRUCOES_POR_MODO[MODO_DE_ENVIO], **_argumentos_http)

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def transcribe_audio(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download and transcribe an audio message using local Whisper (language set by WHATSAPP_AUDIO_LANGUAGE, default Portuguese). Needs the optional audio extra (uv sync --extra audio) and ffmpeg.

    Args:
        message_id: The ID of the message containing the audio
        chat_jid: The JID of the chat containing the message

    Returns:
        A dictionary with success status and the transcribed text
    """
    file_path = whatsapp_download_media(message_id, chat_jid)

    if not file_path:
        return {
            "success": False,
            "message": "Failed to download audio"
        }

    texto = transcrever_audio(file_path)
    if texto.startswith("["):
        # mensagem de erro/aviso da transcricao (ex: Whisper nao instalado)
        return {
            "success": False,
            "message": texto,
            "audio_file": file_path
        }
    return {
        "success": True,
        "message": "Audio transcribed successfully",
        "transcription": texto
    }


CAMINHO_DO_CONFIRM = Path(__file__).resolve().parent / "confirm.py"


def _guardar_rascunho(tipo, recipient, message=None, media_path=None) -> Dict[str, Any]:
    """Modo two-step: guarda o rascunho e NAO envia nada."""
    try:
        registro = seguranca.criar_pendente(tipo, recipient, mensagem=message, arquivo=media_path)
    except seguranca.ErroDeRascunho as erro:
        return {"success": False, "sent": False, "message": str(erro)}
    minutos = seguranca.validade_em_segundos() // 60
    # Em container o comando e outro (por exemplo: podman exec -it whatsapp-mcp python confirm.py);
    # WHATSAPP_CONFIRM_COMMAND troca o comeco do comando mostrado a pessoa
    base = (os.environ.get("WHATSAPP_CONFIRM_COMMAND") or "").strip() or f'python "{CAMINHO_DO_CONFIRM}"'
    comando = f'{base} send {registro["id"]}'
    return {
        "success": True,
        "sent": False,
        "status": "pending_confirmation",
        "pending_id": registro["id"],
        "how_to_send": comando,
        "message": (
            "Draft saved. NOTHING WAS SENT. Show the person the text and the recipient and ask them "
            f"to run this in their own terminal: {comando} (valid for {minutos} minutes)."
        ),
    }


def send_message_two_step(recipient: str, message: str) -> Dict[str, Any]:
    """Save a WhatsApp text message as a DRAFT. It is NOT sent: the person must confirm it in their own terminal.

    Args:
        recipient: A phone number with country code but no + or other symbols, or a JID
        message: The message text to save as a draft

    Returns:
        pending_id, how_to_send (the command the person runs) and a message. sent is always False.
    """
    return _guardar_rascunho("message", recipient, message=message)


def send_file_two_step(recipient: str, media_path: str) -> Dict[str, Any]:
    """Save a file (picture, video, document) as a DRAFT. It is NOT sent: the person must confirm it in their own terminal.

    Args:
        recipient: A phone number with country code but no + or other symbols, or a JID
        media_path: The absolute path to the file

    Returns:
        pending_id, how_to_send (the command the person runs) and a message. sent is always False.
    """
    return _guardar_rascunho("file", recipient, media_path=media_path)


def send_audio_message_two_step(recipient: str, media_path: str) -> Dict[str, Any]:
    """Save an audio file as a DRAFT voice message. It is NOT sent: the person must confirm it in their own terminal.

    Args:
        recipient: A phone number with country code but no + or other symbols, or a JID
        media_path: The absolute path to the audio file

    Returns:
        pending_id, how_to_send (the command the person runs) and a message. sent is always False.
    """
    return _guardar_rascunho("audio", recipient, media_path=media_path)


def check_pending_send(pending_id: str) -> Dict[str, Any]:
    """Check what happened to a saved draft: pending, sent, discarded, expired or unknown. Never shows the content.

    Args:
        pending_id: The pending_id returned when the draft was saved
    """
    return {"pending_id": pending_id, "status": seguranca.estado_do_pendente(pending_id)}


def registrar_ferramentas_de_envio(modo: str) -> None:
    """Registra as ferramentas de envio conforme o modo. No read-only nao registra nenhuma."""
    if modo == "hook":
        mcp.tool()(send_message)
        mcp.tool()(send_file)
        mcp.tool()(send_audio_message)
    elif modo == "two-step":
        mcp.tool(name="send_message")(send_message_two_step)
        mcp.tool(name="send_file")(send_file_two_step)
        mcp.tool(name="send_audio_message")(send_audio_message_two_step)
        mcp.tool()(check_pending_send)


registrar_ferramentas_de_envio(MODO_DE_ENVIO)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport=TRANSPORTE["transporte"])