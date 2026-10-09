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
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>

### Detecta, instala y actualiza cada repositorio de A.R.M.O.R. en la máquina donde se ejecuta (un programa en Python sin dependencias obligatorias, construido desde cero para un ecosistema privado)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-109-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** **Madurez: andamiaje.** El descubrimiento por manifiesto, la comparación de versiones, la instalación/actualización atómica-por-verificación y el registro de evidencia están probados (109 pruebas) contra la forma real del manifiesto de A.R.M.O.R.; nunca ha instalado ni actualizado un repositorio de A.R.M.O.R. real de principio a fin, porque todos son privados y eso exige un GITHUB_TOKEN real que este programa aún no ha recibido.

---

## 🎯 Descripción general

* **Descubrimiento, sin lista fija:** una carpeta local se une en cuanto lleva un `armor.project.json` válido que declara `ecosystem: "A.R.M.O.R."`; en remoto, se revisa igual cada repositorio que un `GITHUB_TOKEN` pueda ver en GitHub - todos los repositorios de A.R.M.O.R. son privados, así que ese token es obligatorio en todo momento, sin el respaldo de 60 peticiones a la hora al que recurriría un ecosistema público.
* **Instalar y actualizar, nunca en el sitio:** una actualización se construye y verifica primero en un clon de ensayo independiente, y solo se promueve -dos renombrados de carpeta, la instalación anterior guardada como copia de seguridad- cuando esa construcción realmente tiene éxito; un cambio local de verdad sin commitear se rechaza sin más, nunca se descarta en silencio.
* **Evidencia:** cada intento, con éxito o no, añade una línea a un registro local con el proyecto, la versión y el commit antes y después, y el motivo de un fallo.
* **Una CLI y una interfaz de escritorio opcional:** `armor-updater status`/`install`/`update`, y una interfaz Qt Quick (`pip install ".[gui]"`) en los siete idiomas del ecosistema.

## 📂 Estructura del repositorio

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client (remote, GITHUB_TOKEN required), install (atomic staging-clone
│                       update), evidence, main (CLI), settings, version_parse, i18n, gui/qt_gui/qml (optional Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), bump_version.py
├── tests/              9 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Entorno de desarrollo

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 109 tests
armor-updater status                                    # local + GitHub state of every repository (needs GITHUB_TOKEN)
armor-updater install ARMOR-NETWORK                     # clone and build one repository that is not installed yet
armor-updater update ARMOR-NETWORK                      # atomic-by-verification update
```

See `docs/CLI_REFERENCE.md`.

Ver `CONTRIBUTING.md` para saber cómo se une un repositorio al ecosistema que describe `armor.project.json`.

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware del nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nodo eléctrico: contadores, el mensaje de las lecturas de la red y las reglas para maniobrar
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Panel táctil: el estado del sistema en una pantalla de pared, armar y reconocer alarmas, y el hogar del asistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador de sitio 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente Android del operador con radar 2D/3D en vivo
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferencia visual que explica sus decisiones y nunca actúa
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
