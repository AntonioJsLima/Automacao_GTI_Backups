"""Cópia dos arquivos, sem interpretar ou modificar o conteúdo dos CSVs."""
from datetime import datetime
from pathlib import Path
import logging
import os
import shutil
import tempfile

MESES = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro")


def executar_backup(config: dict, agora: datetime, logger: logging.Logger) -> dict:
    origem = Path(config["origem"])
    destino = (Path(config["destino"])
               / f"{agora.month:02d}.{MESES[agora.month - 1]}"
               / agora.strftime("%d-%m"))
    resultado = {"destino": str(destino), "copiados": [], "falhas": []}
    destino.mkdir(parents=True, exist_ok=True)
    for nome in config["arquivos"]:
        temporario = None
        try:
            # Só substitui uma cópia anterior depois de terminar a nova cópia.
            # O temporário fica no mesmo volume para permitir os.replace.
            fd, caminho = tempfile.mkstemp(prefix=".backup-", suffix=".tmp", dir=destino)
            os.close(fd)
            temporario = Path(caminho)
            shutil.copy2(origem / nome, temporario)
            os.replace(temporario, destino / nome)
            resultado["copiados"].append(nome)
            logger.info("Arquivo copiado: %s", nome)
        except OSError as erro:
            resultado["falhas"].append(nome)
            logger.error("Falha ao copiar %s: %s", nome, erro)
        finally:
            if temporario is not None:
                try:
                    temporario.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Não foi possível limpar temporário: %s", temporario)
    logger.info("Backup finalizado: %d copiados; %d falhas; destino=%s",
                len(resultado["copiados"]), len(resultado["falhas"]), destino)
    return resultado
