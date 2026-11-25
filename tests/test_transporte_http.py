"""Testes do transporte HTTP do servidor MCP (WHATSAPP_MCP_TRANSPORT=streamable-http).

O modo HTTP existe para agentes que nao conseguem iniciar o servidor por stdio (por exemplo, um
container sem uv). Estes testes sobem o servidor de verdade em uma porta livre e conferem que:
- a configuracao recusa o que e inseguro;
- o servidor responde ao protocolo;
- um nome de host que nao esta na lista permitida e recusado.

Os testes que sobem o servidor precisam do pacote mcp e sao pulados sem ele.
"""

import http.client
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SERVER = RAIZ / "server"
sys.path.insert(0, str(SERVER))

import seguranca  # noqa: E402

TEM_MCP = importlib.util.find_spec("mcp") is not None

INICIAR = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "teste", "version": "0"}},
})
CABECALHOS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


class TesteConfiguracaoDeTransporte(unittest.TestCase):
    def config(self, **ambiente):
        return seguranca.configuracao_de_transporte(ambiente)

    def test_padrao_e_stdio(self):
        self.assertEqual(self.config()["transporte"], "stdio")
        self.assertEqual(self.config(WHATSAPP_MCP_TRANSPORT="")["transporte"], "stdio")

    def test_aceita_http_com_variacao_de_escrita(self):
        for valor in ("streamable-http", "STREAMABLE_HTTP", " Streamable-Http "):
            with self.subTest(valor=valor):
                self.assertEqual(self.config(WHATSAPP_MCP_TRANSPORT=valor)["transporte"], "streamable-http")

    def test_transporte_desconhecido_da_erro_em_vez_de_cair_em_silencio(self):
        for valor in ("http", "sse", "tcp", "aberto", "1"):
            with self.subTest(valor=valor):
                with self.assertRaises(seguranca.ErroDeConfiguracao):
                    self.config(WHATSAPP_MCP_TRANSPORT=valor)

    def test_http_local_nao_pede_lista_de_hosts(self):
        for host in ("127.0.0.1", "localhost", "::1", ""):
            with self.subTest(host=host):
                c = self.config(WHATSAPP_MCP_TRANSPORT="streamable-http", WHATSAPP_MCP_HOST=host)
                self.assertIn(c["host"], seguranca.HOSTS_LOCAIS)

    def test_http_fora_do_computador_exige_a_lista_de_hosts(self):
        for host in ("0.0.0.0", "10.0.0.5", "whatsapp-mcp", "::"):
            with self.subTest(host=host):
                with self.assertRaises(seguranca.ErroDeConfiguracao):
                    self.config(WHATSAPP_MCP_TRANSPORT="streamable-http", WHATSAPP_MCP_HOST=host)
                with self.assertRaises(seguranca.ErroDeConfiguracao):
                    self.config(WHATSAPP_MCP_TRANSPORT="streamable-http", WHATSAPP_MCP_HOST=host,
                                WHATSAPP_MCP_ALLOWED_HOSTS=" , ")

    def test_http_fora_do_computador_com_a_lista_de_hosts_e_aceito(self):
        c = self.config(WHATSAPP_MCP_TRANSPORT="streamable-http", WHATSAPP_MCP_HOST="0.0.0.0",
                        WHATSAPP_MCP_ALLOWED_HOSTS="whatsapp-mcp:8765, whatsapp-mcp ")
        self.assertEqual(c["hosts_permitidos"], ["whatsapp-mcp:8765", "whatsapp-mcp"])
        self.assertEqual(c["porta"], seguranca.PORTA_PADRAO_HTTP)

    def test_porta_invalida_e_recusada(self):
        for porta in ("0", "70000", "abc", "-1", "80.5"):
            with self.subTest(porta=porta):
                with self.assertRaises(seguranca.ErroDeConfiguracao):
                    self.config(WHATSAPP_MCP_TRANSPORT="streamable-http", WHATSAPP_MCP_PORT=porta)

    def test_porta_valida(self):
        self.assertEqual(self.config(WHATSAPP_MCP_TRANSPORT="streamable-http", WHATSAPP_MCP_PORT="9000")["porta"], 9000)

    def test_stdio_ignora_as_variaveis_de_http(self):
        c = self.config(WHATSAPP_MCP_HOST="0.0.0.0", WHATSAPP_MCP_PORT="lixo")
        self.assertEqual(c["transporte"], "stdio")


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(TEM_MCP, "pacote mcp nao instalado")
class TesteServidorHttpDeVerdade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.porta = porta_livre()
        env = {k: v for k, v in os.environ.items() if not k.startswith("WHATSAPP_")}
        env.update({
            "WHATSAPP_MCP_TRANSPORT": "streamable-http", "WHATSAPP_MCP_HOST": "127.0.0.1",
            "WHATSAPP_MCP_PORT": str(cls.porta), "WHATSAPP_PENDING_DIR": str(Path(cls.tmp.name) / "p"),
            "WHATSAPP_API_BASE_URL": "http://127.0.0.1:9/api", "PYTHONIOENCODING": "utf-8",
        })
        cls.processo = subprocess.Popen([sys.executable, str(SERVER / "main.py")], cwd=SERVER, env=env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        limite = time.time() + 40
        while time.time() < limite:
            try:
                socket.create_connection(("127.0.0.1", cls.porta), timeout=0.5).close()
                return
            except OSError:
                if cls.processo.poll() is not None:
                    break
                time.sleep(0.3)
        cls.tearDownClass()
        raise unittest.SkipTest("servidor HTTP nao subiu a tempo")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "processo", None) and cls.processo.poll() is None:
            cls.processo.terminate()
            try:
                cls.processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.processo.kill()
        cls.tmp.cleanup()

    def pedir(self, host=None, metodo="POST", corpo=INICIAR):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=15)
        cabecalhos = dict(CABECALHOS)
        if host:
            cabecalhos["Host"] = host
        conexao.request(metodo, "/mcp", body=corpo if metodo == "POST" else None, headers=cabecalhos)
        resposta = conexao.getresponse()
        corpo_resposta = resposta.read().decode("utf-8", "replace")
        conexao.close()
        return resposta.status, corpo_resposta

    def test_responde_ao_protocolo_e_se_apresenta(self):
        status, corpo = self.pedir(host=f"127.0.0.1:{self.porta}")
        self.assertEqual(status, 200, corpo[:200])
        self.assertIn("whatsapp", corpo)

    def test_as_instrucoes_do_modo_vao_pelo_protocolo(self):
        _, corpo = self.pedir(host=f"localhost:{self.porta}")
        self.assertIn("DISABLED", corpo)  # o servidor de teste esta em read-only

    def test_nome_de_host_nao_permitido_e_recusado(self):
        for host in ("outro-servidor:8765", "evil.example:80", "10.1.2.3:8765"):
            with self.subTest(host=host):
                status, _ = self.pedir(host=host)
                self.assertGreaterEqual(status, 400, host)
                self.assertLess(status, 500)


if __name__ == "__main__":
    unittest.main()
