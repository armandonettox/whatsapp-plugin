"""Transcricao de audio via Whisper local (opcional).

O Whisper nao vem na instalacao padrao porque puxa o PyTorch (alguns GB) e baixa um modelo na
primeira vez. Para ativar: `uv sync --extra audio` (e ter o ffmpeg no PATH).

Carrega o modelo uma vez e reaproveita entre chamadas (carregar o modelo a cada transcricao
seria muito lento). Modelo padrao "small" -- equilibrio entre velocidade e precisao em CPU.

Variaveis de ambiente:
- WHISPER_MODELO: tiny, base, small (padrao), medium ou large
- WHATSAPP_AUDIO_LANGUAGE: codigo do idioma falado nos audios (padrao "pt"; ex: "en", "es")
"""

import os

_MODELO_PADRAO = os.getenv("WHISPER_MODELO", "small")
_IDIOMA = os.getenv("WHATSAPP_AUDIO_LANGUAGE", "pt")
_model_cache = {}

AVISO_SEM_WHISPER = (
    "[transcricao indisponivel: o Whisper nao esta instalado. "
    "Rode `uv sync --extra audio` na pasta whatsapp/mcp-server e instale o ffmpeg]"
)


def _carregar_modelo(nome_modelo: str):
    if nome_modelo not in _model_cache:
        import whisper

        _model_cache[nome_modelo] = whisper.load_model(nome_modelo)
    return _model_cache[nome_modelo]


def transcrever_audio(caminho_arquivo: str, modelo: str = None) -> str:
    """Transcreve um arquivo de audio usando Whisper local.

    Args:
        caminho_arquivo: caminho local do arquivo de audio
        modelo: nome do modelo Whisper (tiny/base/small/medium). Usa
            WHISPER_MODELO do ambiente ou "small" se nao especificado.

    Returns:
        Texto transcrito, ou uma mensagem entre colchetes se o Whisper nao estiver
        instalado ou a transcricao falhar.
    """
    nome_modelo = modelo or _MODELO_PADRAO
    try:
        model = _carregar_modelo(nome_modelo)
    except ImportError:
        return AVISO_SEM_WHISPER
    except Exception as e:
        return f"[erro ao carregar o modelo Whisper: {e}]"

    try:
        resultado = model.transcribe(caminho_arquivo, language=_IDIOMA)
        return resultado["text"].strip()
    except Exception as e:
        return f"[erro na transcricao: {e}]"
