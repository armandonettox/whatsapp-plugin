"""Testes do verificador de instalacao (skills/instalar-whatsapp/scripts/verificar_instalacao.py).

Nenhum teste mexe no computador de verdade: ferramentas, portas e bancos sao simulados.
A propriedade mais importante: o verificador nunca mostra o valor da senha da bridge.
"""

import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "skills" / "instalar-whatsapp" / "scripts" / "verificar_instalacao.py"
_spec = importlib.util.spec_from_file_location("verificador_de_instalacao", CAMINHO)
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)

SENHA = "senha-secreta-de-teste-987"


def estados(linhas):
    return {l["nome"]: l["estado"] for l in linhas}


class TesteFerramentas(unittest.TestCase):
    def todas(self, nome):
        return f"/usr/bin/{nome}"

    def test_instalacao_nativa_completa_esta_pronta(self):
        linhas = v.verificar_ferramentas("nativo", procurar=self.todas, versao=lambda c, p=None: (1, 25))
        e = estados(linhas)
        for nome in ("uv", "Go", "Compilador C", "ffmpeg"):
            self.assertEqual(e[nome], "OK" if nome != "ffmpeg" else "OK")
        self.assertTrue(v.resumo(linhas)["pronto"])

    def test_sem_nenhuma_ferramenta_faltam_as_obrigatorias_na_ordem(self):
        linhas = v.verificar_ferramentas("nativo", procurar=lambda n: None)
        faltam = [l["nome"] for l in linhas if l["estado"] == "FALTA"]
        self.assertEqual(faltam, ["uv", "Go", "Compilador C"])
        self.assertEqual(estados(linhas)["ffmpeg"], "INFO")
        self.assertFalse(v.resumo(linhas)["pronto"])

    def test_go_antigo_e_barrado(self):
        linhas = v.verificar_ferramentas("nativo", procurar=self.todas, versao=lambda c, p=None: (1, 21))
        self.assertEqual(estados(linhas)["Go"], "FALTA")

    def test_go_com_versao_ilegivel_e_barrado(self):
        linhas = v.verificar_ferramentas("nativo", procurar=self.todas, versao=lambda c, p=None: None)
        self.assertEqual(estados(linhas)["Go"], "FALTA")

    def test_aceita_qualquer_compilador_c(self):
        for achado in ("gcc", "cc", "clang"):
            with self.subTest(compilador=achado):
                linhas = v.verificar_ferramentas("nativo", procurar=lambda n, a=achado: f"/x/{n}" if n in (a, "uv", "go") else None,
                                                 versao=lambda c, p=None: (1, 25))
                self.assertEqual(estados(linhas)["Compilador C"], "OK")

    def test_caminho_container_so_pede_podman_ou_docker(self):
        com = v.verificar_ferramentas("container", procurar=lambda n: "/x/podman" if n == "podman" else None)
        self.assertEqual(estados(com)["Podman ou Docker"], "OK")
        self.assertNotIn("uv", estados(com))
        sem = v.verificar_ferramentas("container", procurar=lambda n: None)
        self.assertEqual(estados(sem)["Podman ou Docker"], "FALTA")


class TesteSessaoEBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)

    def banco(self, aparelhos):
        pasta = self.raiz / "data" / "store"
        pasta.mkdir(parents=True)
        con = sqlite3.connect(pasta / "whatsapp.db")
        con.execute("CREATE TABLE whatsmeow_device (jid TEXT)")
        for i in range(aparelhos):
            con.execute("INSERT INTO whatsmeow_device VALUES (?)", (f"x{i}",))
        con.commit()
        con.close()

    def test_sem_banco_a_sessao_nao_esta_pareada(self):
        self.assertEqual(estados(v.verificar_sessao(self.raiz, {}))["WhatsApp pareado"], "FALTA")

    def test_banco_sem_aparelho_nao_conta_como_pareado(self):
        self.banco(0)
        self.assertEqual(estados(v.verificar_sessao(self.raiz, {}))["WhatsApp pareado"], "FALTA")

    def test_banco_com_aparelho_esta_pareado(self):
        self.banco(1)
        self.assertEqual(estados(v.verificar_sessao(self.raiz, {}))["WhatsApp pareado"], "OK")

    def test_a_pasta_da_sessao_pode_vir_de_variavel(self):
        outra = self.raiz / "outra"
        (outra).mkdir()
        con = sqlite3.connect(outra / "whatsapp.db")
        con.execute("CREATE TABLE whatsmeow_device (jid TEXT)")
        con.execute("INSERT INTO whatsmeow_device VALUES ('a')")
        con.commit()
        con.close()
        self.assertEqual(estados(v.verificar_sessao(self.raiz, {"WHATSAPP_STORE_DIR": str(outra)}))["WhatsApp pareado"], "OK")

    def test_bridge_compilada(self):
        self.assertEqual(estados(v.verificar_bridge(self.raiz))["Bridge compilada"], "FALTA")
        (self.raiz / "bridge").mkdir()
        (self.raiz / "bridge" / "main.exe").write_bytes(b"x")
        self.assertEqual(estados(v.verificar_bridge(self.raiz))["Bridge compilada"], "OK")

    def test_bridge_ausente_aponta_para_o_download_da_pronta(self):
        linha = v.verificar_bridge(self.raiz)[0]
        self.assertEqual(linha["estado"], "FALTA")
        self.assertIn("baixar_bridge.py", linha["proximo"])

    def test_mcp_instalado_no_venv_do_servidor_conta_como_ok(self):
        self.assertFalse(v.mcp_no_ambiente_do_servidor(self.raiz))
        for sub in (("Lib", "site-packages"), ("lib", "python3.12", "site-packages")):
            with self.subTest(sub=sub):
                pasta = self.raiz / "server" / ".venv" / Path(*sub) / "mcp"
                pasta.mkdir(parents=True)
                self.assertTrue(v.mcp_no_ambiente_do_servidor(self.raiz))
                self.assertEqual(estados(v.verificar_pacote_mcp(self.raiz))["Pacote mcp do servidor"], "OK")
                shutil.rmtree(self.raiz / "server")

    def test_mcp_ausente_do_venv_nao_acusa_erro(self):
        for linha in v.verificar_pacote_mcp(self.raiz):
            self.assertNotEqual(linha["estado"], "FALTA")

    def test_bridge_parada_nao_e_erro(self):
        linhas = v.verificar_bridge_rodando({}, aceita=lambda h, p, t=1.0: False)
        self.assertEqual(estados(linhas)["Bridge rodando"], "INFO")

    def test_porta_ocupada_por_outra_bridge_nao_e_ok_quando_nao_esta_pareado(self):
        linhas = v.verificar_bridge_rodando({}, aceita=lambda h, p, t=1.0: h == "127.0.0.1", enderecos_da_maquina=[], pareada=False)
        e = estados(linhas)
        self.assertNotIn("Bridge rodando", e)
        self.assertEqual(e["Porta 8081 ocupada por outro processo"], "AVISO")
        self.assertIn("pergunte", linhas[0]["proximo"].lower())

    def test_porta_ocupada_com_sessao_pareada_e_ok(self):
        linhas = v.verificar_bridge_rodando({}, aceita=lambda h, p, t=1.0: h == "127.0.0.1", enderecos_da_maquina=[], pareada=True)
        self.assertEqual(estados(linhas), {"Bridge rodando": "OK"})

    def test_o_diagnostico_completo_liga_o_aviso_a_sessao(self):
        original = v.porta_aceita
        v.porta_aceita = lambda h, p, t=1.0: h == "127.0.0.1"
        v.verificar_bridge_rodando.__defaults__ = (v.porta_aceita, None, True)
        try:
            with tempfile.TemporaryDirectory() as pasta:
                linhas = v.verificar(Path(pasta), {}, "nativo")
        finally:
            v.porta_aceita = original
            v.verificar_bridge_rodando.__defaults__ = (original, None, True)
        self.assertIn("Porta 8081 ocupada por outro processo", estados(linhas))
        self.assertNotIn("Bridge rodando", estados(linhas))

    def test_bridge_so_no_loopback_esta_ok(self):
        linhas = v.verificar_bridge_rodando({}, aceita=lambda h, p, t=1.0: h == "127.0.0.1", enderecos_da_maquina=["192.0.2.10"])
        self.assertEqual(estados(linhas), {"Bridge rodando": "OK"})

    def test_bridge_exposta_sem_senha_e_bloqueio(self):
        linhas = v.verificar_bridge_rodando({}, aceita=lambda h, p, t=1.0: True, enderecos_da_maquina=["192.0.2.10"])
        self.assertEqual(estados(linhas)["Bridge exposta na rede"], "FALTA")
        self.assertFalse(v.resumo(linhas)["pronto"])

    def test_bridge_exposta_com_senha_so_avisa(self):
        linhas = v.verificar_bridge_rodando({"WHATSAPP_BRIDGE_TOKEN": SENHA}, aceita=lambda h, p, t=1.0: True,
                                            enderecos_da_maquina=["192.0.2.10"])
        self.assertEqual(estados(linhas)["Bridge escutando fora do computador"], "AVISO")
        self.assertTrue(v.resumo(linhas)["pronto"])


class TesteEnvioESenha(unittest.TestCase):
    def test_modo_segue_a_regra_do_servidor(self):
        casos = {"": "read-only", "lixo": "read-only", "TWO_STEP": "two-step", " hook ": "hook", "read-only": "read-only"}
        for valor, esperado in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(v.modo_de_envio({"WHATSAPP_SEND_MODE": valor}), esperado)

    def test_modo_hook_gera_aviso(self):
        self.assertEqual(estados(v.verificar_envio({"WHATSAPP_SEND_MODE": "hook"}))["Modo hook"], "AVISO")

    def test_senha_definida_ou_nao(self):
        com = estados(v.verificar_envio({"WHATSAPP_BRIDGE_TOKEN": SENHA}))["Senha da bridge"]
        sem = estados(v.verificar_envio({}))["Senha da bridge"]
        self.assertEqual((com, sem), ("OK", "INFO"))

    def test_a_senha_nunca_aparece_na_saida(self):
        ambiente = {"WHATSAPP_BRIDGE_TOKEN": SENHA, "WHATSAPP_SEND_MODE": "two-step"}
        linhas = v.verificar(RAIZ, ambiente, "nativo") + v.verificar(RAIZ, ambiente, "container")
        self.assertNotIn(SENHA, v.formatar(linhas))
        self.assertNotIn(SENHA, json.dumps(linhas))

    def test_senha_so_com_espacos_conta_como_nao_definida(self):
        self.assertEqual(estados(v.verificar_envio({"WHATSAPP_BRIDGE_TOKEN": "   "}))["Senha da bridge"], "INFO")


class TesteSaida(unittest.TestCase):
    def test_o_proximo_passo_e_o_primeiro_que_falta(self):
        linhas = [v.linha("OK", "a"), v.linha("FALTA", "b", "", "faca B"), v.linha("FALTA", "c", "", "faca C")]
        self.assertEqual(v.resumo(linhas), {"pronto": False, "faltam": 2, "proximo": "faca B"})
        self.assertIn("Comece por: faca B", v.formatar(linhas))

    def test_tudo_pronto(self):
        self.assertTrue(v.resumo([v.linha("OK", "a"), v.linha("INFO", "b")])["pronto"])

    def test_so_falta_e_aviso_mostram_a_dica(self):
        texto = v.formatar([v.linha("INFO", "x", "d", "dica-info"), v.linha("AVISO", "y", "d", "dica-aviso")])
        self.assertNotIn("dica-info", texto)
        self.assertIn("dica-aviso", texto)

    def test_linha_de_comando_json_e_codigo_de_saida(self):
        r = subprocess.run([sys.executable, str(CAMINHO), "--json", "--caminho", "container"], capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        dados = json.loads(r.stdout)
        self.assertIn("linhas", dados)
        self.assertEqual(r.returncode, 0 if dados["pronto"] else 1)

    def test_linha_de_comando_texto(self):
        r = subprocess.run([sys.executable, str(CAMINHO)], capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertIn("Sistema:", r.stdout)
        self.assertIn("Python", r.stdout)


if __name__ == "__main__":
    unittest.main()
