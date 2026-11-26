"""Testes do atualizar_plugin.py com um repositorio git local de mentira e uma API de releases falsa.

Nada sai para a internet. O "origin" e uma pasta local; as releases v0.1.0 e v0.1.1 sao tags nela.
Os testes travam: so verifica sem --aplicar, nunca toca em data/ nem em .env, recusa atualizar com
alteracoes locais ou historico divergente, e so mexe na bridge quando ela mudou e esta fechada.
"""

import http.server
import importlib.util
import json
import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "instalar-whatsapp" / "scripts" / "atualizar_plugin.py"
_spec = importlib.util.spec_from_file_location("atualizar_plugin", SCRIPT)
a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a)

GIT_AMBIENTE = {"GIT_AUTHOR_NAME": "Teste", "GIT_AUTHOR_EMAIL": "teste@example.com",
                "GIT_COMMITTER_NAME": "Teste", "GIT_COMMITTER_EMAIL": "teste@example.com"}
TEM_GIT = shutil.which("git") is not None


def git(pasta, *args):
    env = dict(os.environ)
    env.update(GIT_AMBIENTE)
    r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout.strip()


def escrever(pasta, nome, texto):
    f = Path(pasta) / nome
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


def plugin_json(versao):
    return json.dumps({"name": "whatsapp", "version": versao})


CHANGELOG = """# Changelog

## [0.1.1]

### Corrigido
- correcao de teste

## [0.1.0]

Primeira versao.
"""


class ApiFalsa:
    def __init__(self, tag, corpo="notas de teste", arquivos=None):
        respostas = {"/repos/dono/repo/releases/latest": json.dumps({"tag_name": tag, "body": corpo}).encode()}
        respostas.update(arquivos or {})

        class Atendente(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                dados = respostas.get(self.path)
                self.send_response(200 if dados is not None else 404)
                self.end_headers()
                if dados is not None:
                    self.wfile.write(dados)

            def log_message(self, *x):
                pass

        self.servidor = http.server.HTTPServer(("127.0.0.1", 0), Atendente)
        self.url = f"http://127.0.0.1:{self.servidor.server_port}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def parar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


@unittest.skipUnless(TEM_GIT, "precisa do git")
class AtualizacaoDoPlugin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.origin = base / "origin.git"
        self.autor = base / "autor"
        self.raiz = base / "instalado"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.autor)], check=True)
        git(self.autor, "remote", "add", "origin", str(self.origin))
        escrever(self.autor, ".claude-plugin/plugin.json", plugin_json("0.1.0"))
        # o .gitignore verdadeiro do plugin: ele ignora data/, .env e os binarios da bridge
        escrever(self.autor, ".gitignore", (RAIZ / ".gitignore").read_text(encoding="utf-8"))
        escrever(self.autor, "bridge/main.go", "package main // v0\n")
        escrever(self.autor, "container/x.container", "Image=a:0.1.0\n")
        escrever(self.autor, "server/pyproject.toml", "[project]\nname='x'\n")
        escrever(self.autor, "CHANGELOG.md", "# Changelog\n\n## [0.1.0]\n\nPrimeira versao.\n")
        git(self.autor, "add", "-A")
        git(self.autor, "commit", "-q", "-m", "v0.1.0")
        git(self.autor, "tag", "v0.1.0")
        git(self.autor, "push", "-q", "origin", "main", "--tags")
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.raiz)], check=True)
        # dados e segredos da pessoa, fora do git
        escrever(self.raiz, "data/store/messages.db", "dados reais")
        escrever(self.raiz, ".env", "WHATSAPP_BRIDGE_TOKEN=segredo-de-teste")

    def publicar_v011(self, bridge=False, container=False):
        escrever(self.autor, ".claude-plugin/plugin.json", plugin_json("0.1.1"))
        escrever(self.autor, "CHANGELOG.md", CHANGELOG)
        if bridge:
            escrever(self.autor, "bridge/main.go", "package main // v1\n")
        if container:
            escrever(self.autor, "container/x.container", "Image=a:0.1.1\n")
        git(self.autor, "add", "-A")
        git(self.autor, "commit", "-q", "-m", "v0.1.1")
        git(self.autor, "tag", "v0.1.1")
        git(self.autor, "push", "-q", "origin", "main", "--tags")

    def api(self, tag="v0.1.1", **kw):
        s = ApiFalsa(tag, **kw)
        self.addCleanup(s.parar)
        return s

    def aplicar(self, api, saida=None, **kw):
        linhas = []
        kw.setdefault("com_bridge", False)
        kw.setdefault("url_base_bridge", None)
        kw.setdefault("rodar", lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, "", ""))
        kw.setdefault("bridge_aberta", lambda: False)
        codigo = a.aplicar(self.raiz, "dono/repo", api.url, saida=linhas.append, **kw)
        return codigo, "\n".join(linhas)

    def versao_instalada(self):
        return json.loads((self.raiz / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]

    # --- verificar -------------------------------------------------------------------------

    def test_verificar_mostra_as_duas_versoes_e_nao_altera_nada(self):
        self.publicar_v011()
        antes = git(self.raiz, "rev-parse", "HEAD")
        linhas = []
        atual, nova = a.verificar(self.raiz, "dono/repo", self.api(corpo="o que mudou aqui").url, linhas.append)
        self.assertEqual((atual, nova), ("0.1.0", "0.1.1"))
        self.assertIn("o que mudou aqui", "\n".join(linhas))
        self.assertEqual(git(self.raiz, "rev-parse", "HEAD"), antes)
        self.assertEqual(self.versao_instalada(), "0.1.0")

    def test_sem_rede_o_codigo_de_saida_e_5(self):
        s = self.api()
        s.parar()
        with self.assertRaises(a.ErroDeAtualizacao) as c:
            a.verificar(self.raiz, "dono/repo", s.url, lambda *x: None)
        self.assertEqual(c.exception.codigo, 5)

    # --- aplicar ---------------------------------------------------------------------------

    def test_atualiza_o_codigo_para_a_ultima_release_e_mostra_o_que_mudou(self):
        self.publicar_v011()
        codigo, saida = self.aplicar(self.api())
        self.assertEqual(codigo, 0)
        self.assertEqual(self.versao_instalada(), "0.1.1")
        self.assertIn("correcao de teste", saida)
        self.assertNotIn("Primeira versao", saida)  # so as secoes mais novas que a instalada
        self.assertIn("Reinicie o agente", saida)

    def test_nunca_toca_em_dados_nem_em_segredos(self):
        self.publicar_v011(bridge=True, container=True)
        self.aplicar(self.api())
        self.assertEqual((self.raiz / "data" / "store" / "messages.db").read_text(), "dados reais")
        self.assertEqual((self.raiz / ".env").read_text(), "WHATSAPP_BRIDGE_TOKEN=segredo-de-teste")

    def test_ja_atualizado_nao_faz_nada(self):
        antes = git(self.raiz, "rev-parse", "HEAD")
        codigo, saida = self.aplicar(self.api(tag="v0.1.0"))
        self.assertEqual(codigo, 0)
        self.assertIn("Ja esta na ultima versao", saida)
        self.assertEqual(git(self.raiz, "rev-parse", "HEAD"), antes)

    def test_alteracao_local_em_arquivo_do_plugin_recusa_e_nao_muda_nada(self):
        self.publicar_v011()
        escrever(self.raiz, "bridge/main.go", "package main // remendo da pessoa\n")
        antes = git(self.raiz, "rev-parse", "HEAD")
        with self.assertRaises(a.ErroDeAtualizacao) as c:
            self.aplicar(self.api())
        self.assertEqual(c.exception.codigo, 3)
        self.assertIn("bridge/main.go", str(c.exception))
        self.assertEqual(git(self.raiz, "rev-parse", "HEAD"), antes)
        self.assertEqual((self.raiz / "bridge" / "main.go").read_text(), "package main // remendo da pessoa\n")
        self.assertEqual(self.versao_instalada(), "0.1.0")

    def test_arquivo_novo_ignorado_pelo_git_nao_impede_a_atualizacao(self):
        self.publicar_v011()
        escrever(self.raiz, "data/notas/maria.md", "nota")
        codigo, _ = self.aplicar(self.api())
        self.assertEqual(codigo, 0)

    def test_historico_divergente_recusa_sem_misturar(self):
        self.publicar_v011()
        escrever(self.raiz, "extra.txt", "commit local")
        git(self.raiz, "add", "extra.txt")
        git(self.raiz, "commit", "-q", "-m", "commit so meu")
        antes = git(self.raiz, "rev-parse", "HEAD")
        with self.assertRaises(a.ErroDeAtualizacao) as c:
            self.aplicar(self.api())
        self.assertEqual(c.exception.codigo, 4)
        self.assertEqual(git(self.raiz, "rev-parse", "HEAD"), antes)
        self.assertEqual(self.versao_instalada(), "0.1.0")

    def test_pasta_que_nao_e_git_recusa_com_orientacao(self):
        copia = Path(self.tmp.name) / "copia-sem-git"
        shutil.copytree(self.raiz, copia, ignore=shutil.ignore_patterns(".git"))
        with self.assertRaises(a.ErroDeAtualizacao) as c:
            a.aplicar(copia, "dono/repo", self.api().url, False, None, saida=lambda *x: None)
        self.assertEqual(c.exception.codigo, 2)
        self.assertIn("/plugin update", str(c.exception))

    # --- dependencias ----------------------------------------------------------------------

    def test_atualiza_as_dependencias_pelo_arquivo_de_travas(self):
        self.publicar_v011()
        chamadas = []
        self.aplicar(self.api(), rodar=lambda cmd, **k: chamadas.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(chamadas[0][:2], ["uv", "sync"])
        self.assertIn("--frozen", chamadas[0])
        self.assertNotIn("audio", chamadas[0])

    def test_mantem_o_extra_de_audio_quando_ja_estava_instalado(self):
        (self.raiz / "server" / ".venv" / "Lib" / "site-packages" / "whisper").mkdir(parents=True)
        self.assertEqual(a.comandos_de_dependencias(self.raiz)[-2:], ["--extra", "audio"])

    def test_falha_do_uv_vira_aviso_e_nao_desfaz_a_atualizacao(self):
        self.publicar_v011()
        codigo, saida = self.aplicar(self.api(), rodar=lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, "", "erro"))
        self.assertEqual(codigo, 0)
        self.assertIn("AVISO", saida)
        self.assertEqual(self.versao_instalada(), "0.1.1")

    # --- bridge e containers ---------------------------------------------------------------

    def test_bridge_sem_mudanca_nao_precisa_trocar(self):
        self.publicar_v011(bridge=False)
        _, saida = self.aplicar(self.api())
        self.assertIn("sem mudancas nesta versao", saida)

    def test_bridge_que_mudou_avisa_e_nao_troca_sem_o_pedido(self):
        self.publicar_v011(bridge=True)
        _, saida = self.aplicar(self.api())
        self.assertIn("o codigo dela mudou", saida)
        self.assertFalse((self.raiz / "bridge" / "whatsapp-bridge").exists())

    def test_com_bridge_aberta_nao_troca(self):
        self.publicar_v011(bridge=True)
        _, saida = self.aplicar(self.api(), com_bridge=True, bridge_aberta=lambda: True)
        self.assertIn("esta rodando", saida)
        self.assertFalse((self.raiz / "bridge" / "whatsapp-bridge").exists())

    def test_com_bridge_fechada_baixa_e_confere_a_soma(self):
        self.publicar_v011(bridge=True)
        baixar = a.carregar_baixar_bridge()
        try:
            arquivo = baixar.nome_do_arquivo(platform.system(), platform.machine())
        except baixar.SemBinario:
            self.skipTest("sem bridge pronta para este sistema")
        conteudo = b"bridge nova de mentira"
        soma = f"{hashlib.sha256(conteudo).hexdigest()}  {arquivo}\n".encode()
        api = self.api(arquivos={"/v0.1.1/SHA256SUMS": soma, f"/v0.1.1/{arquivo}": conteudo})
        _, saida = self.aplicar(api, com_bridge=True, url_base_bridge=api.url)
        destino = self.raiz / "bridge" / baixar.nome_no_disco(platform.system())
        self.assertEqual(destino.read_bytes(), conteudo)
        self.assertIn("baixada e conferida", saida)

    def test_soma_errada_nao_troca_a_bridge_que_ja_existe(self):
        self.publicar_v011(bridge=True)
        baixar = a.carregar_baixar_bridge()
        try:
            arquivo = baixar.nome_do_arquivo(platform.system(), platform.machine())
        except baixar.SemBinario:
            self.skipTest("sem bridge pronta para este sistema")
        existente = self.raiz / "bridge" / baixar.nome_no_disco(platform.system())
        existente.parent.mkdir(exist_ok=True)
        existente.write_bytes(b"bridge antiga")
        api = self.api(arquivos={"/v0.1.1/SHA256SUMS": f"{'0' * 64}  {arquivo}\n".encode(), f"/v0.1.1/{arquivo}": b"adulterada"})
        _, saida = self.aplicar(api, com_bridge=True, url_base_bridge=api.url)
        self.assertEqual(existente.read_bytes(), b"bridge antiga")
        self.assertIn("nao troquei", saida)

    def test_container_que_mudou_aponta_o_comando_de_atualizar(self):
        self.publicar_v011(container=True)
        _, saida = self.aplicar(self.api())
        self.assertIn("instalar-vps.sh atualizar", saida)

    # --- comparacao de versoes -------------------------------------------------------------

    def test_comparacao_de_versoes_e_numerica(self):
        self.assertLess(a.como_tupla("0.1.9"), a.como_tupla("0.1.10"))
        self.assertLess(a.como_tupla("0.9.0"), a.como_tupla("0.10.0"))
        self.assertEqual(a.como_tupla("v1.2"), (1, 2, 0))


if __name__ == "__main__":
    unittest.main()
