"""Testes das imagens em docs/: geradas pelo script, validas e na paleta do projeto.

As imagens em ingles e os fluxos novos sao gerados por scripts/gerar-diagramas.py. Estes testes
exigem que o que esta no repositorio seja exatamente o que o script gera, para ninguem editar uma
versao e esquecer a outra.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
SCRIPT = RAIZ / "scripts" / "gerar-diagramas.py"
FONTES = ("arquitetura.svg", "fluxo-envio.svg", "fluxo-envio-animado.svg")
GERADAS = (
    "architecture.svg", "send-flow.svg", "send-flow-animated.svg",
    "send-modes.svg", "modos-de-envio.svg", "container-isolation.svg", "isolamento-containers.svg",
    "install-flow.svg", "fluxo-instalacao.svg",
)
TODAS = FONTES + GERADAS


class TesteImagensGeradas(unittest.TestCase):
    def test_o_que_esta_no_repositorio_e_o_que_o_script_gera(self):
        with tempfile.TemporaryDirectory() as pasta:
            copia = Path(pasta)
            for nome in FONTES:
                shutil.copy(DOCS / nome, copia / nome)
            r = subprocess.run([sys.executable, str(SCRIPT), str(copia)], capture_output=True, text=True,
                               encoding="utf-8", timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            for nome in GERADAS:
                with self.subTest(imagem=nome):
                    self.assertEqual((copia / nome).read_bytes(), (DOCS / nome).read_bytes(),
                                     f"{nome} difere do que o script gera: rode scripts/gerar-diagramas.py docs")

    def test_o_script_nao_deixa_texto_em_portugues_nas_versoes_em_ingles(self):
        with tempfile.TemporaryDirectory() as pasta:
            copia = Path(pasta)
            for nome in FONTES:
                shutil.copy(DOCS / nome, copia / nome)
            r = subprocess.run([sys.executable, str(SCRIPT), str(copia)], capture_output=True, text=True,
                               encoding="utf-8", timeout=120)
            self.assertIn("nenhum", r.stdout)

    def test_um_texto_novo_sem_traducao_e_denunciado(self):
        with tempfile.TemporaryDirectory() as pasta:
            copia = Path(pasta)
            for nome in FONTES:
                shutil.copy(DOCS / nome, copia / nome)
            fonte = copia / "fluxo-envio.svg"
            texto = fonte.read_text(encoding="utf-8")
            fonte.write_text(texto.replace("Agente pede", "Agente pede com a\u00e7\u00e3o nova"), encoding="utf-8", newline="")
            r = subprocess.run([sys.executable, str(SCRIPT), str(copia)], capture_output=True, text=True,
                               encoding="utf-8", timeout=120)
            self.assertNotIn("sobraram nas versoes em ingles: nenhum", r.stdout)


class TesteImagensValidas(unittest.TestCase):
    def test_todas_sao_xml_valido_com_titulo_descricao_e_idioma(self):
        for nome in TODAS:
            texto = (DOCS / nome).read_text(encoding="utf-8")
            with self.subTest(imagem=nome):
                xml.dom.minidom.parseString(texto.encode("utf-8"))
                self.assertIn('<title id="t">', texto)
                self.assertIn('<desc id="d">', texto)
                self.assertIn('role="img"', texto)

    def test_tema_claro_e_escuro_estao_definidos(self):
        for nome in TODAS:
            texto = (DOCS / nome).read_text(encoding="utf-8")
            with self.subTest(imagem=nome):
                self.assertIn("prefers-color-scheme: dark", texto)
                self.assertIn("--bg:#F6F8F7", texto)
                self.assertIn("--bg:#0F1B22", texto)

    def test_o_corpo_so_usa_cores_da_paleta_por_variavel(self):
        for nome in TODAS:
            corpo = (DOCS / nome).read_text(encoding="utf-8").split("</defs>", 1)[1]
            with self.subTest(imagem=nome):
                self.assertEqual(re.findall(r"#[0-9A-Fa-f]{3,8}\b", corpo), [])

    def test_nenhuma_imagem_tem_emoji_ou_simbolo_decorativo(self):
        for nome in TODAS:
            texto = (DOCS / nome).read_text(encoding="utf-8")
            achados = [c for c in texto if 0x1F000 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF or 0x2B00 <= ord(c) <= 0x2BFF]
            with self.subTest(imagem=nome):
                self.assertEqual(achados, [])

    def test_a_animacao_so_existe_no_fluxo_de_envio_animado(self):
        for nome in TODAS:
            with self.subTest(imagem=nome):
                tem = "<animateMotion" in (DOCS / nome).read_text(encoding="utf-8")
                self.assertEqual(tem, nome in ("fluxo-envio-animado.svg", "send-flow-animated.svg"))

    def test_o_diagrama_de_isolamento_diz_que_o_agente_nao_alcanca_a_bridge(self):
        self.assertIn("sem rota", (DOCS / "isolamento-containers.svg").read_text(encoding="utf-8"))
        self.assertIn("no route", (DOCS / "container-isolation.svg").read_text(encoding="utf-8"))

    def test_os_modos_aparecem_nas_imagens_de_modos_de_envio(self):
        for nome in ("send-modes.svg", "modos-de-envio.svg"):
            texto = (DOCS / nome).read_text(encoding="utf-8")
            for modo in ("read-only", "two-step", "hook"):
                with self.subTest(imagem=nome, modo=modo):
                    self.assertIn(modo, texto)

    def test_os_textos_das_caixas_do_fluxo_de_instalacao_cabem(self):
        # as caixas tem 188 px: titulo em 13,5 px negrito (cerca de 7,3 px por letra) e subtitulo em 11,5 px
        for nome in ("install-flow.svg", "fluxo-instalacao.svg"):
            texto = (DOCS / nome).read_text(encoding="utf-8")
            titulos = re.findall(r'class="t1" text-anchor="middle" style="font-size:13.5px">([^<]+)<', texto)
            legendas = re.findall(r'class="t3" text-anchor="middle">([^<]+)<', texto)
            with self.subTest(imagem=nome):
                self.assertEqual(len(titulos), 9)
                for titulo in titulos:
                    self.assertLessEqual(len(titulo), 28, titulo)
                for legenda in legendas:
                    self.assertLessEqual(len(legenda), 34, legenda)  # medido na imagem renderizada

    def test_os_textos_das_caixas_dos_outros_fluxos_cabem(self):
        for nome in ("send-modes.svg", "modos-de-envio.svg"):
            texto = (DOCS / nome).read_text(encoding="utf-8")
            for valor in re.findall(r'text-anchor="start" style="fill:var\(--text\)">([^<]+)<', texto):
                with self.subTest(imagem=nome, valor=valor):
                    self.assertLessEqual(len(valor), 34)  # coluna de 320 px menos o rotulo

    def test_o_fluxo_de_instalacao_tem_os_tres_pontos_de_parada_da_pessoa(self):
        for nome, trechos in (("install-flow.svg", ("You paste the prompt", "You scan the QR", "You choose the send mode")),
                              ("fluxo-instalacao.svg", ("Voc\u00ea cola o prompt", "Voc\u00ea l\u00ea o QR", "Voc\u00ea escolhe o envio"))):
            texto = (DOCS / nome).read_text(encoding="utf-8")
            for trecho in trechos:
                with self.subTest(imagem=nome, trecho=trecho):
                    self.assertIn(trecho, texto)


if __name__ == "__main__":
    unittest.main()