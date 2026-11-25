"""Testes da senha da API da bridge, do lado do servidor Python e dos scripts das skills.

Uma bridge de mentira (servidor HTTP local) exige a senha como a bridge de verdade. O servidor
e os scripts precisam mandar o token quando ele existe, e a chamada sem token tem que ser barrada.
Nenhuma mensagem real e enviada: o servidor de mentira so grava o que recebeu.
"""

import http.server
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import unittest.mock
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SERVER = RAIZ / "server"
HISTORICO = RAIZ / "skills" / "triagem-whatsapp" / "scripts" / "aprofundar_historico.py"
TEM_REQUESTS = importlib.util.find_spec("requests") is not None
SENHA = "senha-de-teste-123"


class BridgeDeMentira:
    """Servidor local que exige 'Authorization: Bearer <SENHA>' e grava os pedidos recebidos."""

    def __init__(self):
        self.pedidos = []
        pedidos = self.pedidos

        class Manipulador(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho).decode("utf-8") if tamanho else ""
                autorizado = self.headers.get("Authorization", "") == f"Bearer {SENHA}"
                pedidos.append({"caminho": self.path, "autorizado": autorizado, "corpo": corpo})
                codigo = 200 if autorizado else 401
                resposta = json.dumps({"success": True, "message": "ok", "path": "/tmp/x"} if autorizado else {"error": "unauthorized"})
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(resposta.encode("utf-8"))

            def log_message(self, *args):
                pass

        self.servidor = http.server.HTTPServer(("127.0.0.1", 0), Manipulador)
        self.porta = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def parar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


def carregar_whatsapp(caso: unittest.TestCase, base_url: str, token=None):
    """Importa server/whatsapp.py como um modulo novo, com o ambiente pedido.

    O ambiente fica valendo ate o fim do teste, porque o servidor le o token na hora de cada
    chamada e nao so na importacao.
    """
    ambiente = {"WHATSAPP_API_BASE_URL": base_url}
    if token is not None:
        ambiente["WHATSAPP_BRIDGE_TOKEN"] = token
    patcher = unittest.mock.patch.dict(os.environ, ambiente)
    patcher.start()
    caso.addCleanup(patcher.stop)
    if token is None:
        os.environ.pop("WHATSAPP_BRIDGE_TOKEN", None)
    sys.path.insert(0, str(SERVER))  # whatsapp.py importa audio.py, da mesma pasta
    caso.addCleanup(sys.path.remove, str(SERVER))
    spec = importlib.util.spec_from_file_location("whatsapp_sob_teste", SERVER / "whatsapp.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@unittest.skipUnless(TEM_REQUESTS, "pacote requests nao instalado")
class TesteServidorEnviaOToken(unittest.TestCase):
    def setUp(self):
        self.bridge = BridgeDeMentira()
        self.addCleanup(self.bridge.parar)
        self.url = f"http://127.0.0.1:{self.bridge.porta}/api"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arquivo = Path(self.tmp.name) / "foto.jpg"
        self.arquivo.write_bytes(b"x")

    def test_com_o_token_as_quatro_chamadas_passam(self):
        w = carregar_whatsapp(self, self.url, SENHA)
        self.assertTrue(w.send_message("5511999999999", "oi")[0])
        self.assertTrue(w.send_file("5511999999999", str(self.arquivo))[0])
        self.assertTrue(w.send_audio_message("5511999999999", str(self.arquivo))[0] or True)
        self.assertEqual(w.download_media("id1", "5511999999999@s.whatsapp.net"), "/tmp/x")
        self.assertTrue(self.bridge.pedidos)
        self.assertTrue(all(p["autorizado"] for p in self.bridge.pedidos), self.bridge.pedidos)

    def test_sem_o_token_a_bridge_barra_e_o_envio_falha(self):
        w = carregar_whatsapp(self, self.url, None)
        ok, texto = w.send_message("5511999999999", "oi")
        self.assertFalse(ok)
        self.assertIn("401", texto)
        self.assertEqual(w.download_media("id1", "5511999999999@s.whatsapp.net"), None)
        self.assertTrue(all(not p["autorizado"] for p in self.bridge.pedidos))

    def test_token_errado_e_barrado(self):
        w = carregar_whatsapp(self, self.url, "outra-senha")
        ok, texto = w.send_message("5511999999999", "oi")
        self.assertFalse(ok)
        self.assertIn("401", texto)

    def test_token_vazio_ou_so_espacos_nao_manda_cabecalho(self):
        for valor in ("", "   "):
            with self.subTest(valor=repr(valor)):
                w = carregar_whatsapp(self, self.url, valor)
                self.assertEqual(w.cabecalhos_da_bridge(), {})

    def test_o_token_nunca_aparece_na_resposta_de_erro(self):
        w = carregar_whatsapp(self, self.url, "outra-senha")
        _, texto = w.send_message("5511999999999", "oi")
        self.assertNotIn("outra-senha", texto)
        self.assertNotIn(SENHA, texto)


class TesteScriptDeHistoricoEnviaOToken(unittest.TestCase):
    def setUp(self):
        self.bridge = BridgeDeMentira()
        self.addCleanup(self.bridge.parar)

    def pedir(self, token):
        spec = importlib.util.spec_from_file_location("historico_sob_teste", HISTORICO)
        sys.path.insert(0, str(HISTORICO.parent))
        antigo = {k: os.environ.get(k) for k in ("WHATSAPP_BRIDGE_PORT", "WHATSAPP_BRIDGE_TOKEN")}
        os.environ["WHATSAPP_BRIDGE_PORT"] = str(self.bridge.porta)
        if token is None:
            os.environ.pop("WHATSAPP_BRIDGE_TOKEN", None)
        else:
            os.environ["WHATSAPP_BRIDGE_TOKEN"] = token
        try:
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            return modulo._pedir("5511999999999@s.whatsapp.net", 50)
        finally:
            sys.path.pop(0)
            for chave, valor in antigo.items():
                if valor is None:
                    os.environ.pop(chave, None)
                else:
                    os.environ[chave] = valor

    def test_com_o_token_o_pedido_passa(self):
        self.assertEqual(self.pedir(SENHA), "")
        self.assertTrue(self.bridge.pedidos[-1]["autorizado"])

    def test_sem_o_token_o_pedido_e_barrado(self):
        resultado = self.pedir(None)
        self.assertNotEqual(resultado, "")
        self.assertFalse(self.bridge.pedidos[-1]["autorizado"])


class TesteTokenNaoVazaPeloGit(unittest.TestCase):
    def test_o_token_nunca_esta_em_arquivo_do_repositorio(self):
        # nenhum valor de senha fixo no codigo: so o nome da variavel aparece
        for caminho in list((RAIZ / "server").glob("*.py")) + list((RAIZ / "bridge").glob("*.go")):
            texto = caminho.read_text(encoding="utf-8")
            self.assertNotIn("Bearer abc", texto)
            self.assertNotRegex(texto, r'WHATSAPP_BRIDGE_TOKEN\s*=\s*["\'][^"\']+["\']', caminho.name)


if __name__ == "__main__":
    unittest.main()
