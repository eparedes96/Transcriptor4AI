from pathlib import Path

# Ejecuta esto para generar el archivo binario de prueba
path = Path("tests/data/edge_cases/binary_simulation.py")
path.parent.mkdir(parents=True, exist_ok=True)

# Contenido: Cabecera válida + Bytes inválidos en UTF-8 (0x80, 0xFF)
content = b"print('Hello')\n\x80\xff\xfe\x00\n# End of corruption"
path.write_bytes(content)