# src/transcriptor4ai/logging.py
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# Modelo de configuración de logging
# =============================================================================

@dataclass(frozen=True)
class LoggingConfig:
    """
    Configuración simple y estable para centralizar logging.

    - level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    - log_file: ruta a archivo (opcional). Si se define, añade FileHandler.
    - console: si True, añade StreamHandler (stderr).
    - fmt: formato del log (opcional).
    """
    level: str = "INFO"
    log_file: Optional[str] = None
    console: bool = True
    fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


# =============================================================================
# Helpers internos
# =============================================================================

_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,  # tolerancia
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _parse_level(level: str) -> int:
    if not level:
        return logging.INFO
    return _LEVEL_MAP.get(level.strip().upper(), logging.INFO)


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _safe_add_file_handler(
    logger: logging.Logger,
    log_file: str,
    fmt: logging.Formatter,
    level: int,
) -> None:
    """
    Intenta añadir FileHandler. Si falla, no rompe la app: cae a consola.
    """
    try:
        _ensure_parent_dir(log_file)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(level)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        logger.warning("No se pudo escribir el log en archivo; se usa consola. log_file=%s", log_file)


# =============================================================================
# API pública
# =============================================================================

def build_config_from_dict(d: dict) -> LoggingConfig:
    """
    Construye LoggingConfig desde dict (típicamente config.json).

    Se aceptan claves esperables (tolerante a faltantes):
      - logging_level (str)
      - logging_file (str)
      - logging_console (bool)

    Nota: si tu config actual no tiene estas claves, esto no rompe nada.
    """
    level = str(d.get("logging_level") or d.get("log_level") or "INFO")
    log_file = d.get("logging_file") or d.get("log_file") or None
    console = bool(d.get("logging_console", True))
    return LoggingConfig(level=level, log_file=log_file, console=console)


def configure_logging(cfg: LoggingConfig) -> logging.Logger:
    """
    Configura el root logger de forma idempotente (sin duplicar handlers).

    - Limpia handlers existentes del root logger para evitar duplicados (útil en CLI/tests).
    - Añade StreamHandler (stderr) y/o FileHandler si aplica.
    - Devuelve el root logger.
    """
    root = logging.getLogger()
    level_int = _parse_level(cfg.level)
    root.setLevel(level_int)

    # Evitar logs duplicados en re-entradas
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(cfg.fmt)

    # Consola
    if cfg.console:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(level_int)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # Archivo
    if cfg.log_file:
        _safe_add_file_handler(root, cfg.log_file, formatter, level_int)

    return root


def get_logger(name: str) -> logging.Logger:
    """
    Conveniencia: obtener logger nombrado.
    """
    return logging.getLogger(name)