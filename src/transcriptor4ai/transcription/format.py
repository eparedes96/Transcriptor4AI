from __future__ import annotations

# -----------------------------------------------------------------------------
# Escritura de entradas
# -----------------------------------------------------------------------------
def _append_entry(output_path: str, rel_path: str, contenido: str) -> None:
    """
    Añade una entrada al final del fichero de salida.
    """
    with open(output_path, "a", encoding="utf-8") as out:
        out.write("-" * 200 + "\n")
        out.write(f"{rel_path}\n")
        out.write(contenido.rstrip("\n") + "\n")