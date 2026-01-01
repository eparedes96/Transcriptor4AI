# src/transcriptor4ai/pipeline.py
# -----------------------------------------------------------------------------
# Orquestador (sin UI) que:
# - Normaliza/valida config (diccionario)
# - Resuelve rutas finales de entrada/salida
# - Detecta sobrescrituras potenciales (lista de ficheros existentes)
# - Ejecuta: transcribir_codigo + generar_arbol_directorios (opcional)
# - Devuelve un resultado agregado pensado para GUI/CLI
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from transcriptor4ai.config import (
    DEFAULT_OUTPUT_PREFIX,
    cargar_configuracion_por_defecto,
)
from transcriptor4ai.paths import (
    DEFAULT_OUTPUT_SUBDIR,
    normalizar_dir,
    ruta_salida_real,
    archivos_destino,
    existen_ficheros_destino,
)
from transcriptor4ai.filtering import (
    default_extensiones,
    default_patrones_incluir,
    default_patrones_excluir,
)
from transcriptor4ai.transcription.service import transcribir_codigo
from transcriptor4ai.tree.service import generar_arbol_directorios


# -----------------------------------------------------------------------------
# Modelos de resultado
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineResult:
    ok: bool
    error: str

    # Entradas normalizadas
    ruta_base: str
    output_base_dir: str
    output_subdir_name: str
    output_prefix: str
    modo: str

    # Salidas
    salida_real: str
    existentes: List[str]

    # Resultados parciales
    res_transcripcion: Dict[str, Any]
    res_arbol_lines: List[str]
    ruta_arbol: str

    # Resumen
    resumen: Dict[str, Any]


# -----------------------------------------------------------------------------
# Helpers de normalización/contratos
# -----------------------------------------------------------------------------

def _ensure_list(value: Any, fallback: List[str]) -> List[str]:
    if value is None:
        return list(fallback)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",") if x.strip()]
        return items if items else list(fallback)
    return list(fallback)


def _ensure_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "si", "sí"):
            return True
        if v in ("0", "false", "no", "n"):
            return False
    return fallback


def _normalize_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normaliza un dict de configuración sin cambiar el "contrato" externo:
    sigue siendo dict y tolera valores None / strings.
    """
    defaults = cargar_configuracion_por_defecto()
    cfg: Dict[str, Any] = dict(defaults)
    if isinstance(config, dict):
        cfg.update(config)

    # Modo
    modo = (cfg.get("modo_procesamiento") or "todo").strip()
    if modo not in ("todo", "solo_modulos", "solo_tests"):
        modo = "todo"
    cfg["modo_procesamiento"] = modo

    # Listas
    cfg["extensiones"] = _ensure_list(cfg.get("extensiones"), default_extensiones())
    cfg["patrones_incluir"] = _ensure_list(cfg.get("patrones_incluir"), default_patrones_incluir())
    cfg["patrones_excluir"] = _ensure_list(cfg.get("patrones_excluir"), default_patrones_excluir())

    # Bools
    cfg["generar_arbol"] = _ensure_bool(cfg.get("generar_arbol"), False)
    cfg["imprimir_arbol"] = _ensure_bool(cfg.get("imprimir_arbol"), True)
    cfg["guardar_log_errores"] = _ensure_bool(cfg.get("guardar_log_errores"), True)
    cfg["mostrar_funciones"] = _ensure_bool(cfg.get("mostrar_funciones"), False)
    cfg["mostrar_clases"] = _ensure_bool(cfg.get("mostrar_clases"), False)
    cfg["mostrar_metodos"] = _ensure_bool(cfg.get("mostrar_metodos"), False)

    # Strings esenciales
    cfg["output_subdir_name"] = (cfg.get("output_subdir_name") or DEFAULT_OUTPUT_SUBDIR).strip() or DEFAULT_OUTPUT_SUBDIR
    cfg["output_prefix"] = (cfg.get("output_prefix") or DEFAULT_OUTPUT_PREFIX).strip() or DEFAULT_OUTPUT_PREFIX

    return cfg


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------

def run_pipeline(
    config: Optional[Dict[str, Any]],
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> PipelineResult:
    """
    Ejecuta el pipeline completo (sin UI).

    Args:
        config: dict con claves compatibles con la app (se normaliza).
        overwrite: si False y hay ficheros existentes, NO ejecuta y devuelve ok=False.
        dry_run: si True, calcula rutas/existentes pero NO ejecuta escritura.

    Returns:
        PipelineResult: resultado agregado.
    """
    # -------------------------------------------------------------------------
    # 1) Normalizar config
    # -------------------------------------------------------------------------
    cfg = _normalize_config(config)

    # -------------------------------------------------------------------------
    # 2) Normalizar rutas de entrada/salida
    # -------------------------------------------------------------------------
    fallback_base = os.path.dirname(os.path.abspath(__file__))
    ruta_base = normalizar_dir(cfg.get("ruta_carpetas", ""), fallback_base)

    if not os.path.exists(ruta_base):
        return PipelineResult(
            ok=False,
            error=f"La ruta a procesar no existe: {ruta_base}",
            ruta_base=ruta_base,
            output_base_dir="",
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["modo_procesamiento"],
            salida_real="",
            existentes=[],
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )
    if not os.path.isdir(ruta_base):
        return PipelineResult(
            ok=False,
            error=f"La ruta a procesar no es un directorio: {ruta_base}",
            ruta_base=ruta_base,
            output_base_dir="",
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["modo_procesamiento"],
            salida_real="",
            existentes=[],
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )

    output_base_dir = normalizar_dir(cfg.get("output_base_dir", ""), ruta_base)
    salida_real = ruta_salida_real(output_base_dir, cfg["output_subdir_name"])

    # -------------------------------------------------------------------------
    # 3) Detectar sobrescrituras
    # -------------------------------------------------------------------------
    nombres = archivos_destino(cfg["output_prefix"], cfg["modo_procesamiento"], bool(cfg.get("generar_arbol")))
    existentes = existen_ficheros_destino(salida_real, nombres)

    if existentes and not overwrite and not dry_run:
        return PipelineResult(
            ok=False,
            error="Hay ficheros existentes en la salida. Ejecución cancelada (overwrite=False).",
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["modo_procesamiento"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={
                "procesados": 0,
                "omitidos": 0,
                "errores": 0,
                "existing_files": list(existentes),
            },
        )

    if dry_run:
        return PipelineResult(
            ok=True,
            error="",
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["modo_procesamiento"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol=os.path.join(salida_real, f"{cfg['output_prefix']}_arbol.txt") if cfg.get("generar_arbol") else "",
            resumen={
                "dry_run": True,
                "existing_files": list(existentes),
                "will_generate": list(nombres),
            },
        )

    # -------------------------------------------------------------------------
    # 4) Asegurar carpeta de salida
    # -------------------------------------------------------------------------
    try:
        os.makedirs(salida_real, exist_ok=True)
    except OSError as e:
        return PipelineResult(
            ok=False,
            error=f"No se pudo crear la carpeta de salida: {salida_real}. Error: {e}",
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["modo_procesamiento"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )

    # -------------------------------------------------------------------------
    # 5) Transcripción
    # -------------------------------------------------------------------------
    res_trans = transcribir_codigo(
        ruta_base=ruta_base,
        modo=cfg["modo_procesamiento"],
        extensiones=cfg["extensiones"],
        patrones_incluir=cfg["patrones_incluir"],
        patrones_excluir=cfg["patrones_excluir"],
        archivo_salida=cfg["output_prefix"],
        output_folder=salida_real,
        guardar_log_errores=bool(cfg.get("guardar_log_errores")),
    )

    if not res_trans.get("ok"):
        return PipelineResult(
            ok=False,
            error=f"Fallo en transcripción: {res_trans.get('error', 'Error desconocido')}",
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["modo_procesamiento"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion=res_trans,
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )

    # -------------------------------------------------------------------------
    # 6) Árbol
    # -------------------------------------------------------------------------
    arbol_lines: List[str] = []
    ruta_arbol = ""
    if cfg.get("generar_arbol"):
        ruta_arbol = os.path.join(salida_real, f"{cfg['output_prefix']}_arbol.txt")

        arbol_lines = generar_arbol_directorios(
            ruta_base=ruta_base,
            modo=cfg["modo_procesamiento"],
            extensiones=cfg["extensiones"],
            patrones_incluir=cfg["patrones_incluir"],
            patrones_excluir=cfg["patrones_excluir"],
            mostrar_funciones=bool(cfg.get("mostrar_funciones")),
            mostrar_clases=bool(cfg.get("mostrar_clases")),
            mostrar_metodos=bool(cfg.get("mostrar_metodos")),
            imprimir=bool(cfg.get("imprimir_arbol")),
            guardar_archivo=ruta_arbol,
        )

    # -------------------------------------------------------------------------
    # 7) Resumen agregado
    # -------------------------------------------------------------------------
    cont = res_trans.get("contadores", {}) or {}
    resumen = {
        "salida_real": salida_real,
        "procesados": int(cont.get("procesados", 0)),
        "omitidos": int(cont.get("omitidos", 0)),
        "errores": int(cont.get("errores", 0)),
        "generados": (res_trans.get("generados", {}) or {}),
        "arbol": {
            "generado": bool(cfg.get("generar_arbol")),
            "ruta": ruta_arbol,
            "lineas": len(arbol_lines),
        },
        "existing_files_before_run": list(existentes),
    }

    return PipelineResult(
        ok=True,
        error="",
        ruta_base=ruta_base,
        output_base_dir=output_base_dir,
        output_subdir_name=cfg["output_subdir_name"],
        output_prefix=cfg["output_prefix"],
        modo=cfg["modo_procesamiento"],
        salida_real=salida_real,
        existentes=existentes,
        res_transcripcion=res_trans,
        res_arbol_lines=arbol_lines,
        ruta_arbol=ruta_arbol,
        resumen=resumen,
    )