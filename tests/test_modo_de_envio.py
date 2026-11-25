"""Testes dos modos de envio do servidor MCP (server/seguranca.py, server/confirm.py, server/main.py).

O servidor e a protecao para agentes que nao tem o guarda do Claude Code. Estes testes travam:
- o padrao e somente leitura, e valor desconhecido cai nele;
- no two-step, o agente so cria rascunho e nunca envia;
- quem envia e o comando confirm.py, que exige terminal interativo e a palavra digitada.

Os testes que carregam o servidor inteiro precisam do pacote mcp e sao pulados sem ele.
"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SERVER = RAIZ / "server"
sys.path.insert(0, str(SERVER))

import seguranca  # noqa: E402
import confirm  # noqa: E402

TEM_MCP = importlib.util.find_spec("mcp") is not None


def ambiente(modo=None, pasta=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("WHATSAPP_")}
    env["PYTHONIOENCODING"] = "utf-8"  # os subprocessos imprimem acentos; o teste le como UTF-8
    # Seguranca do teste: se uma trava quebrar, nenhum envio pode chegar a bridge de verdade.
    # A porta 9 recusa a conexao, entao qualquer envio acidental falha sem consequencia.
    env["WHATSAPP_API_BASE_URL"] = "http://127.0.0.1:9/api"
    if modo is not None:
        env["WHATSAPP_SEND_MODE"] = modo
    if pasta is not None:
        env["WHATSAPP_PENDING_DIR"] = str(pasta)
    return env


class TesteModoDeEnvio(unittest.TestCase):
    def test_padrao_e_somente_leitura(self):
        self.assertEqual(seguranca.modo_de_envio({}), "read-only")
        self.assertEqual(seguranca.MODO_PADRAO, "read-only")

    def test_valor_desconhecido_ou_vazio_cai_no_mais_seguro(self):
        for valor in ("", "   ", "tudo", "send", "true", "1", "enabled", "hook two-step", "read only"):
            with self.subTest(valor=valor):
                self.assertEqual(seguranca.modo_de_envio({"WHATSAPP_SEND_MODE": valor}), "read-only")

    def test_aceita_os_tres_modos_com_variacao_de_escrita(self):
        casos = {"read-only": "read-only", "READ_ONLY": "read-only", "two-step": "two-step",
                 "Two_Step": "two-step", " hook ": "hook", "HOOK": "hook"}
        for valor, esperado in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(seguranca.modo_de_envio({"WHATSAPP_SEND_MODE": valor}), esperado)

    def test_o_plugin_do_claude_code_liga_o_modo_hook(self):
        dados = json.loads((RAIZ / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(dados["mcpServers"]["whatsapp"]["env"]["WHATSAPP_SEND_MODE"], "hook")


class TesteRascunhos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "pending"
        self.arquivo = Path(self.tmp.name) / "foto.jpg"
        self.arquivo.write_bytes(b"x")

    def criar(self, **extra):
        dados = dict(tipo="message", destinatario="5511999999999", mensagem="oi", pasta=self.pasta)
        dados.update(extra)
        return seguranca.criar_pendente(**dados)

    def test_cria_rascunho_com_id_curto_valido_e_validade(self):
        registro = self.criar(agora=1000, validade=600)
        self.assertRegex(registro["id"], r"^[0-9a-f]{8}$")
        self.assertEqual((registro["criado_em"], registro["expira_em"]), (1000, 1600))
        self.assertEqual(seguranca.estado_do_pendente(registro["id"], self.pasta, agora=1001), "pending")

    def test_rascunho_de_arquivo_e_de_audio(self):
        for tipo in ("file", "audio"):
            with self.subTest(tipo=tipo):
                registro = self.criar(tipo=tipo, mensagem=None, arquivo=str(self.arquivo))
                self.assertEqual(registro["arquivo"], str(self.arquivo))
                self.assertIsNone(registro["mensagem"])

    def test_recusa_pedido_invalido(self):
        invalidos = [
            dict(destinatario=""), dict(destinatario="   "), dict(mensagem=""), dict(mensagem="   "),
            dict(mensagem="a" * (seguranca.TAMANHO_MAXIMO_DA_MENSAGEM + 1)), dict(tipo="outro"),
            dict(tipo="file", mensagem=None, arquivo="relativo/foto.jpg"),
            dict(tipo="file", mensagem=None, arquivo=str(Path(self.tmp.name) / "nao-existe.jpg")),
            dict(tipo="audio", mensagem=None, arquivo=""),
        ]
        for extra in invalidos:
            with self.subTest(extra=str(extra)[:50]):
                with self.assertRaises(seguranca.ErroDeRascunho):
                    self.criar(**extra)
        self.assertEqual(seguranca.listar_pendentes(self.pasta), [])

    def test_rascunho_expirado_some_e_vira_expired(self):
        registro = self.criar(agora=1000, validade=60)
        self.assertIsNone(seguranca.carregar_pendente(registro["id"], self.pasta, agora=1061))
        self.assertEqual(seguranca.estado_do_pendente(registro["id"], self.pasta, agora=1062), "expired")

    def test_limite_de_rascunhos_esperando(self):
        for _ in range(seguranca.MAXIMO_DE_PENDENTES):
            self.criar()
        with self.assertRaises(seguranca.ErroDeRascunho):
            self.criar()

    def test_rascunho_expirado_nao_conta_no_limite(self):
        for _ in range(seguranca.MAXIMO_DE_PENDENTES):
            self.criar(agora=1000, validade=10)
        self.criar(agora=2000)

    def test_identificador_fora_do_formato_e_recusado(self):
        for id_ in ("../fora", "..\\fora", "abc", "ABCDEFGH", "zzzzzzzz", "a1b2c3d4/../x", "", None, "a1b2c3d4e5"):
            with self.subTest(id_=id_):
                self.assertEqual(seguranca.estado_do_pendente(id_, self.pasta), "unknown")
                with self.assertRaises(seguranca.ErroDeRascunho):
                    seguranca.carregar_pendente(id_, self.pasta)

    def test_marcador_nao_guarda_o_texto(self):
        registro = self.criar(mensagem="texto confidencial")
        seguranca.marcar(self.pasta, registro["id"], "sent")
        for arquivo in self.pasta.iterdir():
            self.assertNotIn("confidencial", arquivo.read_text(encoding="utf-8"))
        self.assertEqual(seguranca.estado_do_pendente(registro["id"], self.pasta), "sent")

    def test_validade_configuravel_em_minutos(self):
        self.assertEqual(seguranca.validade_em_segundos({"WHATSAPP_PENDING_TTL_MINUTES": "5"}), 300)
        for lixo in ("", "0", "-3", "abc"):
            with self.subTest(lixo=lixo):
                self.assertEqual(seguranca.validade_em_segundos({"WHATSAPP_PENDING_TTL_MINUTES": lixo}),
                                 seguranca.VALIDADE_PADRAO_SEGUNDOS)


class TesteConfirmacaoNoTerminal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "pending"
        self.registro = seguranca.criar_pendente("message", "5511999999999", mensagem="oi, tudo bem?", pasta=self.pasta)
        self.id = self.registro["id"]
        self.enviados = []

    def enviar(self, registro):
        self.enviados.append(registro["id"])
        return True, "enviado"

    def test_envia_so_depois_da_confirmacao_e_marca_como_enviado(self):
        enviado, _ = confirm.enviar_pendente(self.id, lambda r: True, self.enviar, self.pasta)
        self.assertTrue(enviado)
        self.assertEqual(self.enviados, [self.id])
        self.assertEqual(seguranca.estado_do_pendente(self.id, self.pasta), "sent")

    def test_sem_confirmacao_nao_envia_e_o_rascunho_continua(self):
        enviado, texto = confirm.enviar_pendente(self.id, lambda r: False, self.enviar, self.pasta)
        self.assertFalse(enviado)
        self.assertEqual(self.enviados, [])
        self.assertEqual(seguranca.estado_do_pendente(self.id, self.pasta), "pending")
        self.assertIn("Nada foi enviado", texto)

    def test_o_envio_nao_acontece_duas_vezes(self):
        confirm.enviar_pendente(self.id, lambda r: True, self.enviar, self.pasta)
        enviado, _ = confirm.enviar_pendente(self.id, lambda r: True, self.enviar, self.pasta)
        self.assertFalse(enviado)
        self.assertEqual(self.enviados, [self.id])

    def test_se_o_envio_falhar_o_rascunho_continua(self):
        enviado, texto = confirm.enviar_pendente(self.id, lambda r: True, lambda r: (False, "bridge fora"), self.pasta)
        self.assertFalse(enviado)
        self.assertIn("bridge fora", texto)
        self.assertEqual(seguranca.estado_do_pendente(self.id, self.pasta), "pending")

    def test_rascunho_expirado_nao_envia(self):
        enviado, _ = confirm.enviar_pendente(self.id, lambda r: True, self.enviar, self.pasta, agora=self.registro["expira_em"] + 1)
        self.assertFalse(enviado)
        self.assertEqual(self.enviados, [])

    def test_identificador_invalido_nao_envia(self):
        for id_ in ("../x", "naoexiste", "00000000"):
            with self.subTest(id_=id_):
                enviado, _ = confirm.enviar_pendente(id_, lambda r: True, self.enviar, self.pasta)
                self.assertFalse(enviado)
        self.assertEqual(self.enviados, [])

    def test_a_pergunta_so_aceita_a_palavra_exata(self):
        respostas = {"enviar": True, "ENVIAR": True, "  enviar ": True, "": False, "sim": False, "s": False,
                     "enviar agora": False, "nao": False, "ok": False, "y": False}
        for resposta, esperado in respostas.items():
            with self.subTest(resposta=resposta):
                with unittest.mock.patch("builtins.input", return_value=resposta),                         contextlib.redirect_stdout(io.StringIO()):
                    self.assertIs(confirm.confirmar_no_terminal(self.registro), esperado)

    def test_o_comando_recusa_rodar_sem_terminal_interativo(self):
        # subprocess com pipes nao e terminal: o comando precisa recusar e nada pode ser enviado
        resultado = subprocess.run(
            [sys.executable, str(SERVER / "confirm.py"), "send", self.id],
            input="enviar\n", capture_output=True, text=True, encoding="utf-8",
            env=ambiente(pasta=self.pasta), timeout=30,
        )
        self.assertEqual(resultado.returncode, 2, resultado.stdout + resultado.stderr)
        self.assertIn("terminal interativo", resultado.stdout)
        self.assertEqual(seguranca.estado_do_pendente(self.id, self.pasta), "pending")

    def test_list_show_e_discard_pelo_comando(self):
        env = ambiente(pasta=self.pasta)

        def rodar(*args):
            return subprocess.run([sys.executable, str(SERVER / "confirm.py"), *args], capture_output=True,
                                  text=True, encoding="utf-8", env=env, timeout=30)

        lista = rodar("list")
        self.assertEqual(lista.returncode, 0)
        self.assertIn(self.id, lista.stdout)
        mostrar = rodar("show", self.id)
        self.assertEqual(mostrar.returncode, 0)
        self.assertIn("oi, tudo bem?", mostrar.stdout)
        self.assertIn("5511999999999", mostrar.stdout)
        descartar = rodar("discard", self.id)
        self.assertEqual(descartar.returncode, 0)
        self.assertEqual(seguranca.estado_do_pendente(self.id, self.pasta), "discarded")
        self.assertEqual(rodar("show", self.id).returncode, 1)

    def test_discard_all_e_comando_desconhecido(self):
        seguranca.criar_pendente("message", "5511999999999", mensagem="dois", pasta=self.pasta)
        env = ambiente(pasta=self.pasta)
        tudo = subprocess.run([sys.executable, str(SERVER / "confirm.py"), "discard", "--all"], capture_output=True,
                              text=True, encoding="utf-8", env=env, timeout=30)
        self.assertEqual(tudo.returncode, 0)
        self.assertEqual(seguranca.listar_pendentes(self.pasta), [])
        estranho = subprocess.run([sys.executable, str(SERVER / "confirm.py"), "enviar-tudo"], capture_output=True,
                                  text=True, encoding="utf-8", env=env, timeout=30)
        self.assertEqual(estranho.returncode, 1)

    def test_a_descricao_mostra_texto_inteiro_e_destinatario(self):
        texto = confirm.descrever(self.registro, nome="Fulano", agora=self.registro["criado_em"] + 120)
        for trecho in ("oi, tudo bem?", "5511999999999", "Fulano", self.id, "Criado há 2 min"):
            self.assertIn(trecho, texto)


class TesteEnvioEmPartes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "pending"
        self.partes = [
            seguranca.criar_pendente("message", "5511999999999", mensagem=texto, pasta=self.pasta)
            for texto in ("oi", "tudo bem por ai", "te ligo mais tarde")
        ]
        self.ids = [p["id"] for p in self.partes]
        self.enviados = []
        self.pausas = []

    def enviar(self, registro):
        self.enviados.append(registro["mensagem"])
        return True, "enviado"

    def rodar(self, ids=None, confirmar=lambda registros: True, enviar=None):
        return confirm.enviar_varios(ids or self.ids, confirmar, enviar or self.enviar, self.pasta,
                                     pausa=1.5, dormir=self.pausas.append)

    def test_envia_as_partes_na_ordem_com_pausa_entre_elas(self):
        enviado, texto = self.rodar()
        self.assertTrue(enviado)
        self.assertEqual(self.enviados, ["oi", "tudo bem por ai", "te ligo mais tarde"])
        self.assertEqual(self.pausas, [1.5, 1.5])
        for id_ in self.ids:
            self.assertEqual(seguranca.estado_do_pendente(id_, self.pasta), "sent")
        self.assertIn("3 mensagem", texto)

    def test_pede_uma_unica_confirmacao_e_mostra_todas_as_partes(self):
        vistas = []
        self.rodar(confirmar=lambda registros: vistas.append([r["mensagem"] for r in registros]) or True)
        self.assertEqual(vistas, [["oi", "tudo bem por ai", "te ligo mais tarde"]])

    def test_sem_confirmacao_nada_e_enviado(self):
        enviado, _ = self.rodar(confirmar=lambda registros: False)
        self.assertFalse(enviado)
        self.assertEqual(self.enviados, [])
        for id_ in self.ids:
            self.assertEqual(seguranca.estado_do_pendente(id_, self.pasta), "pending")

    def test_uma_parte_invalida_cancela_o_lote_inteiro(self):
        for ids in (self.ids + ["00000000"], [self.ids[0], "../x"]):
            with self.subTest(ids=ids):
                enviado, texto = self.rodar(ids=ids)
                self.assertFalse(enviado)
                self.assertIn("Nada foi enviado", texto)
        self.assertEqual(self.enviados, [])

    def test_destinatarios_diferentes_no_mesmo_lote_sao_recusados(self):
        outra = seguranca.criar_pendente("message", "5511988888888", mensagem="oi, outra pessoa", pasta=self.pasta)
        enviado, texto = self.rodar(ids=self.ids + [outra["id"]])
        self.assertFalse(enviado)
        self.assertIn("destinatários diferentes", texto)
        self.assertEqual(self.enviados, [])

    def test_se_uma_parte_falhar_as_seguintes_nao_saem(self):
        def falha_na_segunda(registro):
            if registro["mensagem"] == "tudo bem por ai":
                return False, "bridge fora"
            return self.enviar(registro)

        enviado, texto = self.rodar(enviar=falha_na_segunda)
        self.assertFalse(enviado)
        self.assertEqual(self.enviados, ["oi"])
        self.assertIn("parte 2", texto)
        estados = [seguranca.estado_do_pendente(i, self.pasta) for i in self.ids]
        self.assertEqual(estados, ["sent", "pending", "pending"])

    def test_o_comando_com_varios_ids_tambem_recusa_sem_terminal(self):
        resultado = subprocess.run(
            [sys.executable, str(SERVER / "confirm.py"), "send", *self.ids], input="enviar\n",
            capture_output=True, text=True, encoding="utf-8", env=ambiente(pasta=self.pasta), timeout=30,
        )
        self.assertEqual(resultado.returncode, 2)
        self.assertEqual([seguranca.estado_do_pendente(i, self.pasta) for i in self.ids], ["pending"] * 3)


SCRIPT_DE_FERRAMENTAS = """
import asyncio, json
import main
print(json.dumps(sorted(t.name for t in asyncio.run(main.mcp.list_tools()))))
"""

SCRIPT_DE_RASCUNHO = """
import asyncio, json, sys
import whatsapp
def nunca(*a, **k):
    print("ENVIOU"); raise SystemExit(99)
whatsapp.send_message = nunca
whatsapp.send_file = nunca
whatsapp.send_audio_message = nunca
import main
r = asyncio.run(main.mcp.call_tool(sys.argv[1], json.loads(sys.argv[2])))
print("OK")
"""

SCRIPT_DE_CHAMADA_INEXISTENTE = """
import asyncio
import main
try:
    asyncio.run(main.mcp.call_tool("send_message", {"recipient": "5511999999999", "message": "oi"}))
    print("CHAMOU")
except Exception:
    print("FERRAMENTA-AUSENTE")
"""

LEITURA = {"search_contacts", "list_messages", "list_chats", "get_chat", "get_direct_chat_by_contact",
           "get_contact_chats", "get_last_interaction", "get_message_context", "download_media", "transcribe_audio"}
ENVIO = {"send_message", "send_file", "send_audio_message"}


@unittest.skipUnless(TEM_MCP, "pacote mcp nao instalado")
class TesteServidorPorModo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "pending"

    def rodar(self, script, modo, *args):
        return subprocess.run([sys.executable, "-c", script, *args], cwd=SERVER, capture_output=True, text=True,
                              encoding="utf-8", env=ambiente(modo, self.pasta), timeout=60)

    def ferramentas(self, modo):
        resultado = self.rodar(SCRIPT_DE_FERRAMENTAS, modo)
        self.assertEqual(resultado.returncode, 0, resultado.stderr[-400:])
        return set(json.loads(resultado.stdout.strip().splitlines()[-1]))

    def test_somente_leitura_e_o_padrao_e_nao_expoe_nenhum_envio(self):
        for modo in (None, "read-only", "lixo"):
            with self.subTest(modo=modo):
                nomes = self.ferramentas(modo)
                self.assertEqual(nomes, LEITURA)
                self.assertEqual(nomes & ENVIO, set())

    def test_chamar_envio_no_somente_leitura_falha(self):
        resultado = self.rodar(SCRIPT_DE_CHAMADA_INEXISTENTE, "read-only")
        self.assertIn("FERRAMENTA-AUSENTE", resultado.stdout)

    def test_two_step_expoe_envio_como_rascunho_e_a_consulta(self):
        self.assertEqual(self.ferramentas("two-step"), LEITURA | ENVIO | {"check_pending_send"})

    def test_hook_expoe_as_tres_ferramentas_de_envio(self):
        self.assertEqual(self.ferramentas("hook"), LEITURA | ENVIO)

    def test_two_step_nunca_chama_a_bridge(self):
        casos = [
            ("send_message", {"recipient": "5511999999999", "message": "oi"}),
            ("send_file", {"recipient": "5511999999999", "media_path": str(Path(self.tmp.name) / "a.jpg")}),
            ("send_audio_message", {"recipient": "5511999999999", "media_path": str(Path(self.tmp.name) / "a.ogg")}),
        ]
        for nome, args in casos:
            if "media_path" in args:
                Path(args["media_path"]).write_bytes(b"x")
            with self.subTest(ferramenta=nome):
                resultado = self.rodar(SCRIPT_DE_RASCUNHO, "two-step", nome, json.dumps(args))
                self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr[-300:])
                self.assertNotIn("ENVIOU", resultado.stdout)
                self.assertIn("OK", resultado.stdout)
        self.assertEqual(len(list(self.pasta.glob("*.json"))), 3)

    def test_two_step_com_pedido_invalido_nao_cria_rascunho(self):
        resultado = self.rodar(SCRIPT_DE_RASCUNHO, "two-step", "send_message", json.dumps({"recipient": "", "message": "oi"}))
        self.assertEqual(resultado.returncode, 0)
        self.assertEqual(list(self.pasta.glob("*.json")) if self.pasta.exists() else [], [])

    def test_o_comando_de_confirmacao_pode_ser_trocado_para_container(self):
        script = ("import json, main; r = main.send_message_two_step('5511999999999', 'oi'); "
                  "print(json.dumps({'cmd': r['how_to_send'], 'id': r['pending_id']}))")
        padrao = json.loads(self.rodar(script, "two-step").stdout.strip().splitlines()[-1])
        self.assertIn("confirm.py", padrao["cmd"])
        self.assertTrue(padrao["cmd"].endswith("send " + padrao["id"]))
        env = ambiente("two-step", self.pasta)
        env["WHATSAPP_CONFIRM_COMMAND"] = "podman exec -it whatsapp-mcp python confirm.py"
        r = subprocess.run([sys.executable, "-c", script], cwd=SERVER, capture_output=True, text=True,
                           encoding="utf-8", env=env, timeout=60)
        trocado = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(trocado["cmd"], "podman exec -it whatsapp-mcp python confirm.py send " + trocado["id"])

    def test_as_instrucoes_explicam_o_modo_ao_agente(self):
        trechos = {"read-only": "DISABLED", "two-step": "TWO-STEP", "hook": "explicit confirmation"}
        for modo, trecho in trechos.items():
            with self.subTest(modo=modo):
                resultado = self.rodar("import main; print(main.mcp.instructions)", modo)
                self.assertIn(trecho, resultado.stdout)


if __name__ == "__main__":
    unittest.main()
