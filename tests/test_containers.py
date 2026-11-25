"""Testes dos arquivos de container (container/): isolamento, senha e coerencia entre os arquivos.

Nao constroem imagens nem sobem containers. Travam as propriedades que protegem a conta:
- a bridge nunca esta na rede do agente nem publica porta;
- o servidor MCP so publica porta no loopback;
- a senha da bridge vem de segredo ou de variavel obrigatoria, nunca de um valor no arquivo;
- tudo roda sem root e sem privilegios extras;
- os nomes de redes, volumes e imagens batem entre compose, Quadlet e Containerfiles.

O teste do compose usa o comando `docker compose config` (so le o arquivo, nao precisa do daemon)
e e pulado quando o docker nao esta instalado.
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONTAINER = RAIZ / "container"
QUADLET = CONTAINER / "quadlet"
VERSAO = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def ler_quadlet(caminho: Path) -> dict:
    """Le um arquivo Quadlet (ini com chaves repetidas). Devolve {secao: {chave: [valores]}}."""
    dados, secao = {}, None
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith(("#", ";")):
            continue
        if linha.startswith("[") and linha.endswith("]"):
            secao = linha[1:-1]
            dados.setdefault(secao, {})
        elif "=" in linha and secao:
            chave, _, valor = linha.partition("=")
            dados[secao].setdefault(chave.strip(), []).append(valor.strip())
    return dados


def container(nome: str) -> dict:
    return ler_quadlet(QUADLET / f"{nome}.container")["Container"]


class TesteQuadletDaVps(unittest.TestCase):
    def test_a_bridge_so_esta_na_rede_back_e_nao_publica_porta(self):
        bridge = container("whatsapp-bridge")
        self.assertEqual(bridge["Network"], ["whatsapp-back.network"])
        self.assertNotIn("PublishPort", bridge)

    def test_o_servidor_mcp_esta_nas_duas_redes_e_nao_publica_porta(self):
        mcp = container("whatsapp-mcp")
        self.assertEqual(sorted(mcp["Network"]), ["whatsapp-agente.network", "whatsapp-back.network"])
        self.assertNotIn("PublishPort", mcp)

    def test_nenhum_container_do_quadlet_publica_porta(self):
        for arquivo in QUADLET.glob("*.container"):
            with self.subTest(arquivo=arquivo.name):
                self.assertNotIn("PublishPort", ler_quadlet(arquivo)["Container"])

    def test_a_senha_vem_de_segredo_e_nunca_de_valor_no_arquivo(self):
        for nome in ("whatsapp-bridge", "whatsapp-mcp"):
            with self.subTest(container=nome):
                c = container(nome)
                self.assertTrue(any(s.startswith("whatsapp-bridge-token,type=env,target=WHATSAPP_BRIDGE_TOKEN") for s in c["Secret"]))
                ambiente = " ".join(c.get("Environment", []))
                self.assertNotIn("WHATSAPP_BRIDGE_TOKEN", ambiente)

    def test_sem_privilegios_extras(self):
        for nome in ("whatsapp-bridge", "whatsapp-mcp"):
            with self.subTest(container=nome):
                c = container(nome)
                self.assertEqual(c["DropCapability"], ["ALL"])
                self.assertEqual(c["NoNewPrivileges"], ["true"])
                self.assertNotIn("PodmanArgs", c)
                self.assertNotIn("AddCapability", c)

    def test_o_modo_de_envio_nunca_e_hook_em_container(self):
        modos = [v.strip('"') for v in container("whatsapp-mcp").get("Environment", []) if v.strip('"').startswith("WHATSAPP_SEND_MODE=")]
        self.assertEqual(len(modos), 1)
        self.assertIn(modos[0].split("=", 1)[1], ("read-only", "two-step"))

    def test_o_comando_de_confirmacao_usa_o_nome_do_container(self):
        comandos = [v.strip('"') for v in container("whatsapp-mcp")["Environment"]
                    if v.strip('"').startswith("WHATSAPP_CONFIRM_COMMAND=")]
        self.assertEqual(len(comandos), 1)
        self.assertIn("exec -it whatsapp-mcp", comandos[0])

    def test_valor_de_ambiente_com_espaco_vai_entre_aspas(self):
        # O Quadlet corta o valor no primeiro espaco quando nao ha aspas
        for arquivo in QUADLET.glob("*.container"):
            for valor in ler_quadlet(arquivo)["Container"].get("Environment", []):
                with self.subTest(arquivo=arquivo.name, valor=valor[:40]):
                    if " " in valor:
                        self.assertTrue(valor.startswith('"') and valor.endswith('"'), valor)

    def test_imagens_tem_a_versao_do_plugin(self):
        for nome in ("whatsapp-bridge", "whatsapp-mcp"):
            with self.subTest(container=nome):
                self.assertEqual(container(nome)["Image"], [f"localhost/{nome}:{VERSAO}"])

    def test_referencias_a_volumes_e_redes_existem(self):
        for arquivo in QUADLET.glob("*.container"):
            c = ler_quadlet(arquivo)["Container"]
            for rede in c.get("Network", []):
                with self.subTest(arquivo=arquivo.name, rede=rede):
                    self.assertTrue((QUADLET / rede).is_file(), rede)
            for volume in c.get("Volume", []):
                origem = volume.split(":")[0]
                if origem.endswith(".volume"):
                    with self.subTest(arquivo=arquivo.name, volume=origem):
                        self.assertTrue((QUADLET / origem).is_file(), origem)

    def test_as_redes_tem_os_nomes_esperados_e_a_do_agente_nao_inclui_a_bridge(self):
        self.assertEqual(ler_quadlet(QUADLET / "whatsapp-back.network")["Network"]["NetworkName"], ["whatsapp-back"])
        self.assertEqual(ler_quadlet(QUADLET / "whatsapp-agente.network")["Network"]["NetworkName"], ["whatsapp-agente"])
        usam_agente = [a.name for a in QUADLET.glob("*.container") if "whatsapp-agente.network" in ler_quadlet(a)["Container"].get("Network", [])]
        self.assertEqual(usam_agente, ["whatsapp-mcp.container"])

    def test_o_servidor_mcp_depende_da_bridge(self):
        unidade = ler_quadlet(QUADLET / "whatsapp-mcp.container")["Unit"]
        self.assertIn("whatsapp-bridge.service", unidade["Requires"])


class TesteContainerfiles(unittest.TestCase):
    def texto(self, nome):
        return (CONTAINER / nome).read_text(encoding="utf-8")

    def test_ambos_rodam_sem_root(self):
        for nome in ("bridge.Containerfile", "mcp.Containerfile"):
            with self.subTest(arquivo=nome):
                usuarios = re.findall(r"^USER\s+(\S+)", self.texto(nome), re.M)
                self.assertTrue(usuarios)
                self.assertEqual(usuarios[-1], "whatsapp")

    def test_a_bridge_so_escuta_fora_do_loopback_porque_exige_senha(self):
        texto = self.texto("bridge.Containerfile")
        self.assertIn("WHATSAPP_BRIDGE_ADDR=0.0.0.0", texto)
        self.assertIn("senha", texto.lower())
        self.assertNotIn("WHATSAPP_BRIDGE_TOKEN=", texto)

    def test_a_bridge_roda_de_dentro_da_pasta_bridge(self):
        self.assertIn("WORKDIR /app/bridge", self.texto("bridge.Containerfile"))

    def test_o_servidor_aceita_so_os_nomes_de_host_esperados(self):
        texto = self.texto("mcp.Containerfile")
        permitidos = re.search(r'WHATSAPP_MCP_ALLOWED_HOSTS="([^"]+)"', texto).group(1).split(",")
        self.assertIn("whatsapp-mcp:8765", permitidos)
        self.assertTrue(all(h.endswith(":8765") for h in permitidos), permitidos)

    def test_o_servidor_aponta_para_a_bridge_pelo_nome_do_container(self):
        self.assertIn('WHATSAPP_API_BASE_URL="http://whatsapp-bridge:8081/api"', self.texto("mcp.Containerfile"))

    def test_o_servidor_comeca_em_somente_leitura(self):
        self.assertIn("WHATSAPP_SEND_MODE=read-only", self.texto("mcp.Containerfile"))

    def test_o_servidor_usa_o_lock_do_projeto(self):
        self.assertIn("uv sync --frozen", self.texto("mcp.Containerfile"))

    def test_o_contexto_de_build_nao_leva_dados_nem_historico(self):
        ignorados = (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()
        for item in (".git", "data/", ".env", "*.db", "*.log"):
            self.assertIn(item, ignorados)


class TesteComposeDoComputador(unittest.TestCase):
    def texto(self):
        return (CONTAINER / "compose.yaml").read_text(encoding="utf-8")

    def test_a_senha_e_obrigatoria_e_nao_tem_valor_no_arquivo(self):
        texto = self.texto()
        self.assertEqual(len(re.findall(r"WHATSAPP_BRIDGE_TOKEN: \$\{WHATSAPP_BRIDGE_TOKEN:\?", texto)), 2)
        self.assertNotRegex(texto, r"WHATSAPP_BRIDGE_TOKEN:\s+[A-Za-z0-9]")

    def test_a_porta_do_servidor_so_vale_no_loopback(self):
        portas = re.findall(r'^\s*-\s*"([^"]*:\d+:\d+)"', self.texto(), re.M)
        self.assertEqual(portas, ["127.0.0.1:8765:8765"])

    def test_a_bridge_nao_publica_porta_e_so_esta_na_rede_back(self):
        bloco = self.texto().split("  mcp:")[0].split("  bridge:")[1]
        self.assertNotIn("ports:", bloco)
        self.assertIn("- back", bloco)
        self.assertNotIn("- agente", bloco)

    def test_sem_privilegios_extras(self):
        texto = self.texto()
        self.assertEqual(texto.count("- ALL"), 2)
        self.assertEqual(texto.count("no-new-privileges:true"), 2)
        self.assertNotIn("privileged", texto)

    def test_o_arquivo_de_exemplo_nao_traz_senha_e_nao_e_ignorado_pelo_git(self):
        exemplo = (CONTAINER / ".env.example").read_text(encoding="utf-8")
        self.assertRegex(exemplo, r"(?m)^WHATSAPP_BRIDGE_TOKEN=\s*$")
        self.assertIn("!.env.example", (RAIZ / ".gitignore").read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("docker"), "docker nao instalado")
    def test_o_docker_compose_aceita_o_arquivo(self):
        env = dict(os.environ, WHATSAPP_BRIDGE_TOKEN="senha-de-teste")
        r = subprocess.run(["docker", "compose", "-f", str(CONTAINER / "compose.yaml"), "config", "--format", "json"],
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        if r.returncode != 0 and "docker compose" in r.stderr.lower() and "unknown" in r.stderr.lower():
            self.skipTest("plugin compose do docker nao instalado")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        servicos = json.loads(r.stdout)["services"]
        self.assertEqual(set(servicos), {"bridge", "mcp"})
        self.assertEqual(set(servicos["bridge"]["networks"]), {"back"})
        self.assertNotIn("ports", servicos["bridge"])
        self.assertEqual(servicos["mcp"]["ports"][0]["host_ip"], "127.0.0.1")

    @unittest.skipUnless(shutil.which("docker"), "docker nao instalado")
    def test_o_docker_compose_recusa_subir_sem_a_senha(self):
        env = {k: v for k, v in os.environ.items() if k != "WHATSAPP_BRIDGE_TOKEN"}
        r = subprocess.run(["docker", "compose", "-f", str(CONTAINER / "compose.yaml"), "config"],
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        if "unknown" in r.stderr.lower() and "compose" in r.stderr.lower():
            self.skipTest("plugin compose do docker nao instalado")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("WHATSAPP_BRIDGE_TOKEN", r.stderr)


if __name__ == "__main__":
    unittest.main()
