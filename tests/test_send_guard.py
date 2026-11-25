"""Testes do guarda de envio (hooks/whatsapp-send-guard.py).

Rodar: python -m unittest discover -s tests -v

O guarda falha fechado: se nao conseguir ler o historico, bloqueia. Por isso cada teste de
bloqueio precisa ter, ao lado, um teste que libera; so o caso que libera prova que o guarda
leu o historico de verdade.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARDA = Path(__file__).resolve().parents[1] / "hooks" / "whatsapp-send-guard.py"

ENVIO_AVULSO = "mcp__whatsapp__send_message"
ENVIO_PLUGIN = "mcp__plugin_whatsapp_whatsapp__send_message"
ARQUIVO_PLUGIN = "mcp__plugin_whatsapp_whatsapp__send_file"
AUDIO_PLUGIN = "mcp__plugin_whatsapp_whatsapp__send_audio_message"


def rodar_guarda(ferramenta: str, ultima_mensagem: str, com_historico: bool = True) -> int:
    """Roda o guarda como o Claude Code roda e devolve o codigo de saida."""
    with tempfile.TemporaryDirectory() as pasta:
        historico = Path(pasta) / "conversa.jsonl"
        if com_historico:
            linha = {"type": "user", "message": {"content": ultima_mensagem}}
            historico.write_text(json.dumps(linha) + "\n", encoding="utf-8")
        entrada = {"tool_name": ferramenta, "transcript_path": str(historico)}
        resultado = subprocess.run(
            [sys.executable, str(GUARDA)],
            input=json.dumps(entrada),
            capture_output=True,
            text=True,
        )
        return resultado.returncode


class TesteGuardaDeEnvio(unittest.TestCase):
    def test_libera_confirmacao_direta_no_mcp_avulso(self):
        self.assertEqual(rodar_guarda(ENVIO_AVULSO, "sim, manda"), 0)

    def test_libera_confirmacao_direta_no_mcp_de_plugin(self):
        self.assertEqual(rodar_guarda(ENVIO_PLUGIN, "sim, manda"), 0)

    def test_libera_nas_tres_ferramentas_de_envio(self):
        for ferramenta in (ENVIO_PLUGIN, ARQUIVO_PLUGIN, AUDIO_PLUGIN):
            with self.subTest(ferramenta=ferramenta):
                self.assertEqual(rodar_guarda(ferramenta, "pode enviar"), 0)

    def test_bloqueia_pedido_que_nao_e_confirmacao(self):
        self.assertEqual(rodar_guarda(ENVIO_PLUGIN, "escreve uma resposta pra ele"), 2)

    def test_bloqueia_confirmacao_com_edicao(self):
        self.assertEqual(rodar_guarda(ENVIO_PLUGIN, "sim, mas troca o oi"), 2)

    def test_bloqueia_pergunta(self):
        self.assertEqual(rodar_guarda(ENVIO_PLUGIN, "pode mandar agora?"), 2)

    def test_bloqueia_frase_longa(self):
        self.assertEqual(rodar_guarda(ENVIO_PLUGIN, "sim pode mandar essa mensagem para ele agora mesmo"), 2)

    def test_bloqueia_sem_historico_falha_fechada(self):
        self.assertEqual(rodar_guarda(ENVIO_PLUGIN, "sim, manda", com_historico=False), 2)

    def test_ignora_ferramenta_de_leitura(self):
        self.assertEqual(rodar_guarda("mcp__plugin_whatsapp_whatsapp__list_chats", "qualquer coisa"), 0)

    def test_ignora_envio_de_outro_mcp(self):
        self.assertEqual(rodar_guarda("mcp__outro__send_message", "qualquer coisa"), 0)


if __name__ == "__main__":
    unittest.main()
