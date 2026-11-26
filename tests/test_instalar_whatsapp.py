"""Testes da skill instalar-whatsapp e do prompt de instalacao do README.

A skill e o texto que um agente segue para instalar o plugin sozinho. Estes testes travam o que a
torna segura: pontos em que o agente precisa parar, nada de senha impressa, nada de mensagem de
teste, e so citar arquivos que existem.
"""

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SKILL = RAIZ / "skills" / "instalar-whatsapp" / "SKILL.md"
README = RAIZ / "README.md"


def blocos_de_codigo(texto: str) -> list:
    return re.findall(r"```[a-z]*\n(.*?)```", texto, re.S)


README_EN = RAIZ / "README.md"
README_PT = RAIZ / "README.pt-BR.md"
SECAO = {README_EN: "## Install with an agent's help", README_PT: "## Instalar com a ajuda de um agente"}


def secao_de_instalacao(readme: Path) -> str:
    return readme.read_text(encoding="utf-8").split(SECAO[readme], 1)[1].split(chr(10) + "## ", 1)[0]


def prompt_do_readme(readme: Path = README_PT) -> str:
    return re.search(r"```" + chr(10) + r"(.*?)```", secao_de_instalacao(readme), re.S).group(1).strip()


class TesteSkillDeInstalacao(unittest.TestCase):
    def setUp(self):
        self.texto = SKILL.read_text(encoding="utf-8")

    def test_ha_pontos_de_parada_para_o_que_so_a_pessoa_faz(self):
        paradas = self.texto.count("PARE")
        self.assertGreaterEqual(paradas, 5, "esperava paradas na escolha do caminho, no QR, no envio e na VPS")
        for assunto in ("QR", "Aparelhos conectados"):
            self.assertIn(assunto, self.texto)

    def test_proibe_enviar_mensagem_de_teste(self):
        self.assertIn("Nunca envie mensagem de teste", self.texto)
        self.assertIn("`list_chats` com `limit` 1", self.texto)

    def test_o_envio_fica_desligado_ate_a_pessoa_decidir(self):
        self.assertIn("read-only", self.texto)
        self.assertIn("Não mude o modo sem a resposta dela", self.texto)
        self.assertIn("**Não use `hook`** fora do Claude Code", self.texto)

    def test_pergunta_antes_de_instalar_programas(self):
        self.assertIn("Pergunte antes de instalar qualquer programa", self.texto)

    def test_nenhum_comando_imprime_a_senha(self):
        for bloco in blocos_de_codigo(self.texto):
            if "token_urlsafe" in bloco:
                self.assertRegex(bloco, r">\s*container/\.env|\.write|write_text",
                                 "o comando que gera a senha precisa gravar direto no arquivo")
        self.assertNotRegex(self.texto, r"(?m)^\s*python -c \"import secrets; print\(secrets\.token_urlsafe\(32\)\)\"\s*$")

    def test_o_arquivo_com_a_senha_nao_e_versionado(self):
        self.assertIn("git check-ignore container/.env", self.texto)

    def test_nao_manda_adicionar_tudo_nem_enviar_dados(self):
        self.assertIn("Nunca use `git add .`", self.texto)
        self.assertNotRegex(self.texto, r"(?m)^\s*git add \.\s*$")

    def test_nao_inventa_configuracao_de_agente(self):
        self.assertIn("Não invente configuração de agente", self.texto)
        self.assertIn("docs/agentes.md", self.texto)

    def test_avisa_que_agente_que_conhece_a_senha_pode_usa_la(self):
        self.assertIn("um agente que conhece a senha consegue usá-la", self.texto)

    def test_nos_caminhos_nativos_nao_manda_usar_senha(self):
        passo_b = self.texto.split("## Passo 3B")[1].split("## Passo 3C")[0]
        self.assertIn("Senha da bridge: não use neste caminho", passo_b)

    def test_todo_arquivo_citado_existe(self):
        citados = set(re.findall(r"`((?:docs|skills|container|commands|bridge|server|scripts)/[\w./-]+\.(?:md|py|yaml|json))`", self.texto))
        citados |= set(re.findall(r"\((?:\.\./)*((?:docs|skills)/[\w./-]+\.md)\)", self.texto))
        self.assertGreaterEqual(len(citados), 4)  # controle: a busca esta achando as citacoes
        for caminho in sorted(citados):
            with self.subTest(arquivo=caminho):
                self.assertTrue((RAIZ / caminho).is_file(), f"a skill cita {caminho}, que nao existe")

    def test_pede_confirmacao_antes_de_editar_a_configuracao_do_agente(self):
        self.assertIn("Antes de editar a configuração do agente", self.texto)
        self.assertIn("peça o \"sim\" antes de editar a configuração", self.texto)

    def test_pergunta_antes_de_escolher_o_caminho_b_com_agente_com_terminal(self):
        self.assertIn("PARE e pergunte antes", self.texto)

    def test_agente_generico_manda_conferir_na_documentacao_dele(self):
        self.assertIn("peça que ela confira, na documentação do agente", self.texto)

    def test_avisa_que_fora_do_claude_code_a_bridge_sobe_a_mao(self):
        self.assertIn("só o Claude Code liga a bridge sozinho", self.texto)

    def test_nao_fecha_processo_de_outra_bridge_sozinho(self):
        self.assertIn("Não feche o processo por conta própria", self.texto)

    def test_os_comandos_de_compilar_nao_estao_no_mesmo_bloco(self):
        for bloco in blocos_de_codigo(self.texto):
            self.assertFalse("main.exe" in bloco and "whatsapp-bridge ." in bloco, bloco)

    def test_o_mais_simples_no_caminho_b_e_nao_definir_o_modo(self):
        self.assertIn("O mais simples é não definir `WHATSAPP_SEND_MODE`", self.texto)

    def test_a_secao_por_que_explica_os_pontos_principais(self):
        porque = self.texto.split("## Por que")[1]
        for assunto in ("Diagnóstico", "PARE", "Envio desligado", "Senha", "Caminho C"):
            self.assertIn(assunto, porque)

    def test_os_tres_caminhos_estao_na_tabela_de_decisao(self):
        escolha = self.texto.split("## Passo 1")[1].split("## Passo 2")[0]
        for caminho in ("**A**", "**B**", "**C**", "OpenBot", "Claude Code"):
            self.assertIn(caminho, escolha)

    def test_o_comando_de_diagnostico_citado_existe(self):
        self.assertIn("skills/instalar-whatsapp/scripts/verificar_instalacao.py", self.texto)
        self.assertTrue((RAIZ / "skills" / "instalar-whatsapp" / "scripts" / "verificar_instalacao.py").is_file())

    def passo(self, numero, proximo):
        return self.texto.split(f"## Passo {numero}")[1].split(f"## Passo {proximo}")[0]

    def test_todas_as_escolhas_vao_em_uma_mensagem_so(self):
        passo1 = self.passo(1, 2)
        self.assertIn("uma mensagem só", passo1)
        for escolha in ("**Caminho**", "**Transcrição de áudio**", "**Instalar as skills no agente**"):
            self.assertIn(escolha, passo1)
        self.assertIn("com a sua recomendação", passo1)

    def test_agente_dentro_de_container_recebe_um_comando_so_para_a_vps(self):
        self.assertIn("dentro de um container sem acesso ao servidor", self.passo(1, 2))
        passo3c = self.passo("3C", 4)
        self.assertIn("container/instalar-vps.sh", passo3c)
        self.assertIn("instalar-vps.sh servidor", passo3c)
        self.assertIn("só depois de perguntar e fazer cópia", passo3c)
        self.assertTrue((RAIZ / "container" / "instalar-vps.sh").is_file())

    def test_tenta_a_bridge_pronta_antes_de_compilar(self):
        passo4 = self.passo(4, 5)
        self.assertIn("baixar_bridge.py", passo4)
        self.assertLess(passo4.index("baixar_bridge.py"), passo4.index("go build"))
        self.assertIn("SHA-256", passo4)
        self.assertIn("**pare**, não use o arquivo", passo4)
        self.assertTrue((RAIZ / "skills" / "instalar-whatsapp" / "scripts" / "baixar_bridge.py").is_file())

    def test_go_e_compilador_nao_sao_pedidos_antes_de_saber_que_precisa(self):
        passo2 = self.passo(2, "3A")
        self.assertIn("Go e compilador C não são necessários", passo2)
        self.assertNotIn("winget install GoLang.Go", passo2)

    def test_qr_vai_como_imagem_renovada_sozinha(self):
        passo5 = self.passo(5, 6)
        self.assertIn("data/store/qr.png", passo5)
        self.assertIn("renova sozinha", passo5)
        self.assertIn("anexe a imagem", passo5)
        self.assertIn("a bridge apaga o arquivo", passo5)

    def test_audio_exige_o_extra_no_comando_do_servidor(self):
        passo3b = self.passo("3B", "3C")
        self.assertIn("run --extra audio main.py", passo3b)
        self.assertIn("desinstala o Whisper", passo3b)

    def test_secao_de_atualizar_verifica_pergunta_e_nunca_forca(self):
        secao = self.texto.split("## Atualizar (sem reinstalar)")[1].split("## Se algo der errado")[0]
        self.assertIn("atualizar_plugin.py", secao)
        self.assertIn("Verifique, sem alterar nada", secao)
        self.assertIn("pergunte se pode atualizar", secao)
        self.assertIn("--aplicar", secao)
        self.assertIn("não force", secao)
        self.assertIn("nunca** toca em `data/`", secao)
        self.assertIn("instalar-vps.sh atualizar", secao)
        self.assertIn("/plugin update whatsapp@whatsapp-plugin", secao)
        self.assertTrue((RAIZ / "skills" / "instalar-whatsapp" / "scripts" / "atualizar_plugin.py").is_file())

    def test_a_descricao_da_skill_cobre_atualizar(self):
        cabecalho = self.texto.split("---")[1]
        self.assertIn("atualiza o plugin", cabecalho)

    def test_as_perguntas_novas_tem_motivo_na_secao_por_que(self):
        porque = self.texto.split("## Por que")[1]
        for assunto in ("Todas as perguntas de uma vez", "Bridge pronta antes de compilar", "QR como imagem"):
            self.assertIn(assunto, porque)


class TestePromptDoReadme(unittest.TestCase):
    SALVAGUARDAS = {
        README_EN: ("ask before installing", "qr code", "message sending turned off", "never show the bridge password"),
        README_PT: ("pergunte antes de instalar", "qr", "envio de mensagens desligado", "nunca mostre a senha"),
    }
    PARTE_DA_PESSOA = {
        README_EN: ("Scanning the QR code", "Authorizing", "Deciding", "What it will not do"),
        README_PT: ("Ler o QR", "Autorizar", "Decidir", "O que ele n\u00e3o faz"),
    }

    def test_o_prompt_e_curto_nos_dois_idiomas(self):
        for readme in (README_EN, README_PT):
            with self.subTest(readme=readme.name):
                self.assertLessEqual(len(prompt_do_readme(readme)), 650)

    def test_o_prompt_aponta_para_a_skill_certa_nos_dois_idiomas(self):
        for readme in (README_EN, README_PT):
            prompt = prompt_do_readme(readme)
            with self.subTest(readme=readme.name):
                self.assertIn("skills/instalar-whatsapp/SKILL.md", prompt)
                self.assertIn("github.com/armandonettox/whatsapp-plugin", prompt)

    def test_o_prompt_leva_as_tres_salvaguardas_nos_dois_idiomas(self):
        for readme, frases in self.SALVAGUARDAS.items():
            prompt = prompt_do_readme(readme).lower()
            for frase in frases:
                with self.subTest(readme=readme.name, frase=frase):
                    self.assertIn(frase, prompt)

    def test_o_readme_diz_o_que_continua_sendo_da_pessoa_nos_dois_idiomas(self):
        for readme, trechos in self.PARTE_DA_PESSOA.items():
            secao = secao_de_instalacao(readme)
            for trecho in trechos:
                with self.subTest(readme=readme.name, trecho=trecho):
                    self.assertIn(trecho, secao)

    def test_o_prompt_nao_contem_dado_pessoal(self):
        for readme in (README_EN, README_PT):
            prompt = prompt_do_readme(readme)
            with self.subTest(readme=readme.name):
                self.assertNotRegex(prompt, r"[\w.]+@[\w.]+\.\w+")
                self.assertNotRegex(prompt, r"\d{8,}")

    def test_os_dois_prompts_dizem_a_mesma_coisa_em_numero_de_frases(self):
        def frases(texto):
            return len([f for f in re.split(r"[.]\s", texto) if f.strip()])
        self.assertEqual(frases(prompt_do_readme(README_EN)), frases(prompt_do_readme(README_PT)))

    def test_o_readme_em_ingles_mostra_a_imagem_do_fluxo_de_instalacao(self):
        self.assertIn("docs/install-flow.svg", secao_de_instalacao(README_EN))
        self.assertIn("docs/fluxo-instalacao.svg", secao_de_instalacao(README_PT))


if __name__ == "__main__":
    unittest.main()
