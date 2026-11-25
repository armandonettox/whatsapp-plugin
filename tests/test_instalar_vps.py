"""Testes do container/instalar-vps.sh com `podman` e `systemctl` de mentira.

Os programas falsos so anotam o que receberam. Nada e instalado, e nenhum container sobe.
Os testes travam: a senha nunca aparece na tela, nada roda como root, o arquivo do OpenBot so
muda com o "sim" e com copia, e o script e idempotente.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "container" / "instalar-vps.sh"
BASH = shutil.which("bash")

PODMAN_FALSO = """#!/usr/bin/env bash
echo "podman $*" >> "$FAKE_LOG"
case "$1 $2" in
  "secret inspect") [ -f "$FAKE_STATE/segredo" ] && exit 0 || exit 1 ;;
  "secret create") cat > "$FAKE_STATE/segredo"; exit 0 ;;
esac
exit 0
"""
SYSTEMCTL_FALSO = """#!/usr/bin/env bash
echo "systemctl $*" >> "$FAKE_LOG"
case "$2" in
  is-active) echo active ;;
esac
exit 0
"""
OPENBOT = """[Unit]
Description=OpenBot

[Container]
Image=ghcr.io/exemplo/openbot:0.78.0
ContainerName=openbot
Volume=openbot-data.volume:/data

[Service]
Restart=always
"""


@unittest.skipUnless(BASH, "precisa do bash")
class InstaladorDaVps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.casa = base / "casa"
        self.bin = base / "bin"
        self.estado = base / "estado"
        for p in (self.casa, self.bin, self.estado):
            p.mkdir()
        self.log = base / "log.txt"
        self.log.write_text("")
        for nome, corpo in (("podman", PODMAN_FALSO), ("systemctl", SYSTEMCTL_FALSO)):
            f = self.bin / nome
            f.write_text(corpo, newline="\n")
            f.chmod(f.stat().st_mode | stat.S_IXUSR)
        self.quadlet = self.casa / ".config" / "containers" / "systemd"

    def rodar(self, *args):
        env = dict(os.environ)
        env.update({"HOME": str(self.casa), "FAKE_LOG": str(self.log), "FAKE_STATE": str(self.estado),
                    "PATH": str(self.bin) + os.pathsep + env["PATH"]})
        return subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8",
                              env=env, timeout=60, stdin=subprocess.DEVNULL)

    def comandos(self):
        return self.log.read_text().splitlines()

    def test_preparar_constroi_cria_a_senha_instala_e_inicia_a_bridge(self):
        r = self.rodar()
        self.assertEqual(r.returncode, 0, r.stderr)
        cmds = "\n".join(self.comandos())
        self.assertIn("podman build -f", cmds)
        self.assertIn("bridge.Containerfile", cmds)
        self.assertIn("mcp.Containerfile", cmds)
        self.assertIn("podman secret create whatsapp-bridge-token -", cmds)
        self.assertIn("systemctl --user daemon-reload", cmds)
        self.assertIn("systemctl --user start whatsapp-bridge.service", cmds)
        self.assertIn("podman logs -f whatsapp-bridge", cmds)
        for nome in ("whatsapp-bridge.container", "whatsapp-mcp.container", "whatsapp-back.network",
                     "whatsapp-agente.network", "whatsapp-data.volume"):
            self.assertTrue((self.quadlet / nome).is_file(), nome)

    def test_a_imagem_construida_e_a_que_os_quadlets_usam(self):
        self.rodar()
        cmds = "\n".join(self.comandos()) + " "
        for arquivo in ("whatsapp-bridge.container", "whatsapp-mcp.container"):
            linhas = (RAIZ / "container" / "quadlet" / arquivo).read_text().splitlines()
            imagem = next(l[6:] for l in linhas if l.startswith("Image="))
            self.assertIn("-t " + imagem + " ", cmds)

    def test_a_senha_nunca_aparece_na_tela_nem_no_log_de_comandos(self):
        r = self.rodar()
        segredo = (self.estado / "segredo").read_text().strip()
        self.assertGreaterEqual(len(segredo), 32)  # o segredo foi gerado e entregue ao podman
        self.assertNotIn(segredo, r.stdout + r.stderr)
        self.assertNotIn(segredo, self.log.read_text())

    def test_senha_existente_nao_e_trocada(self):
        (self.estado / "segredo").write_text("senha-antiga-de-teste")
        r = self.rodar()
        self.assertEqual((self.estado / "segredo").read_text(), "senha-antiga-de-teste")
        self.assertIn("ja existe", r.stdout)
        self.assertNotIn("podman secret create", self.log.read_text())

    def test_audio_so_com_a_opcao(self):
        self.rodar()
        self.assertNotIn("INSTALL_AUDIO", self.log.read_text())
        self.log.write_text("")
        self.rodar("--audio")
        self.assertIn("--build-arg INSTALL_AUDIO=1", self.log.read_text())

    def test_nenhuma_porta_publicada_nem_privilegio(self):
        self.rodar()
        cmds = self.log.read_text()
        for proibido in (" -p ", "--publish", "--privileged", "sudo"):
            self.assertNotIn(proibido, cmds)

    def test_servidor_sem_quadlets_instalados_pede_para_preparar_primeiro(self):
        r = self.rodar("servidor", "--sem-openbot")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("instalar-vps.sh", r.stderr)

    def preparar_openbot(self):
        self.rodar()
        self.log.write_text("")
        arquivo = self.quadlet / "openbot.container"
        arquivo.write_text(OPENBOT, newline="\n")
        return arquivo

    def test_servidor_liga_o_openbot_com_copia_e_so_com_o_sim(self):
        arquivo = self.preparar_openbot()
        r = self.rodar("servidor", "--sim")
        self.assertEqual(r.returncode, 0, r.stderr)
        texto = arquivo.read_text()
        linhas = texto.splitlines()
        self.assertEqual(texto.count("Network=whatsapp-agente.network"), 1)
        self.assertEqual(linhas.index("[Container]") + 1, linhas.index("Network=whatsapp-agente.network"))
        self.assertEqual(Path(str(arquivo) + ".bak").read_text(), OPENBOT)
        # o resto do arquivo continua igual
        sem = [l for l in linhas if l != "Network=whatsapp-agente.network"]
        self.assertEqual(sem, OPENBOT.splitlines())
        cmds = "\n".join(self.comandos())
        self.assertIn("systemctl --user start whatsapp-mcp.service", cmds)
        self.assertIn("systemctl --user restart openbot.service", cmds)

    def test_servidor_sem_o_sim_e_sem_terminal_nao_altera_o_openbot(self):
        arquivo = self.preparar_openbot()
        r = self.rodar("servidor")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(arquivo.read_text(), OPENBOT)
        self.assertFalse(Path(str(arquivo) + ".bak").exists())
        self.assertNotIn("restart openbot", self.log.read_text())

    def test_servidor_rodado_duas_vezes_nao_duplica_a_rede(self):
        arquivo = self.preparar_openbot()
        self.rodar("servidor", "--sim")
        self.log.write_text("")
        r = self.rodar("servidor", "--sim")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(arquivo.read_text().count("Network=whatsapp-agente.network"), 1)
        self.assertNotIn("restart openbot", self.log.read_text())

    def test_arquivo_do_openbot_sem_secao_container_e_restaurado(self):
        arquivo = self.preparar_openbot()
        arquivo.write_text("[Unit]\nDescription=so isso\n", newline="\n")
        r = self.rodar("servidor", "--sim")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(arquivo.read_text(), "[Unit]\nDescription=so isso\n")

    def test_sem_openbot_nao_toca_no_arquivo_dele(self):
        arquivo = self.preparar_openbot()
        r = self.rodar("servidor", "--sem-openbot")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(arquivo.read_text(), OPENBOT)
        self.assertNotIn("restart openbot", self.log.read_text())

    def test_openbot_ausente_da_erro_claro_sem_alterar_nada(self):
        self.rodar()
        r = self.rodar("servidor", "--sim")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--openbot-arquivo", r.stderr)

    def test_opcao_desconhecida_e_recusada(self):
        r = self.rodar("--apagar-tudo")
        self.assertEqual(r.returncode, 2)

    def test_status_lista_as_unidades(self):
        r = self.rodar("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        for u in ("whatsapp-bridge", "whatsapp-mcp", "openbot"):
            self.assertIn(u, r.stdout)

    def test_o_script_e_ascii_com_fim_de_linha_lf(self):
        dados = SCRIPT.read_bytes()
        dados.decode("ascii")
        self.assertNotIn(b"\r", dados)

    def test_o_script_nao_le_o_valor_da_senha(self):
        corpo = SCRIPT.read_text()
        self.assertNotIn("--showsecret", corpo)


if __name__ == "__main__":
    unittest.main()
