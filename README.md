# 📘 **Herramientas de Python: Code Transcription y Directory Tree Generator**

## **Contenido**
1. [Introducción](#introducción)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación](#instalación)
4. [Uso del Módulo Code Transcription](#uso-del-módulo-code-transcription)
    - [Descripción](#descripción)
    - [Ejemplo Básico](#ejemplo-básico)
    - [Opciones Avanzadas](#opciones-avanzadas)
5. [Uso del Módulo Directory Tree Generator](#uso-del-módulo-directory-tree-generator)
    - [Descripción](#descripción-1)
    - [Ejemplo Básico](#ejemplo-básico-1)
    - [Opciones Avanzadas](#opciones-avanzadas-1)
6. [Solución de Problemas](#solución-de-problemas)
7. [Notas Adicionales](#notas-adicionales)

---

## **Introducción**

Estos dos módulos de Python están diseñados para ayudarte a gestionar y visualizar el contenido de tus proyectos de manera más eficiente:

- **Code Transcription**: Permite generar transcripciones de archivos de código según diferentes criterios de inclusión y exclusión.
- **Directory Tree Generator**: Genera y muestra un árbol de directorios y archivos, con opciones para extraer funciones y clases de archivos Python.

Este manual te guiará paso a paso para que puedas utilizarlos sin complicaciones.

---

## **Requisitos Previos**

Antes de comenzar, asegúrate de tener lo siguiente:

1. **Python Instalado**: Ambos módulos están escritos en Python. Necesitas tener Python instalado en tu computadora. Puedes descargarlo desde [python.org](https://www.python.org/downloads/).

2. **Conocimientos Básicos de la Línea de Comandos**: Los módulos se ejecutan desde la terminal o el símbolo del sistema. Familiarízate con abrir y navegar en la terminal de tu sistema operativo.

3. **Descargar los Módulos**: Asegúrate de tener los archivos `code_transcription.py` y `directory_tree.py` descargados en una carpeta de tu elección.

---

## **Instalación**

1. **Descargar Python**:
   - Visita [python.org](https://www.python.org/downloads/) y descarga la versión más reciente de Python compatible con tu sistema operativo.
   - Durante la instalación, asegúrate de marcar la opción **"Add Python to PATH"** para facilitar el uso desde la línea de comandos.

2. **Verificar la Instalación**:
   - Abre la terminal (o símbolo del sistema en Windows).
   - Escribe `python --version` y presiona **Enter**. Deberías ver la versión de Python instalada.
     ```bash
     python --version
     ```

3. **Obtener los Módulos**:
   - Descarga los archivos `code_transcription.py` y `directory_tree.py` y guárdalos en una carpeta, por ejemplo, `C:/HerramientasPython/`.

---

## **Uso del Módulo Code Transcription**

### **Descripción**

El módulo **Code Transcription** permite generar una transcripción de los archivos de código en una carpeta específica, filtrando según ciertos criterios como tipo de archivo, patrones de inclusión/exclusión y modos de selección (solo módulos, solo tests, todo).

### **Ejemplo Básico**

Supongamos que deseas transcribir todos los archivos `.py` que no son de test en una carpeta y guardar la transcripción en un archivo de texto.

1. **Abrir la Terminal**:
   - En Windows: Presiona **Win + R**, escribe `cmd` y presiona **Enter**.
   - En macOS/Linux: Abre la aplicación **Terminal**.


2. **Navegar a la Carpeta de los Módulos**:
    ```bash
    cd C:/HerramientasPython/
    ```

3. **Ejecutar el Módulo Code Transcription**:
    ```bash
   cd python code_transcription.py --ruta_carpetas "C:/Ruta/De/Tu/Proyecto" --modo "solo_modulos" --archivo_salida "transcripcion_modulos.txt"
    ```

    **Descripción de los Argumentos**:

    - **--ruta_carpetas**: Ruta de la carpeta que deseas procesar.
    - **--modo**: Modo de inclusión de archivos. Opciones disponibles:
        - **solo_modulos**: Incluye solo archivos que no son de test.
        - **solo_tests**: Incluye solo archivos de test.
        - **todo**: Incluye todos los archivos.
    - **--archivo_salida**: Nombre del archivo donde se guardará la transcripción.


4. **Resultado**:
    - Se creará un archivo llamado **transcripcion_modulos.txt** en la carpeta actual con la transcripción de los archivos seleccionados.

### **Opciones Avanzadas**

Puedes personalizar aún más el comportamiento del módulo usando opciones adicionales.

**Ejemplo con Opciones Avanzadas**:

    ```bash
    python code_transcription.py \
        --ruta_carpetas "C:/Ruta/De/Tu/Proyecto" \
        --modo "todo" \
        --archivo_salida "transcripcion_completa.txt" \
        --extensiones ".py" ".js" \
        --patrones_excluir "__pycache__" "*.pyc" \
        --mostrar_clases
    ```

**Descripción de los Argumentos Adicionales**:

- **--extensiones**: Especifica las extensiones de archivo a incluir. Por defecto es .py. Puedes agregar múltiples extensiones separadas por espacios, por ejemplo, .py .js.
- **--patrones_incluir**: Patrones regex para incluir archivos o carpetas específicos.
- **--patrones_excluir**: Patrones regex para excluir archivos o carpetas específicos.
- **--mostrar_clases**: Si se incluye esta opción, también se extraerán y mostrarán las clases definidas en los archivos.

**Notas**:

- Los patrones de exclusión utilizan expresiones regulares. Por ejemplo, **__pycache__** excluye la carpeta **__pycache__**, y ***.pyc** excluye todos los archivos con extensión **.pyc**.
- Para patrones más complejos, consulta una guía básica de expresiones regulares.

---

## Uso del Módulo Directory Tree Generator

### Descripción

El módulo **Directory Tree Generator** genera y muestra un árbol de directorios y archivos desde una ruta inicial especificada. Además, puede extraer y mostrar funciones y clases de archivos Python.

**Ejemplo Básico**

Supongamos que deseas visualizar la estructura de directorios de una carpeta y mostrar únicamente los archivos **.py**.

1. **Abrir la Terminal**:

- En Windows: Presiona **Win + R**, escribe **cmd** y presiona **Enter**.
- En macOS/Linux: Abre la aplicación **Terminal**.

2. **Navegar a la Carpeta de los Módulos**:

    ```bash
   cd C:/HerramientasPython/
    ```
   
3. **Ejecutar el Módulo Directory Tree Generator**:

    ```bash
    python directory_tree.py --ruta_inicial "C:/Ruta/De/Tu/Proyecto"
    ```
   
    **Descripción de los Argumentos**:

    - **--ruta_inicial**: Ruta del directorio inicial que deseas visualizar.
    - **--extensiones**: (Opcional) Especifica las extensiones de archivo a incluir. Por defecto es .py.
    - **--patrones_incluir**: (Opcional) Patrones regex para incluir archivos o carpetas específicos.
    - **--patrones_excluir****: (Opcional) Patrones regex para excluir archivos o carpetas específicos.
    - **--mostrar_funcione**s**: (Opcional) Si se incluye, extraerá y mostrará las funciones definidas en los archivos.
    - **--mostrar_clases**:** (Opcional) Si se incluye, extraerá y mostrará las clases definidas en los archivos.
    - **--guardar_archivo**: (Opcional) Ruta del archivo donde se guardará el árbol generado.

4. **Resultado**:

- Se mostrará en la terminal el árbol de directorios y archivos de la ruta especificada.

**Opciones Avanzadas**

Puedes personalizar el árbol de directorios con opciones adicionales.

**Ejemplo con Opciones Avanzadas**:

    ```bash
    python directory_tree.py \
    --ruta_inicial "C:/Ruta/De/Tu/Proyecto" \
    --extensiones ".py" ".js" \
    --patrones_excluir "__pycache__" "*.pyc" \
    --mostrar_funciones \
    --mostrar_clases \
    --guardar_archivo "arbol_directorio.txt"
    ```

**Descripción de los Argumentos Adicionales**:

- **--extensiones**: Especifica las extensiones de archivo a incluir. Puedes agregar múltiples extensiones separadas por espacios, por ejemplo, .py .js.
- **--patrones_incluir**: Patrones regex para incluir archivos o carpetas específicos.
- **--patrones_excluir**: Patrones regex para excluir archivos o carpetas específicos.
- **--mostrar_funciones**: Extrae y muestra las funciones definidas en los archivos Python.
- **--mostrar_clases**: Extrae y muestra las clases definidas en los archivos Python.
- **--guardar_archivo**: Guarda el árbol generado en un archivo de texto especificado.

**Notas**:

- Al usar **--guardar_archivo**, el árbol también se guardará en el archivo indicado, además de mostrarse en la terminal.
- Las opciones **--mostrar_funciones** y **--mostrar_clases** son útiles para obtener una visión más detallada del contenido de tus archivos Python.

---

## Solución de Problemas

A continuación, se presentan algunas soluciones a problemas comunes que podrías encontrar al usar estos módulos.

### 1. **Python No Reconocido en la Terminal**

**Problema**: Al ejecutar **python**, la terminal indica que el comando no se reconoce.

**Solución**:

- Asegúrate de haber agregado Python al PATH durante la instalación.
- Si ya lo hiciste, reinicia la terminal o tu computadora.
- Verifica la instalación con:

    ```bash
    python --version
    ```
  
    Si aún no funciona, intenta usar python3 en lugar de python.

### 2. **Error al Ejecutar el Módulo**

**Problema**: La terminal muestra un error al intentar ejecutar el módulo, por ejemplo, **ModuleNotFoundError** o **SyntaxError**.

**Solución**:

- Asegúrate de estar en la carpeta correcta donde se encuentran los archivos **code_transcription.py** o **directory_tree.py**.
- Verifica que el archivo se descargó correctamente y que no tiene errores de sintaxis.
- Asegúrate de estar usando una versión de Python compatible (recomendado Python 3.6 o superior).

### 3. **No Se Genera el Archivo de Salida**

**Problema**: Al ejecutar el módulo, no se crea el archivo de salida especificado.

**Solución**:

- Verifica que tienes permisos de escritura en la carpeta donde estás intentando guardar el archivo.
- Asegúrate de que la ruta proporcionada para **--archivo_salida** o **--guardar_archivo** es correcta y accesible.
- Revisa si hubo algún mensaje de error durante la ejecución del módulo que indique qué salió mal.

### 4. **Los Patrones Regex No Funcionan Como Esperado**

**Problema**: Los patrones de inclusión/exclusión no filtran los archivos correctamente.

**Solución**:

- Asegúrate de que las expresiones regulares (regex) estén bien escritas. Puedes probarlas en herramientas online como regex101.com.
- Recuerda que los patrones regex son sensibles a mayúsculas y minúsculas por defecto.
- Si estás excluyendo una carpeta específica como **__pycache__**, utiliza el patrón **__pycache__** sin comillas ni caracteres especiales.

---

## Notas Adicionales

- **Expresiones Regulares Básicas**: Si no estás familiarizado con las regex, aquí hay algunos ejemplos útiles:
    - **^test_.*\.py$**: Coincide con archivos que comienzan con test_ y terminan con **.py**.
    - **.*_test\.py$**: Coincide con archivos que terminan con **_test.py**.
    - **__pycache__**: Coincide con la carpeta **__pycache__**.
    - **.*\.pyc$**: Coincide con todos los archivos que terminan con **.pyc**.
- **Extensiones de Archivo**: Asegúrate de incluir el punto (.) al especificar extensiones, por ejemplo, **.py** y no **py**.
- **Compatibilidad de Rutas**:
  - En Windows, las rutas pueden usar barras normales (/) o invertidas (\). Por ejemplo, **C:/Ruta/De/Tu/Proyecto** o **C:\\Ruta\\De\\Tu\\Proyecto**.
  - En macOS/Linux, utiliza barras normales (/).
- **Permisos de Archivo**: Si encuentras problemas al leer ciertos archivos, verifica que tienes los permisos necesarios para acceder a ellos.
- **Actualizaciones de los Módulos**: Si el módulo recibe actualizaciones futuras, asegúrate de mantener una copia actualizada para aprovechar las mejoras y correcciones de errores.