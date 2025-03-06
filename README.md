# Transcriptor: Herramienta de Transcripción y Árbol de Directorios

Transcriptor es un paquete de Python diseñado para transcribir el contenido de archivos de código fuente y generar una representación en árbol de la estructura de directorios. Además, permite extraer funciones y clases definidas en cada archivo. La herramienta incluye una interfaz gráfica (usando PySimpleGUI) que facilita la configuración y ejecución del proceso.

## Características

- **Transcripción de Código:**  
  - Extrae el contenido completo de los archivos que cumplen criterios definidos (por ejemplo, extensión `.py`, patrones de inclusión/exclusión).
  - Separa los resultados en archivos de transcripción para tests y para módulos según el modo de procesamiento.

- **Generación de Árbol de Directorios:**  
  - Crea una representación jerárquica de la estructura de directorios utilizando caracteres como `├──` y `└──`.
  - Puede extraer y mostrar las definiciones de funciones y clases (usando el módulo `ast`).

- **Interfaz Gráfica Configurable:**  
  - Permite seleccionar la ruta de entrada y salida, el modo de procesamiento, extensiones, patrones, y opciones para mostrar funciones y clases.
  - Incluye botones para guardar o resetear la configuración, que se almacena en un archivo `config.json`.

- **Configuración Personalizable:**  
  - Define parámetros como las extensiones a procesar, patrones para incluir o excluir archivos, etc.
  - Guarda la configuración para usos futuros y permite restablecerla a los valores por defecto.

## Requisitos

- Python 3.6 o superior.
- [PySimpleGUI](https://pypi.org/project/PySimpleGUI/) (se instalará automáticamente al instalar el paquete).

## Instalación

1. **Clona el repositorio** o descarga el código fuente.

2. **Instala el paquete en modo editable** (esto permite que cualquier cambio en el código se refleje de inmediato sin reinstalar):
   ```bash
   pip install -e .
   ```
Nota: Durante la instalación se generará una carpeta transcriptor.egg-info con metadatos del paquete. Esto es normal y forma parte del proceso de empaquetado.

## Uso

### Ejecutar la Interfaz Gráfica

El paquete incluye un punto de entrada para la línea de comandos. Una vez instalado, puedes iniciar la interfaz gráfica con:

   ```bash
   
   transcriptor-cli
   ```

Esto abrirá la ventana configurada con PySimpleGUI, donde podrás:

- Seleccionar la carpeta a procesar (se abre el explorador en la ruta mostrada).
- Establecer la carpeta de salida (y, en caso de existir, solicitar confirmación para sobrescribir).
- Configurar el modo de procesamiento, extensiones, patrones y opciones de extracción.
- Guardar o resetear la configuración.

### Usar el Paquete en Otros Proyectos

Puedes importar las funciones principales del paquete en tus propios scripts. Por ejemplo:

   ```bash
   
   from transcriptor import transcribir_codigo, generar_arbol_directorios

   def main():
       # Define las rutas de ejemplo
       ruta_codigo = "ruta/a/tu/codigo"
       carpeta_salida = "resultados"
   
       # Transcribe el código
       transcribir_codigo(
           ruta_base=ruta_codigo,
           modo="todo",
           archivo_salida="mi_transcripcion",
           output_folder=carpeta_salida
       )
   
       # Genera el árbol de directorios
       generar_arbol_directorios(
           ruta_base=ruta_codigo,
           mostrar_funciones=True,
           mostrar_clases=True,
           guardar_archivo=f"{carpeta_salida}/mi_arbol.txt"
       )
   
   if __name__ == "__main__":
       main()
   ```

## Estructura del Proyecto

La estructura típica del paquete es la siguiente:

   ```bash
   
   mi_transcriptor/
    ├── transcriptor/
    │   ├── __init__.py         # Inicializa el paquete y expone funciones clave
    │   ├── code_transcriptor.py
    │   ├── tree_generator.py
    │   └── main.py             # Interfaz gráfica (opcional)
    ├── setup.py                # Configuración para la instalación del paquete
    ├── README.md               # Este archivo
    └── .gitignore              # Excluye archivos y directorios no deseados
   ```