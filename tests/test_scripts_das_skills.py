"""Testes dos scripts das skills triagem-whatsapp e notas-por-contato, com um banco sintetico.

Nenhum WhatsApp real e usado: nomes, numeros e mensagens do banco sao inventados (fixtures.py).
Rodar: python -m unittest discover -s tests -v
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixtures  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
TRIAGEM = RAIZ / "skills" / "triagem-whatsapp" / "scripts"
NOTAS = RAIZ / "skills" / "notas-por-contato" / "scripts"
SCRIPTS_DE_NOTAS = {"criar_nota.py", "compromissos.py"}


def pasta_do_script(script: str) -> Path:
    return NOTAS if script in SCRIPTS_DE_NOTAS else TRIAGEM


class BaseScripts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = fixtures.criar_banco(Path(self.tmp.name) / "store")
        self.notas = Path(self.tmp.name) / "notas"
        self.notas.mkdir()

    def ambiente(self, env_extra=None) -> dict:
        env = {k: v for k, v in os.environ.items() if not k.startswith("WHATSAPP_")}
        env["PYTHONIOENCODING"] = "utf-8"
        env.update({"WHATSAPP_STORE_DIR": str(self.store), "WHATSAPP_NOTES_DIR": str(self.notas)})
        env.update(env_extra or {})
        return env

    def rodar(self, script: str, *args: str, env_extra=None, scripts_dir=None) -> str:
        pasta = scripts_dir or pasta_do_script(script)
        r = subprocess.run(
            [sys.executable, str(pasta / script), *args],
            capture_output=True, text=True, encoding="utf-8", env=self.ambiente(env_extra), timeout=60,
        )
        self.assertEqual(r.returncode, 0, f"{script} falhou: {r.stderr}")
        return r.stdout


class TestResumoEBusca(BaseScripts):
    def test_resumo_junta_os_dois_jids_e_usa_o_nome_da_agenda(self):
        saida = self.rodar("resumo_contato.py", fixtures.MARIA_PN)
        self.assertIn("Maria Silva", saida)
        self.assertIn("oi, tudo bem?", saida)  # mensagem do @s.whatsapp.net
        self.assertIn("consegue me mandar o relatorio", saida)  # mensagem do @lid

    def test_resumo_pelo_lid_tambem_acha_o_historico_antigo(self):
        saida = self.rodar("resumo_contato.py", fixtures.MARIA_LID)
        self.assertIn("oi, tudo bem?", saida)

    def test_buscar_junta_jids_da_mesma_pessoa(self):
        saida = self.rodar("buscar_contato.py", "maria")
        self.assertEqual(saida.count("[1]"), 1)
        self.assertNotIn("[2]", saida)
        self.assertIn(fixtures.MARIA_PN, saida)
        self.assertIn(fixtures.MARIA_LID, saida)

    def test_buscar_avisa_quando_ha_pessoas_com_nome_parecido(self):
        saida = self.rodar("buscar_contato.py", "pedro")
        self.assertIn("[2]", saida)
        self.assertIn("Confirmar com o usuario", saida)

    def test_buscar_sem_resultado(self):
        self.assertIn("Nenhum contato encontrado", self.rodar("buscar_contato.py", "zzz"))


class TestPendentes(BaseScripts):
    def test_lista_so_conversas_individuais_com_ultima_mensagem_do_outro(self):
        saida = self.rodar("listar_pendentes.py")
        self.assertIn("Maria Silva", saida)
        self.assertIn("consegue me mandar o relatorio", saida)
        self.assertNotIn("Joao Souza", saida)  # a ultima mensagem foi do usuario
        self.assertNotIn("PROMOCAO", saida)  # grupo ignorado

    def test_mesma_pessoa_em_dois_jids_aparece_uma_vez(self):
        saida = self.rodar("listar_pendentes.py")
        self.assertEqual(saida.count("Maria Silva"), 1)

    def test_nao_avisa_de_dados_antigos_quando_o_banco_esta_em_dia(self):
        self.assertNotIn("AVISO", self.rodar("listar_pendentes.py"))


class TestNotasECompromissos(BaseScripts):
    def test_criar_nota_registra_decisao_compromisso_e_conclui(self):
        saida = self.rodar("criar_nota.py", fixtures.MARIA_LID, "--relacao", "colega de trabalho")
        self.assertIn("criado", saida)
        arquivo = self.notas / "maria-silva.md"
        self.assertTrue(arquivo.exists())
        texto = arquivo.read_text(encoding="utf-8")
        self.assertIn(fixtures.MARIA_LID, texto)
        self.assertIn(fixtures.MARIA_PN, texto)  # os dois jids ficam na nota
        self.assertIn("colega de trabalho", texto)

        self.rodar("criar_nota.py", fixtures.MARIA_PN, "--decisao", "sugeri X, confirmou")
        self.rodar("criar_nota.py", fixtures.MARIA_PN, "--compromisso", "enviar o relatorio")
        texto = arquivo.read_text(encoding="utf-8")
        self.assertIn("sugeri X, confirmou", texto)
        self.assertIn("- [ ] ", texto)

        self.assertIn("enviar o relatorio", self.rodar("compromissos.py"))

        self.rodar("criar_nota.py", fixtures.MARIA_PN, "--concluir", "enviar o relatorio")
        self.assertIn("- [x] ", arquivo.read_text(encoding="utf-8"))
        self.assertIn("Nenhum compromisso aberto", self.rodar("compromissos.py"))

    def test_criar_nota_nao_duplica_a_nota_do_mesmo_contato(self):
        self.rodar("criar_nota.py", fixtures.MARIA_LID)
        saida = self.rodar("criar_nota.py", fixtures.MARIA_PN)  # outro jid da mesma pessoa
        self.assertIn("ja existia", saida)
        self.assertEqual(len(list(self.notas.glob("*.md"))), 1)

    def test_historico_de_decisoes_guarda_so_as_ultimas_10(self):
        self.rodar("criar_nota.py", fixtures.JOAO_PN)
        for i in range(13):
            self.rodar("criar_nota.py", fixtures.JOAO_PN, "--decisao", f"decisao numero {i}")
        texto = (self.notas / "joao-souza.md").read_text(encoding="utf-8")
        self.assertEqual(texto.count("decisao numero"), 10)
        self.assertIn("decisao numero 12", texto)
        self.assertNotIn("decisao numero 0\n", texto)

    def test_buscar_mostra_a_nota_quando_existe(self):
        self.rodar("criar_nota.py", fixtures.MARIA_LID)
        self.assertIn("nota: maria-silva.md", self.rodar("buscar_contato.py", "maria"))


class TestBacklog(BaseScripts):
    def test_banco_recente_nao_espera(self):
        self.assertIn("Banco em dia", self.rodar("aguardar_backlog.py", "--max", "5"))


class TestAprofundarHistorico(BaseScripts):
    def test_avisa_quando_a_bridge_esta_fora_do_ar(self):
        with socket.socket() as s:  # acha uma porta livre e a deixa fechada
            s.bind(("127.0.0.1", 0))
            porta = s.getsockname()[1]
        saida = self.rodar(
            "aprofundar_historico.py", fixtures.MARIA_PN, "--rodadas", "1", "--espera", "1",
            env_extra={"WHATSAPP_BRIDGE_PORT": str(porta)},
        )
        self.assertIn("Nao deu para pedir o historico", saida)


class TestResumoSessao(BaseScripts):
    def test_conta_so_mensagens_recebidas_de_conversas_individuais(self):
        saida = self.rodar("resumo_sessao.py")
        self.assertIn("mensagem(ns) nova(s)", saida)
        self.assertNotIn("@g.us", saida)

    def test_retomar_a_sessao_reaproveita_a_janela(self):
        primeira = self.rodar("resumo_sessao.py")
        self.assertEqual(primeira, self.rodar("resumo_sessao.py"))

    def test_saida_json_serve_de_contexto_para_o_hook(self):
        import json

        dados = json.loads(self.rodar("resumo_sessao.py", "--json"))
        contexto = dados["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(contexto.startswith("WhatsApp:"))
        self.assertEqual(dados["systemMessage"], contexto)


class TestSkillsSozinhas(BaseScripts):
    def test_cada_skill_copiada_sozinha_funciona(self):
        """Quem instala uma skill isolada (sem o resto do plugin) tem que conseguir usar os scripts."""
        copia = Path(self.tmp.name) / "so-a-triagem"
        shutil.copytree(TRIAGEM.parent, copia, ignore=shutil.ignore_patterns("__pycache__"))
        saida = self.rodar("buscar_contato.py", "maria", scripts_dir=copia / "scripts")
        self.assertIn("Maria Silva", saida)
        copia_notas = Path(self.tmp.name) / "so-as-notas"
        shutil.copytree(NOTAS.parent, copia_notas, ignore=shutil.ignore_patterns("__pycache__"))
        self.assertIn("criado", self.rodar("criar_nota.py", fixtures.MARIA_PN, scripts_dir=copia_notas / "scripts"))

    def test_as_duas_copias_do_modulo_comum_sao_identicas(self):
        self.assertEqual((TRIAGEM / "_comum.py").read_bytes(), (NOTAS / "_comum.py").read_bytes())

    def test_sem_variaveis_os_dados_ficam_dentro_da_pasta_data_do_plugin(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("WHATSAPP_")}
        r = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, %r); import _comum as c; print(c.pasta_store()); print(c.pasta_notas())" % str(TRIAGEM)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
        )
        store, notas = r.stdout.strip().splitlines()
        self.assertEqual(Path(store), RAIZ / "data" / "store")
        self.assertEqual(Path(notas), RAIZ / "data" / "notas")


if __name__ == "__main__":
    unittest.main()
