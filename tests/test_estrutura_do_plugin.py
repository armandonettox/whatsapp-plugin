"""Testes da estrutura do plugin: skills, comandos, manifestos e texto publico.

Garante que cada skill funciona sozinha (os arquivos que ela cita existem), que os comandos tem
descricao, que os manifestos concordam entre si e que os textos publicos nao carregam bastidores
(historias de correcao, pessoas, empresas, notas privadas) nem emoji.

Os termos proibidos sao montados em tempo de execucao, para este arquivo passar nele mesmo.
"""

import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SKILLS = sorted(p for p in (RAIZ / "skills").iterdir() if p.is_dir())
COMANDOS = sorted((RAIZ / "commands").glob("*.md"))
SKILLS_ESPERADAS = {
    "instalar-whatsapp", "usar-whatsapp-mcp", "triagem-whatsapp", "notas-por-contato", "escrever-como-humano",
    "mensagens-em-partes",
}
COMANDOS_ESPERADOS = {"status", "pendentes", "responder", "resumo", "loop", "modo", "atualizar"}

PASTAS_IGNORADAS = {".git", "data", ".venv", "__pycache__", "node_modules"}
ARQUIVOS_IGNORADOS = {"uv.lock", "go.sum"}
EXTENSOES_BINARIAS = {".png", ".jpg", ".exe", ".db", ".zip"}

# Rastros de bastidores que nao podem aparecer em texto publico (montados em pedacos)
PROIBIDOS = {
    "nome interno do projeto antigo": re.compile("conci" + "erge", re.I),
    "referencia a nota privada": re.compile("va" + "ult", re.I),
    "numero de learning": re.compile(r"\bL-\d{3}\b"),
    "empresa": re.compile(r"best\s?sa|best" + "senior|best" + "saude", re.I),
    "projeto privado": re.compile("her" + "mes", re.I),
    "e-mail pessoal": re.compile("armando" + "sln7", re.I),
    "relato de problema passado": re.compile(r"j[aá] (?:aconteceu|precisou)|inci" + "dente", re.I),
}


def arquivos_de_texto():
    for caminho in RAIZ.rglob("*"):
        if not caminho.is_file():
            continue
        partes = set(caminho.relative_to(RAIZ).parts)
        if partes & PASTAS_IGNORADAS or caminho.name in ARQUIVOS_IGNORADOS or caminho.suffix.lower() in EXTENSOES_BINARIAS:
            continue
        try:
            yield caminho, caminho.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def frontmatter(texto: str) -> dict:
    assert texto.startswith("---\n") or texto.startswith("---\r\n"), "sem frontmatter"
    bloco = texto.split("---", 2)[1]
    dados = {}
    for linha in bloco.strip().splitlines():
        if ":" in linha:
            chave, _, valor = linha.partition(":")
            dados[chave.strip()] = valor.strip().strip('"')
    return dados


class TesteSkills(unittest.TestCase):
    def test_existem_exatamente_as_seis_skills(self):
        self.assertEqual({p.name for p in SKILLS}, SKILLS_ESPERADAS)

    def test_cada_skill_tem_nome_igual_a_pasta_e_descricao(self):
        for pasta in SKILLS:
            with self.subTest(skill=pasta.name):
                dados = frontmatter((pasta / "SKILL.md").read_text(encoding="utf-8"))
                self.assertEqual(dados.get("name"), pasta.name)
                descricao = dados.get("description", "")
                self.assertGreater(len(descricao), 80)
                self.assertLessEqual(len(descricao), 1024)

    def test_os_arquivos_citados_pela_skill_existem_dentro_dela(self):
        for pasta in SKILLS:
            texto = (pasta / "SKILL.md").read_text(encoding="utf-8")
            for citado in set(re.findall(r"(?:references|scripts)/[\w.-]+\.(?:md|py)", texto)):
                with self.subTest(skill=pasta.name, arquivo=citado):
                    self.assertTrue((pasta / citado).is_file(), f"{pasta.name} cita {citado}, que nao existe")

    def test_referencias_citam_so_arquivos_que_existem(self):
        for pasta in SKILLS:
            for referencia in (pasta / "references").glob("*.md") if (pasta / "references").is_dir() else []:
                texto = referencia.read_text(encoding="utf-8")
                for citado in set(re.findall(r"(?:references|scripts)/[\w.-]+\.(?:md|py)", texto)):
                    with self.subTest(arquivo=referencia.name, citado=citado):
                        existe = any((outra / citado).is_file() for outra in SKILLS)
                        self.assertTrue(existe, f"{referencia.name} cita {citado}, que nao existe em nenhuma skill")

    def test_toda_skill_tem_uma_secao_com_o_porque(self):
        for pasta in SKILLS:
            with self.subTest(skill=pasta.name):
                self.assertIn("## Por que", (pasta / "SKILL.md").read_text(encoding="utf-8"))

    def test_scripts_de_cada_skill_estao_onde_a_skill_diz(self):
        esperados = {
            "triagem-whatsapp": {"listar_pendentes.py", "buscar_contato.py", "resumo_contato.py", "aprofundar_historico.py",
                                 "aguardar_backlog.py", "resumo_sessao.py", "caminhos.py", "_comum.py"},
            "notas-por-contato": {"criar_nota.py", "compromissos.py", "_comum.py"},
            "mensagens-em-partes": {"dividir_mensagem.py"},
            "instalar-whatsapp": {"verificar_instalacao.py", "baixar_bridge.py", "atualizar_plugin.py"},
        }
        for skill, nomes in esperados.items():
            with self.subTest(skill=skill):
                presentes = {p.name for p in (RAIZ / "skills" / skill / "scripts").glob("*.py")}
                self.assertEqual(presentes, nomes)


class TesteComandos(unittest.TestCase):
    def test_existem_os_comandos_esperados(self):
        self.assertEqual({c.stem for c in COMANDOS}, COMANDOS_ESPERADOS)

    def test_cada_comando_tem_descricao(self):
        for comando in COMANDOS:
            with self.subTest(comando=comando.stem):
                dados = frontmatter(comando.read_text(encoding="utf-8"))
                self.assertGreater(len(dados.get("description", "")), 20)

    def test_comando_com_argumento_usa_o_argumento(self):
        for comando in COMANDOS:
            texto = comando.read_text(encoding="utf-8")
            if "argument-hint" in texto:
                with self.subTest(comando=comando.stem):
                    self.assertIn("$ARGUMENTS", texto)

    def test_o_comando_de_atualizar_verifica_primeiro_pergunta_e_nao_forca(self):
        texto = (RAIZ / "commands" / "atualizar.md").read_text(encoding="utf-8")
        for trecho in ("scripts/atualizar_plugin.py", "--aplicar", "Verifique primeiro, sem alterar nada",
                       "pergunte se pode atualizar", "nao force nada", "pasta `data/`",
                       "/plugin update whatsapp@whatsapp-plugin", "instalar-vps.sh atualizar"):
            self.assertIn(trecho, texto)
        self.assertLess(texto.index("Verifique primeiro"), texto.index("--aplicar"))

    def test_o_loop_nunca_manda_enviar(self):
        texto = (RAIZ / "commands" / "loop.md").read_text(encoding="utf-8")
        self.assertIn("nunca envia", texto.lower())
        pendentes = (RAIZ / "commands" / "pendentes.md").read_text(encoding="utf-8")
        self.assertIn("Não envie nada", pendentes)

    def test_arquivos_citados_pelos_comandos_existem(self):
        for comando in COMANDOS:
            for citado in set(re.findall(r"(?:references|scripts)/[\w.-]+\.(?:md|py)", comando.read_text(encoding="utf-8"))):
                with self.subTest(comando=comando.stem, citado=citado):
                    self.assertTrue(any((pasta / citado).is_file() for pasta in SKILLS))


class TesteManifestos(unittest.TestCase):
    def carregar(self, caminho: str) -> dict:
        return json.loads((RAIZ / caminho).read_text(encoding="utf-8"))

    def test_versao_e_nome_batem_entre_os_manifestos(self):
        plugin = self.carregar(".claude-plugin/plugin.json")
        catalogo = self.carregar(".claude-plugin/marketplace.json")["plugins"][0]
        self.assertEqual(plugin["name"], catalogo["name"])
        self.assertEqual(plugin["version"], catalogo["version"])
        self.assertEqual(plugin["license"], catalogo["license"])

    def test_hooks_apontam_para_arquivos_que_existem(self):
        hooks = self.carregar("hooks/hooks.json")["hooks"]
        for evento, grupos in hooks.items():
            for grupo in grupos:
                for hook in grupo["hooks"]:
                    for citado in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", hook["command"]):
                        with self.subTest(evento=evento, arquivo=citado):
                            self.assertTrue((RAIZ / citado).is_file())

    def test_servidor_mcp_aponta_para_a_pasta_do_servidor(self):
        mcp = self.carregar(".mcp.json")["mcpServers"]["whatsapp"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/server", " ".join(mcp["args"]))
        self.assertTrue((RAIZ / "server" / "main.py").is_file())

    def test_licenca_e_aviso_de_terceiros_existem(self):
        licenca = (RAIZ / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", licenca)
        self.assertIn("Luke Harries", licenca)
        aviso = (RAIZ / "NOTICE").read_text(encoding="utf-8")
        for termo in ("whatsapp-mcp", "whatsmeow", "MPL-2.0"):
            self.assertIn(termo, aviso)


class TesteTextoPublico(unittest.TestCase):
    def test_nenhum_rastro_de_bastidores(self):
        achados = []
        for caminho, texto in arquivos_de_texto():
            for nome, regra in PROIBIDOS.items():
                if regra.search(texto):
                    achados.append(f"{caminho.relative_to(RAIZ)}: {nome}")
        self.assertEqual(achados, [], "rastros de bastidores nos arquivos:\n" + "\n".join(achados))

    def test_nenhum_emoji_em_arquivo_algum(self):
        achados = []
        for caminho, texto in arquivos_de_texto():
            for caractere in texto:
                codigo = ord(caractere)
                if 0x1F000 <= codigo <= 0x1FAFF or 0x2600 <= codigo <= 0x27BF or 0x2B00 <= codigo <= 0x2BFF:
                    achados.append(f"{caminho.relative_to(RAIZ)}: U+{codigo:04X}")
                    break
        self.assertEqual(achados, [])

    def test_o_verificador_de_termos_proibidos_funciona(self):
        # controle positivo: cada regra acha o que deve achar
        amostras = {
            "nome interno do projeto antigo": "conci" + "erge-mcp",
            "referencia a nota privada": "vau" + "lt pessoal",
            "numero de learning": "L-" + "648",
            "empresa": "Best " + "Saude",
            "projeto privado": "her" + "mes",
            "e-mail pessoal": "armando" + "sln7" + "@" + "gmail" + ".com",
            "relato de problema passado": "ja " + "aconteceu antes",
        }
        for nome, amostra in amostras.items():
            with self.subTest(regra=nome):
                self.assertTrue(PROIBIDOS[nome].search(amostra))
        self.assertFalse(PROIBIDOS["numero de learning"].search("versao L-12"))


README_EN = RAIZ / "README.md"
README_PT = RAIZ / "README.pt-BR.md"
IMAGENS_EN = ("capa.png", "install-flow.svg", "architecture.svg", "send-flow-animated.svg", "send-modes.svg", "container-isolation.svg")
IMAGENS_PT = ("capa.png", "fluxo-instalacao.svg", "arquitetura.svg", "fluxo-envio-animado.svg", "modos-de-envio.svg", "isolamento-containers.svg")


def ler(caminho) -> str:
    return caminho.read_text(encoding="utf-8")


class TesteReadmeEmDoisIdiomas(unittest.TestCase):
    """O README principal e em ingles e ha uma versao em portugues. Os dois contam a mesma historia."""

    def test_os_dois_arquivos_existem_e_se_apontam(self):
        self.assertIn("(README.pt-BR.md)", ler(README_EN).split("## ", 1)[0])
        self.assertIn("(README.md)", ler(README_PT).split("## ", 1)[0])

    def test_o_principal_esta_em_ingles_e_o_outro_em_portugues(self):
        self.assertTrue(ler(README_EN).startswith("# WhatsApp for AI agents"))
        self.assertTrue(ler(README_PT).startswith("# WhatsApp para agentes de IA"))
        self.assertIn("Install with an agent", ler(README_EN))
        self.assertIn("Instalar com a ajuda de um agente", ler(README_PT))
        self.assertNotIn("Instalar com a ajuda", ler(README_EN))

    def test_as_duas_versoes_tem_o_mesmo_numero_de_secoes(self):
        def secoes(texto):
            return [l for l in texto.splitlines() if l.startswith("## ")]
        self.assertEqual(len(secoes(ler(README_EN))), len(secoes(ler(README_PT))))

    def test_as_duas_versoes_tem_o_mesmo_numero_de_subsecoes_e_blocos_de_codigo(self):
        for marca in ("### ", "`" * 3):
            self.assertEqual(ler(README_EN).count(marca), ler(README_PT).count(marca), marca)

    def test_cada_versao_usa_as_imagens_no_proprio_idioma_e_todas_existem(self):
        for caminho, imagens in ((README_EN, IMAGENS_EN), (README_PT, IMAGENS_PT)):
            texto = ler(caminho)
            for imagem in imagens:
                with self.subTest(readme=caminho.name, imagem=imagem):
                    self.assertIn(f"docs/{imagem})", texto)
                    self.assertTrue((RAIZ / "docs" / imagem).is_file())

    def test_o_readme_em_ingles_nao_usa_as_imagens_em_portugues(self):
        for imagem in IMAGENS_PT:
            if imagem not in IMAGENS_EN:
                self.assertNotIn(imagem, ler(README_EN))
        for imagem in IMAGENS_EN:
            if imagem not in IMAGENS_PT:
                self.assertNotIn(imagem, ler(README_PT))

    def test_as_imagens_em_ingles_nao_tem_texto_em_portugues(self):
        acentos = re.compile("[\u00e1\u00e9\u00ed\u00f3\u00fa\u00e2\u00ea\u00f4\u00e3\u00f5\u00e7]")
        nomes = ("architecture.svg", "send-flow.svg", "send-flow-animated.svg", "send-modes.svg", "container-isolation.svg", "install-flow.svg")
        for nome in nomes:
            corpo = ler(RAIZ / "docs" / nome).split("</defs>", 1)[1]
            textos = re.findall(r">([^<>]*[^<>\s][^<>]*)<", corpo)
            with self.subTest(imagem=nome):
                self.assertEqual([x for x in textos if acentos.search(x)], [])
                self.assertIn('lang="en"', ler(RAIZ / "docs" / nome))

    def test_as_imagens_em_portugues_declaram_o_idioma(self):
        for nome in ("modos-de-envio.svg", "isolamento-containers.svg", "fluxo-instalacao.svg"):
            self.assertIn('lang="pt-BR"', ler(RAIZ / "docs" / nome))

    def test_as_duas_versoes_documentam_as_mesmas_variaveis(self):
        padrao = re.compile("(?<![A-Z_])(?:WHATSAPP_[A-Z_]+|WHISPER_MODELO)(?![A-Z_])")
        self.assertEqual(set(padrao.findall(ler(README_EN))), set(padrao.findall(ler(README_PT))))

    def test_as_duas_versoes_dizem_o_que_foi_e_o_que_nao_foi_testado(self):
        self.assertIn("**Tested:**", ler(README_EN))
        self.assertIn("**Not tested yet:**", ler(README_EN))
        self.assertIn("**Testado:**", ler(README_PT))
        self.assertIn("**Ainda n\u00e3o testado:**", ler(README_PT))

    def test_nenhuma_das_duas_diz_que_a_api_da_bridge_nao_tem_senha(self):
        self.assertNotIn("n\u00e3o tem senha", ler(README_PT))
        self.assertNotIn("has no password", ler(README_EN))
        self.assertIn("WHATSAPP_BRIDGE_TOKEN", ler(README_EN).split("## Privacy and security", 1)[1].split("## Requirements", 1)[0])
        self.assertIn("WHATSAPP_BRIDGE_TOKEN", ler(README_PT).split("## Privacidade e seguran\u00e7a", 1)[1].split("## Requisitos", 1)[0])

    def test_o_readme_em_ingles_avisa_que_os_guias_estao_em_portugues(self):
        self.assertIn("The detailed guides are currently written in Portuguese.", ler(README_EN))


class TestePosicionamentoParaQualquerAgente(unittest.TestCase):
    """O projeto e um servidor MCP que funciona em qualquer agente; o Claude Code e um dos agentes.
    A apresentacao nao pode tratar o Claude Code como o unico caminho (nos dois idiomas)."""

    AGENTES = ("OpenBot", "Codex", "OpenCode", "OpenClaw")

    def test_o_titulo_do_readme_nao_e_so_do_claude_code(self):
        for caminho, palavra in ((README_EN, "agents"), (README_PT, "agentes")):
            titulo = ler(caminho).splitlines()[0]
            with self.subTest(readme=caminho.name):
                self.assertNotIn("Claude", titulo)
                self.assertIn(palavra, titulo)

    def test_o_primeiro_paragrafo_cita_os_outros_agentes(self):
        for caminho in (README_EN, README_PT):
            abertura = ler(caminho).split("## ", 1)[0]
            for agente in self.AGENTES:
                with self.subTest(readme=caminho.name, agente=agente):
                    self.assertIn(agente, abertura)

    def test_as_descricoes_dos_manifestos_falam_de_agentes_de_ia(self):
        plugin = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        catalogo = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        projeto = (RAIZ / "server" / "pyproject.toml").read_text(encoding="utf-8")
        for texto in (plugin["description"], catalogo["description"], projeto):
            self.assertIn("agentes de IA", texto)
        self.assertNotIn("WhatsApp para Claude Code", plugin["description"])

    def test_o_readme_tem_uma_tabela_de_agentes_com_o_que_vem_junto(self):
        cabecalhos = {README_EN: "| Your agent | How to use it | What comes with it |", README_PT: "| Seu agente | Como usar | O que vem junto |"}
        for caminho, cabecalho in cabecalhos.items():
            texto = ler(caminho)
            with self.subTest(readme=caminho.name):
                self.assertIn(cabecalho, texto)
                for agente in ("Claude Code", "OpenBot", "Codex, OpenCode, OpenClaw"):
                    self.assertIn(f"**{agente}**", texto)

    def test_a_instalacao_nao_assume_o_claude_code(self):
        casos = {
            README_EN: ("## Manual installation", "## Usage", "**4. Connect to your agent**", "**Other agents**", "Open Claude Code"),
            README_PT: ("## Instala\u00e7\u00e3o", "## Uso", "**4. Conecte ao seu agente**", "**Outros agentes**", "Abra o Claude Code"),
        }
        for caminho, (inicio, fim, passo, outros, proibido) in casos.items():
            instalacao = ler(caminho).split(inicio, 1)[1].split(fim, 1)[0]
            with self.subTest(readme=caminho.name):
                self.assertIn(passo, instalacao)
                self.assertIn(outros, instalacao)
                self.assertNotIn(proibido, instalacao)

    def test_o_diagrama_nao_diz_que_o_agente_e_o_claude_code(self):
        self.assertIn("Seu agente", ler(RAIZ / "docs" / "arquitetura.svg"))
        self.assertIn("Your agent", ler(RAIZ / "docs" / "architecture.svg"))
        self.assertNotIn(">Como o plugin funciona<", ler(RAIZ / "docs" / "arquitetura.svg"))

    def test_o_que_so_existe_no_claude_code_diz_que_e_so_dele(self):
        self.assertIn("## The send guard (Claude Code)", ler(README_EN))
        self.assertIn("**Commands** for Claude Code", ler(README_EN))
        self.assertIn("## O guarda de envio (Claude Code)", ler(README_PT))
        self.assertIn("**Comandos** para o Claude Code", ler(README_PT))
        guia = (RAIZ / "docs" / "guia-de-uso.md").read_text(encoding="utf-8")
        self.assertIn("### Comandos (Claude Code)", guia)

class TesteDependenciasDoServidor(unittest.TestCase):
    """O servidor usa recursos do pacote mcp que so existem a partir de uma versao, e a versao 2
    renomeia a API. O limite no pyproject e a versao do lock precisam concordar com isso."""

    VERSAO_MINIMA = (1, 29)

    def versao_no_lock(self) -> tuple:
        linhas = (RAIZ / "server" / "uv.lock").read_text(encoding="utf-8").splitlines()
        for i, linha in enumerate(linhas):
            if linha == 'name = "mcp"' and linhas[i + 1].startswith("version = "):
                partes = linhas[i + 1].split('"')[1].split(".")
                return int(partes[0]), int(partes[1])
        self.fail("o lock nao tem o pacote mcp")

    def test_o_pyproject_limita_o_mcp_a_1_x_a_partir_da_versao_testada(self):
        projeto = (RAIZ / "server" / "pyproject.toml").read_text(encoding="utf-8")
        achado = re.search(r'"mcp(?:\[cli\])?>=(\d+)\.(\d+)[\d.]*,<(\d+)"', projeto)
        self.assertIsNotNone(achado, "o mcp precisa ter piso e teto de versao")
        self.assertGreaterEqual((int(achado.group(1)), int(achado.group(2))), self.VERSAO_MINIMA)
        self.assertEqual(int(achado.group(3)), 2)

    def test_o_lock_respeita_o_piso_e_o_teto(self):
        versao = self.versao_no_lock()
        self.assertGreaterEqual(versao, self.VERSAO_MINIMA)
        self.assertLess(versao[0], 2)

    def test_o_servidor_so_usa_o_que_o_piso_garante(self):
        codigo = (RAIZ / "server" / "main.py").read_text(encoding="utf-8")
        self.assertIn("from mcp.server.fastmcp import FastMCP", codigo)  # nome da API na linha 1.x
        self.assertIn("TransportSecuritySettings", codigo)

    def test_o_ci_usa_o_arquivo_de_travas(self):
        fluxo = (RAIZ / ".github" / "workflows" / "testes.yml").read_text(encoding="utf-8")
        self.assertIn("uv sync --project server --frozen", fluxo)
        self.assertIn("uv run --project server --frozen python -m unittest", fluxo)
        self.assertNotRegex(fluxo, "pip install[^" + chr(10) + "]*mcp")


class TesteVariaveisDeAmbiente(unittest.TestCase):
    def test_toda_variavel_usada_no_codigo_esta_no_readme(self):
        readmes = {nome: (RAIZ / nome).read_text(encoding="utf-8") for nome in ("README.md", "README.pt-BR.md")}
        padrao = re.compile(r"(?<![A-Z_])(?:WHATSAPP_[A-Z_]+|WHISPER_MODELO)(?![A-Z_])")
        usadas = {}
        for caminho, texto in arquivos_de_texto():
            partes = caminho.relative_to(RAIZ).parts
            if partes[0] in ("tests", "docs") or caminho.name in ("README.md", "README.pt-BR.md", "AGENTS.md", "CHANGELOG.md"):
                continue
            for nome in set(padrao.findall(texto)):
                usadas.setdefault(nome, str(caminho.relative_to(RAIZ)))
        faltam = sorted(f"{n} (em {onde}, falta no {nome})" for n, onde in usadas.items() for nome, readme in readmes.items() if n not in readme)
        self.assertEqual(faltam, [], "variaveis sem documentacao no README:" + chr(10) + chr(10).join(faltam))
        self.assertGreater(len(usadas), 10)  # controle: a busca esta mesmo achando as variaveis


if __name__ == "__main__":
    unittest.main()
