"""Entrada do Backup GTI. Sem argumentos: verifica a agenda. --manual: força backup."""
import argparse
from contextlib import contextmanager
from datetime import datetime, time
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile

from backup import executar_backup

DIAS = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo")


def pasta_aplicacao():
    # No executável, configurações externas ficam ao lado do .exe.
    return Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent


def ler_json(caminho):
    with caminho.open(encoding="utf-8-sig") as arquivo:
        return json.load(arquivo)


def carregar_config(caminho):
    config = ler_json(caminho)
    if not isinstance(config, dict):
        raise ValueError("O JSON deve conter um objeto.")
    for campo in ("origem", "destino"):
        valor = config.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"'{campo}' precisa ser um caminho não vazio.")
        pasta = Path(valor)
        config[campo] = str((caminho.parent / pasta).resolve() if not pasta.is_absolute() else pasta)
    if os.path.normcase(config["origem"]) == os.path.normcase(config["destino"]):
        raise ValueError("Origem e destino devem ser diferentes.")
    arquivos = config.get("arquivos")
    if not isinstance(arquivos, list) or not arquivos:
        raise ValueError("'arquivos' precisa ser uma lista não vazia.")
    for nome in arquivos:
        if (not isinstance(nome, str) or not nome.strip() or nome in (".", "..")
                or any(c in nome for c in '/\\:*?"<>|') or nome.endswith((".", " "))):
            raise ValueError("Cada arquivo deve ser um nome simples, incluindo extensão.")
    if len({nome.casefold() for nome in arquivos}) != len(arquivos):
        raise ValueError("A lista de arquivos contém nomes repetidos.")
    agenda = config.get("agendamento")
    if not isinstance(agenda, dict):
        raise ValueError("Informe o objeto 'agendamento'.")
    dias = agenda.get("dias_semana")
    if not isinstance(dias, list) or not dias or any(d not in DIAS for d in dias):
        raise ValueError("Informe dias_semana válidos, sem acentos, como segunda ou terca.")
    horario = agenda.get("horario")
    if not isinstance(horario, str) or len(horario) != 5:
        raise ValueError("Use horario no formato HH:MM.")
    try:
        datetime.strptime(horario, "%H:%M")
    except ValueError as erro:
        raise ValueError("Use horario válido no formato HH:MM.") from erro
    if not isinstance(agenda.get("executar_se_atrasado"), bool):
        raise ValueError("executar_se_atrasado precisa ser true ou false.")
    return config


def preparar_logger(base):
    (base / "logs").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("backup_gti")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in (RotatingFileHandler(base / "logs" / "backup.log", maxBytes=2_000_000,
                                       backupCount=3, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(formato)
        logger.addHandler(handler)
    return logger


@contextmanager
def bloquear_execucao(base):
    # O Windows libera o bloqueio mesmo se o processo for encerrado inesperadamente.
    import msvcrt
    with (base / ".backup.lock").open("a+b") as arquivo:
        arquivo.seek(0, os.SEEK_END)
        if arquivo.tell() == 0:
            arquivo.write(b"0")
            arquivo.flush()
        arquivo.seek(0)
        try:
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            arquivo.seek(0)
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)


def salvar_estado(caminho, estado):
    fd, nome = tempfile.mkstemp(prefix=".estado-", suffix=".tmp", dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(estado, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(nome, caminho)
    finally:
        Path(nome).unlink(missing_ok=True)


def carregar_estado(caminho):
    if not caminho.exists():
        return {}
    estado = ler_json(caminho)
    if not isinstance(estado, dict):
        raise ValueError("estado.json inválido; consulte o log antes de restaurá-lo.")
    data = estado.get("ultima_tentativa_automatica")
    if data is not None:
        datetime.strptime(data, "%Y-%m-%d")
    return estado


def deve_executar(config, estado, agora):
    agenda = config["agendamento"]
    if DIAS[agora.weekday()] not in agenda["dias_semana"]:
        return False
    alvo = time.fromisoformat(agenda["horario"])
    minuto = agora.time().replace(second=0, microsecond=0)
    if minuto < alvo or (not agenda["executar_se_atrasado"] and minuto != alvo):
        return False
    ultima = estado.get("ultima_tentativa_automatica", "")
    return ultima < agora.date().isoformat()


def executar(config, base, logger, manual=False, agora=None):
    agora = agora or datetime.now()
    with bloquear_execucao(base) as adquirido:
        if not adquirido:
            return 0
        caminho_estado = base / "estado.json"
        estado = carregar_estado(caminho_estado)
        if not manual and not deve_executar(config, estado, agora):
            return 0
        # Marca antes de copiar: falha ou interrupção também consome a tentativa diária.
        if not manual:
            estado["ultima_tentativa_automatica"] = agora.date().isoformat()
        estado["ultima_execucao"] = {"inicio": agora.isoformat(),
                                    "modo": "manual" if manual else "automatico",
                                    "status": "iniciada"}
        salvar_estado(caminho_estado, estado)
        logger.info("Iniciando backup %s", estado["ultima_execucao"]["modo"])
        try:
            resultado = executar_backup(config, agora, logger)
            estado["ultima_execucao"].update(resultado)
            falhou = bool(resultado["falhas"])
            estado["ultima_execucao"]["status"] = "com_falhas" if falhou else "concluida"
        except OSError as erro:
            falhou = True
            estado["ultima_execucao"].update(status="falhou", erro=str(erro))
            logger.exception("Não foi possível preparar ou concluir o backup")
        estado["ultima_execucao"]["fim"] = datetime.now().isoformat()
        salvar_estado(caminho_estado, estado)
        return 1 if falhou else 0


def main():
    parser = argparse.ArgumentParser(description="Backup GTI: sem opções, verifica agenda do JSON.")
    parser.add_argument("--manual", action="store_true", help="Executa agora e substitui cópias do dia.")
    parser.add_argument("--validar", action="store_true", help="Valida apenas a configuração, sem copiar.")
    parser.add_argument("--config", type=Path, default=pasta_aplicacao() / "config.json")
    args = parser.parse_args()
    caminho = args.config.resolve()
    logger = None
    try:
        logger = preparar_logger(caminho.parent)
        config = carregar_config(caminho)
        if args.validar:
            logger.info("Configuração válida. Disponibilidade dos arquivos não foi verificada.")
            return 0
        return executar(config, caminho.parent, logger, args.manual)
    except (OSError, ValueError, TypeError) as erro:
        if logger:
            logger.exception("Execução interrompida: %s", erro)
        else:
            print(f"Não foi possível iniciar: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
