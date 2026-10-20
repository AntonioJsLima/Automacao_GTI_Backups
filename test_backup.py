"""Testes locais: não acessam a pasta de rede nem o destino real."""
from datetime import datetime
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.origem = self.base / "origem"
        self.origem.mkdir()
        self.config = {
            "origem": str(self.origem), "destino": str(self.base / "destino"),
            "arquivos": ["atendimentos.csv", "clientesAtendidos.csv", "FatoProducao.csv", "producoesReports.csv"],
            "agendamento": {"dias_semana": list(main.DIAS[:5]), "horario": "10:00", "executar_se_atrasado": True}}
        for nome in self.config["arquivos"]:
            (self.origem / nome).write_bytes(b"id;valor\r\n1;100\r\n")
        self.logger = logging.getLogger("teste_backup")
        self.logger.addHandler(logging.NullHandler())
        self.agora = datetime(2026, 10, 16, 11, 30)
        self.destino = self.base / "destino" / "10.Outubro" / "16-10"

    def run_backup(self, manual=False, agora=None):
        return main.executar(self.config, self.base, self.logger, manual, agora or self.agora)

    def test_backup_atrasado_preserva_conteudo_e_so_executa_uma_vez(self):
        self.assertEqual(self.run_backup(), 0)
        for nome in self.config["arquivos"]:
            self.assertEqual((self.destino / nome).read_bytes(), (self.origem / nome).read_bytes())
        nome = self.config["arquivos"][0]
        (self.origem / nome).write_bytes(b"alterado")
        self.assertEqual(self.run_backup(), 0)
        self.assertNotEqual((self.destino / nome).read_bytes(), b"alterado")
        self.assertEqual(self.run_backup(manual=True), 0)
        self.assertEqual((self.destino / nome).read_bytes(), b"alterado")

    def test_ausente_registra_falha_copia_demais_e_consume_tentativa(self):
        (self.origem / "FatoProducao.csv").unlink()
        with self.assertLogs("teste_backup", level="ERROR") as logs:
            self.assertEqual(self.run_backup(), 1)
        self.assertIn("FatoProducao.csv", " ".join(logs.output))
        self.assertEqual(len(list(self.destino.glob("*.csv"))), 3)
        estado = main.carregar_estado(self.base / "estado.json")
        self.assertEqual(estado["ultima_execucao"]["falhas"], ["FatoProducao.csv"])
        self.assertFalse(main.deve_executar(self.config, estado, self.agora))

    def test_antes_do_horario_e_fim_de_semana_nao_copia(self):
        for data in (datetime(2026, 10, 16, 9, 59), datetime(2026, 10, 17, 11), datetime(2026, 10, 18, 11)):
            self.assertEqual(self.run_backup(agora=data), 0)
        self.assertFalse((self.base / "estado.json").exists())
        self.assertFalse((self.base / "destino").exists())

    def test_config_editada_e_proximo_dia(self):
        self.config["agendamento"]["horario"] = "12:00"
        self.assertFalse(main.deve_executar(self.config, {}, self.agora))
        self.config["agendamento"]["horario"] = "10:00"
        self.assertTrue(main.deve_executar(self.config, {"ultima_tentativa_automatica": "2026-10-15"}, self.agora))
        self.config["agendamento"]["executar_se_atrasado"] = False
        self.assertFalse(main.deve_executar(self.config, {}, self.agora))

    def test_copia_interrompida_preserva_backup_anterior(self):
        self.run_backup()
        anterior = (self.destino / "atendimentos.csv").read_bytes()
        with patch("backup.shutil.copy2", side_effect=OSError("Falha de rede simulada")):
            self.assertEqual(self.run_backup(manual=True), 1)
        self.assertEqual((self.destino / "atendimentos.csv").read_bytes(), anterior)
        self.assertEqual(list(self.destino.glob("*.tmp")), [])

    def test_bloqueio_impede_execucoes_simultaneas(self):
        with main.bloquear_execucao(self.base) as primeiro:
            self.assertTrue(primeiro)
            self.assertEqual(self.run_backup(), 0)
            self.assertFalse(self.destino.exists())

    def test_estado_corrompido_interrompe_sem_copiar(self):
        (self.base / "estado.json").write_text("{quebrado", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_backup()
        self.assertFalse(self.destino.exists())

    def test_validacao_config(self):
        caminho = self.base / "config.json"
        caminho.write_text(json.dumps(self.config), encoding="utf-8")
        self.assertEqual(main.carregar_config(caminho)["arquivos"], self.config["arquivos"])
        self.config["arquivos"] = ["../arquivo.csv"]
        caminho.write_text(json.dumps(self.config), encoding="utf-8")
        with self.assertRaises(ValueError):
            main.carregar_config(caminho)

    def test_destino_inacessivel_consumiu_tentativa(self):
        arquivo = self.base / "nao_e_pasta"
        arquivo.write_text("teste")
        self.config["destino"] = str(arquivo)
        self.assertEqual(self.run_backup(), 1)
        estado = main.carregar_estado(self.base / "estado.json")
        self.assertEqual(estado["ultima_execucao"]["status"], "falhou")
        self.assertFalse(main.deve_executar(self.config, estado, self.agora))


if __name__ == "__main__":
    unittest.main()
