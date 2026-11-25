"""Testes do baixar_bridge.py: baixa a bridge pronta da release e confere o SHA-256.

Um servidor HTTP local faz o papel do GitHub. Nada sai para a internet.
"""

import hashlib
import http.server
import importlib.util
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "instalar-whatsapp" / "scripts" / "baixar_bridge.py"
_spec = importlib.util.spec_from_file_location("baixar_bridge", SCRIPT)
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)

CONTEUDO = b"binario de mentira da bridge"


class ServidorDeRelease:
    """Serve /v<versao>/<arquivo> a partir de um dicionario."""

    def __init__(self, arquivos):
        arquivos_ = arquivos

        class Atendente(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                dados = arquivos_.get(self.path)
                if dados is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(dados)

            def log_message(self, *a):
                pass

        self.servidor = http.server.HTTPServer(("127.0.0.1", 0), Atendente)
        self.url = f"http://127.0.0.1:{self.servidor.server_port}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def parar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


def soma(dados):
    return hashlib.sha256(dados).hexdigest()


class NomesDosArquivos(unittest.TestCase):
    def test_nome_por_sistema_e_arquitetura(self):
        casos = {
            ("Windows", "AMD64"): "whatsapp-bridge-windows-amd64.exe",
            ("Linux", "x86_64"): "whatsapp-bridge-linux-amd64",
            ("Linux", "aarch64"): "whatsapp-bridge-linux-arm64",
            ("Darwin", "arm64"): "whatsapp-bridge-darwin-arm64",
            ("Darwin", "x86_64"): "whatsapp-bridge-darwin-amd64",
        }
        for (so, arq), esperado in casos.items():
            with self.subTest(so=so, arq=arq):
                self.assertEqual(b.nome_do_arquivo(so, arq), esperado)

    def test_sistema_ou_arquitetura_sem_binario(self):
        for so, arq in [("FreeBSD", "amd64"), ("Linux", "riscv64"), ("Windows", "arm64"), ("", "")]:
            with self.subTest(so=so, arq=arq):
                with self.assertRaises(b.SemBinario):
                    b.nome_do_arquivo(so, arq)

    def test_nome_no_disco_e_o_mesmo_que_o_go_build_gera(self):
        self.assertEqual(b.nome_no_disco("Windows"), "main.exe")
        self.assertEqual(b.nome_no_disco("Linux"), "whatsapp-bridge")
        self.assertEqual(b.nome_no_disco("Darwin"), "whatsapp-bridge")

    def test_soma_esperada_le_o_formato_do_sha256sum(self):
        texto = f"{'a' * 64}  outro-arquivo\n{'b' * 64} *whatsapp-bridge-linux-amd64\n"
        self.assertEqual(b.soma_esperada(texto, "whatsapp-bridge-linux-amd64"), "b" * 64)

    def test_soma_ausente_ou_mal_formada_e_erro(self):
        for texto in ("", f"{'a' * 64}  outro\n", f"zzzz  whatsapp-bridge-linux-amd64\n", f"{'a' * 10}  whatsapp-bridge-linux-amd64\n"):
            with self.subTest(texto=texto[:20]):
                with self.assertRaises(b.ErroDeSoma):
                    b.soma_esperada(texto, "whatsapp-bridge-linux-amd64")


class Download(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.arquivo = "whatsapp-bridge-linux-amd64"

    def servir(self, binario=CONTEUDO, soma_publicada=None, com_somas=True, com_binario=True):
        arquivos = {}
        if com_somas:
            arquivos["/v9.9.9/SHA256SUMS"] = f"{soma_publicada or soma(CONTEUDO)}  {self.arquivo}\n".encode()
        if com_binario:
            arquivos["/v9.9.9/" + self.arquivo] = binario
        s = ServidorDeRelease(arquivos)
        self.addCleanup(s.parar)
        return s

    def baixar(self, s, **kw):
        return b.baixar_bridge(self.raiz, "9.9.9", s.url, "Linux", "x86_64", **kw)

    def test_baixa_confere_e_grava_executavel(self):
        destino = self.baixar(self.servir())
        self.assertEqual(destino, self.raiz / "bridge" / "whatsapp-bridge")
        self.assertEqual(destino.read_bytes(), CONTEUDO)
        if os.name != "nt":
            self.assertTrue(os.access(destino, os.X_OK))
        self.assertEqual([p.name for p in destino.parent.iterdir()], ["whatsapp-bridge"])

    def test_soma_diferente_recusa_e_nao_grava_nada(self):
        s = self.servir(binario=b"outro conteudo adulterado")
        with self.assertRaises(b.ErroDeSoma):
            self.baixar(s)
        self.assertFalse((self.raiz / "bridge" / "whatsapp-bridge").exists())
        pasta = self.raiz / "bridge"
        self.assertEqual(list(pasta.iterdir()) if pasta.exists() else [], [])

    def test_sem_arquivo_de_somas_recusa(self):
        with self.assertRaises(b.ErroDeRede):
            self.baixar(self.servir(com_somas=False))
        self.assertFalse((self.raiz / "bridge" / "whatsapp-bridge").exists())

    def test_binario_ausente_na_release_e_erro_de_rede(self):
        with self.assertRaises(b.ErroDeRede):
            self.baixar(self.servir(com_binario=False))

    def test_nao_substitui_sem_forcar_e_substitui_com_forcar(self):
        s = self.servir()
        destino = self.raiz / "bridge" / "whatsapp-bridge"
        destino.parent.mkdir()
        destino.write_bytes(b"antiga")
        with self.assertRaises(FileExistsError):
            self.baixar(s)
        self.assertEqual(destino.read_bytes(), b"antiga")
        self.baixar(s, forcar=True)
        self.assertEqual(destino.read_bytes(), CONTEUDO)

    def test_sistema_sem_binario_nao_toca_a_rede(self):
        with self.assertRaises(b.SemBinario):
            b.baixar_bridge(self.raiz, "9.9.9", "http://127.0.0.1:9", "Linux", "riscv64")

    def test_versao_vem_do_plugin_json(self):
        v = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertEqual(b.versao_do_plugin(), v)


class NomesBatemComOFluxoDeRelease(unittest.TestCase):
    def test_o_fluxo_de_release_publica_exatamente_os_arquivos_que_o_script_procura(self):
        fluxo = (RAIZ / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        for so, arq in sorted(b.DISPONIVEIS):
            nome = b.nome_do_arquivo(so, arq)
            with self.subTest(nome=nome):
                self.assertIn(nome, fluxo)
        self.assertIn("SHA256SUMS", fluxo)


if __name__ == "__main__":
    unittest.main()
