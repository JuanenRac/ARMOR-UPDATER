<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-UPDATER banner" width="100%">
</p>

# 🛠️ ARMOR-UPDATER

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Detecta, instala y actualiza cada repositorio de A.R.M.O.R. en la máquina donde se ejecuta (un programa en Python sin dependencias obligatorias)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-191-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.4-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** El descubrimiento por manifiesto, la comparación de versiones, la comprobación de firma, la instalación y actualización por etapas con su bloqueo, su diario, sus copias y su vuelta atrás, el registro de evidencias y las tablas de la interfaz en ocho idiomas están probados (191 tests), y la interfaz Qt Quick se ha ejecutado en Windows. No se ha ejecutado contra todos los repositorios de la familia de principio a fin, y las instalaciones que hace necesitan `git` y las herramientas de compilación de cada repositorio en la máquina.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.1.4` |
| Madurez | Establecido |
| Tests | 191 (`python -m pytest tests -q`) |
| Tecnología | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| En hardware real | No aplica: es un programa de escritorio; su interfaz Qt Quick se ha ejecutado en Windows |

## 🎯 Descripción general

* **Descubrimiento, sin lista fija:** una carpeta local se une en cuanto lleva un `armor.project.json` válido que declara `ecosystem: "A.R.M.O.R."`; en remoto, se revisa igual cada repositorio público de la cuenta. Un `GITHUB_TOKEN` es opcional: solo sube el límite de 60 peticiones a la hora de GitHub.
* **Instalar y actualizar, nunca en el sitio:** un proyecto nuevo y una actualización se construyen y verifican primero en un clon de ensayo independiente, y solo se promueven -dos renombrados con diario, la copia reemplazada guardada en `.armor-updater/backups/` (las tres más recientes)- cuando esa construcción tiene éxito; actualizar al commit ya instalado no hace nada; un cambio local de verdad sin commitear se rechaza sin más, nunca se descarta en silencio; un fallo entre los renombrados se repara en la siguiente ejecución, y `rollback` devuelve la copia más reciente.
* **De uno en uno y en orden:** un bloqueo impide que dos actualizadores trabajen a la vez en un espacio de trabajo; un lote empieza por ARMOR-COMMON (todas las construcciones lo necesitan) y no se construye un proyecto sin él.
* **Evidencia:** cada intento, con éxito o no, añade una línea a un registro local con el proyecto, la versión y el commit antes y después, y el motivo de un fallo.
* **Requisitos:** un manifiesto puede listar, en el campo opcional `requires`, los proyectos que deben instalarse antes; un lote los pone primero, y una instalación o actualización se rechaza con un mensaje claro, en el idioma de la ventana, si falta alguno.
* **Firmas, avisar por defecto:** una revisión sin firma válida se instala o se actualiza igualmente, y la ventana y la línea de comandos indican que no está firmada; elegir *exigir* en los ajustes (`"signature_policy": "require"`) la rechaza en su lugar.
* **Copias anteriores:** la ventana puede restaurar la copia anterior de un proyecto o borrar las copias guardadas, y `status` muestra cuántas hay y el disco que ocupan.
* **Una CLI y una interfaz de escritorio opcional:** `armor-updater status`/`install`/`update`, y una interfaz Qt Quick (`pip install ".[gui]"`) en los ocho idiomas del ecosistema.

## 🧩 Papel en A.R.M.O.R.

ARMOR-UPDATER es la herramienta de escritorio para quien guarda una copia de la familia en un PC: encuentra los repositorios A.R.M.O.R. de la máquina, los compara con GitHub e instala o actualiza uno a uno, verificando antes de sustituir nada. Es distinta de las actualizaciones que [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) gobierna en la CM5 (esas pasan por [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)): esta es para la máquina de un desarrollador.

## 📂 Estructura del repositorio

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              18 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Entorno de desarrollo

**Requisitos:** Python 3.10+, `git` and the build tools of the repositories you install, optional: PySide6 for the desktop shell

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 191 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

Véase `docs/CLI_REFERENCE.md`.

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware del nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nodo eléctrico: contadores, el mensaje de las lecturas de la red y las reglas para maniobrar
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - Nodo y central de alarma: zonas, armado, retardos, sirena y PIN, con el servidor o sin él
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Panel táctil: el estado del sistema en una pantalla de pared, armar y reconocer alarmas, y el hogar del asistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador de sitio 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente Android del operador con radar 2D/3D en vivo
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferencia visual que explica sus decisiones y nunca actúa
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de cámara, máscaras y reglas de detección para la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenciones de voz sin conexión con una confirmación imposible de falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Cajas, electrónica y la matriz de aceptación en banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Despliegue, el banco de pruebas de la CM5, copias de seguridad y TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetría sin conexión con fallos repetibles
* **ARMOR-UPDATER** (este repositorio) - Detecta, instala y actualiza los propios repositorios del ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitectura, base de seguridad y la matriz de capacidades

## 📚 Documentación y comunidad

Dónde leer más:

* [Matriz de capacidades: qué está probado y qué no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de proyectos: versiones y cómo dependen unos de otros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historial de cambios de este repositorio](CHANGELOG.md)
* [Licencia (GPL-3.0-or-later)](LICENSE)
* Preguntas, ideas e informes: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
