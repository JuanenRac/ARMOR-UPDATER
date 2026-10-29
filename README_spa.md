<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Banner de ARMOR-UPDATER" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 o posterior">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Lenguaje">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Idiomas">
  <img src="https://img.shields.io/badge/Tests-288%20passing-2ea44f.svg" alt="Pruebas">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Versión">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Madurez">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** El descubrimiento por manifiesto, la comparación de versiones, la comprobación de firma, la instalación y actualización por etapas con su bloqueo, su diario, sus copias y su vuelta atrás, el registro de evidencias y las tablas de la interfaz en ocho idiomas están probados (288 tests), y la interfaz Qt Quick se ha ejecutado en Windows. No se ha ejecutado contra todos los repositorios de la familia de principio a fin, y las instalaciones que hace necesitan `git` y las herramientas de compilación de cada repositorio en la máquina.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.1.5` |
| Madurez | Establecido |
| Función | Herramienta de escritorio que instala y actualiza la familia en un PC, un proyecto cada vez |
| Tecnología | Python 3.10+, git; PySide6 (Qt Quick) opcional |
| Pruebas | 288 (`python -m pytest tests -q`, unos seis minutos) |
| Interfaces | `armor-updater --cli` con `status`, `install`, `update`, `rollback` y `backups`, y una ventana Qt Quick en ocho idiomas |
| Funciona en | Un PC con Python y git (la ventana solo ha corrido en Windows) |
| En hardware real | No aplica: es un programa de escritorio; su interfaz Qt Quick se ha ejecutado en Windows |
| Licencia | GPL-3.0-or-later |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Seguridad](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Configuración](#-configuración) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Problemas](#-resolución-de-problemas) · [Estructura](#-estructura-del-repositorio) · [Relacionados](#-proyectos-relacionados)

## 🚦 Estado del proyecto

Cada línea es una parte de este repositorio y la luz dice hasta dónde llega hoy. Está escrito con lo que el repositorio puede demostrar (pruebas, compilaciones, ejecuciones), no con lo que está planeado.

🟢 Hecho y verificado · 🟡 Funciona, con límites conocidos · 🟠 Parcial o sin verificar todavía · 🔴 No hecho o no funciona

| Área | Estado | Qué significa aquí |
|---|---|---|
| Software | 🟡 | El descubrimiento de manifiestos, la comparación de versiones y la instalación y actualización por etapas funcionan; no se han ejecutado de principio a fin contra todos los repositorios de la familia. |
| Pruebas | 🟢 | Pasan 288 pruebas (`python -m pytest tests -q`): el descubrimiento, la comparación de versiones, la comprobación de la firma, la instalación por etapas con su bloqueo, diario, copias y vuelta atrás, el registro de evidencias y las tablas de los ocho idiomas. |
| Interfaz | 🟡 | La interfaz Qt Quick solo se ha ejecutado en Windows. |
| Seguridad | 🟡 | La comprobación de la firma y el registro de evidencias están probados en el host; no ha habido una revisión independiente. |
| Actualizaciones | 🟡 | Las instalaciones que hace necesitan `git` y las herramientas de compilación propias de cada repositorio en la máquina. |
| Documentación | 🟢 | Ocho idiomas y el historial de cambios están al día. |

## 🎯 Resumen

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

| Habla con | Cómo | Para qué |
|---|---|---|
| Carpeta de trabajo local | carpetas con un `armor.project.json` válido | qué está instalado y en qué versión |
| GitHub | `api.github.com`, `raw.githubusercontent.com` y git; `GITHUB_TOKEN` opcional | la última versión de cada repositorio de la cuenta |
| ARMOR-COMMON | un proyecto puede listarlo en `requires` | va primero en cada lote: toda compilación lo necesita |
| ARMOR-DEVOPS | aparte | las actualizaciones que ARMOR-STUDIO dirige en la CM5 pasan por él, no por esta herramienta |

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 Seguridad y protección

| Amenaza | Defensa |
|---|---|
| Se instala código comprometido | Los commits se comprueban con firmantes de `data/allowed_signers` (formato OpenSSH) cuya huella está fijada en `signature.py`; cambiar el fichero sin cambiar la huella hace fallar toda comprobación (cierra en falso); `signature_policy` es `warn` (defecto: instala y dice que no está firmado) o `require` (rechaza) |
| Una instalación a medias o un reemplazo en caliente | Nunca en sitio: todo se construye y verifica en un clon de preparación independiente y se promueve con dos renombrados con diario (`promotion.json`); la copia sustituida se guarda en `.armor-updater/backups/` (las tres más nuevas) |
| Dos actualizadores en una misma carpeta | Un bloqueo (`.armor-updater/lock`) que caduca a las 6 horas |
| Una dependencia sin construir | ARMOR-COMMON va primero y un proyecto no se construye sin él; el campo opcional `requires` del manifiesto ordena un lote y rechaza una instalación con un mensaje claro en el idioma de la ventana |
| Cambios locales perdidos | Una actualización al commit ya instalado no hace nada; un cambio local realmente sin guardar se rechaza de plano |
| Un descubrimiento falso | Un proyecto solo cuenta con un `armor.project.json` válido que declare `ecosystem: "A.R.M.O.R."`; en remoto, cada repositorio público de la cuenta se comprueba igual |
| GitHub lento o caído | Tiempo de espera de 10 s, hasta 8 a la vez, 3 reintentos (espera base 0,5 s), `ls-remote` 20 s; se tiene en cuenta el retraso de minutos de `raw.githubusercontent.com` |

Cada intento, bueno o malo, añade una línea al registro local de evidencias (proyecto, versión y commit antes y después, razón del fallo). Las instalaciones necesitan `git` y las herramientas de construcción de cada repositorio; la firma solo avisa salvo que se elija `require`; no se ha ejecutado contra todos los repositorios de la familia de punta a punta y no ha habido revisión independiente.

## 🔌 Interfaces

| Ruta | Autenticación | Qué hace |
|---|---|---|
| `armor-updater --cli status` | - | qué está instalado, su versión y la última en GitHub; `--workspace D`, `--offline` (solo local), `--notes` (las notas reales de cada proyecto), `--json` (legible por máquina) |
| `armor-updater --cli install <project>` | - | clona, construye e instala UN proyecto que aún no está instalado; `--no-build` solo clona |
| `armor-updater --cli update <project>` | - | actualiza uno instalado, construido y verificado antes de ponerlo en su sitio; `--no-build` solo trae los cambios |
| `armor-updater --cli rollback <project>` | - | devuelve la copia más nueva del proyecto sustituido |
| `armor-updater --cli backups [<project>]` | - | lista las copias de proyectos sustituidos y el disco que ocupan; `--prune N` conserva las N más nuevas de cada uno |
| `armor-updater --version` | - | la versión de la herramienta |

La ventana (Qt Quick, `pip install ".[gui]"`, que en Windows arranca `run-gui.vbs`) muestra el mismo estado, instala y actualiza un proyecto, restaura la copia anterior de un proyecto o borra las copias guardadas, y dice cuándo una revisión no está firmada; está redactada en ocho idiomas (`i18n.py`, `i18n_pt.py`, `i18n_recovery.py`, `result_text.py`) y solo se ha ejecutado en Windows. Referencia completa: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) y [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md).

## ⚙️ Configuración

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| `--workspace` | la carpeta padre de la herramienta | la raíz de la carpeta de trabajo que se escanea |
| `GITHUB_TOKEN` | opcional | sube el límite de GitHub de 60 peticiones por hora; solo se lee, nunca se escribe |
| `signature_policy` | warn | `warn` instala y dice que no está firmado; `require` rechaza; se guarda en `~/.armor_updater_settings.json` |
| Copias guardadas | 3 | las tres más nuevas de cada proyecto; `backups --prune N` lo cambia |
| Bloqueo | 6 h | un bloqueo más viejo se ignora |

`.env.example` muestra las variables que puede leer la construcción de un repositorio. El idioma de la ventana sigue a `~/.armor_updater_settings.json` (y al antiguo `~/.armor_updater_lang.json`).

## 🚀 Inicio rápido

**Requisitos:** Python 3.10+, `git` y las herramientas de construcción de los repositorios que instales; opcional: PySide6 para la ventana de escritorio.

```bash
pip install -e ".[dev]"                     # o ".[dev,gui]" para la ventana Qt Quick opcional
python -m pytest tests -q                   # 288 pruebas, unos seis minutos
armor-updater --cli status                  # estado local y de GitHub de cada repositorio
armor-updater --cli install ARMOR-NETWORK   # clona, construye e instala un repositorio que aún no está instalado
armor-updater --cli update ARMOR-NETWORK    # actualiza uno instalado (construido y verificado antes de ponerlo)
armor-updater --cli rollback ARMOR-NETWORK  # devuelve la copia más nueva de un proyecto sustituido
```

Mira [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

## 🧪 Pruebas

```powershell
python -m pytest tests -q  # 288 pruebas, unos seis minutos
python -I tools/armor_ci_validate.py
```

| Área | Qué cubre |
|---|---|
| Descubrimiento y versiones | el manifiesto, el registro, la detección local y remota, el análisis de versiones y el cliente de GitHub |
| Instalación y actualización | la preparación, el bloqueo, el diario, las copias y la vuelta atrás, los requisitos y el registro de evidencias |
| Firmas | las claves fijadas, el fallo cerrado y las dos políticas |
| Línea de órdenes | `status`, `install`, `update`, `rollback` y `backups` con sus opciones |
| Idiomas y ventana | los ocho idiomas (`test_i18n.py`) y los textos de cada resultado |

`python -m unittest` solo encuentra tres: la batería está escrita para pytest (`conftest.py` está en `tests/`) y tarda casi seis minutos. GitHub Actions ejecuta la base de A.R.M.O.R. en cada push y pull request: la validación del manifiesto, la versión, el registro de cambios y la paridad de los README, y luego la compilación y las pruebas del propio proyecto.

## 🏗️ Compilación y publicación

Es Python puro: no hay nada que compilar (`pip install -e .`). La versión vive en `pyproject.toml`, en `armor.project.json` y en la insignia del README (leída del manifiesto); cada versión tiene su entrada en [CHANGELOG.md](CHANGELOG.md). Las versiones se publican en GitHub.

## 🩺 Resolución de problemas

| Ves | Porque | Haz |
|---|---|---|
| Una actualización dice que no pasó nada | el proyecto ya está en el commit que tiene GitHub | nada que hacer |
| Una actualización se rechaza por cambios locales | el proyecto tiene un cambio sin commit | haz commit o guárdalo aparte y actualiza |
| Dice que un requisito no está instalado | el manifiesto lo lista en `requires` | instala antes ese proyecto (un lote ya los ordena) |
| La ventana o la línea de órdenes dice que la revisión no está firmada | `signature_policy` es `warn`, así que instala y lo dice | elige `require` en los ajustes para rechazar revisiones sin firma |
| Una actualización estropeó algo | la nueva revisión compila pero no se comporta bien | `armor-updater --cli rollback <proyecto>` devuelve la copia más nueva |

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   el manifiesto, la lista, el catálogo
│   ├── detect.py github_client.py version_parse.py            descubrimiento local y remoto, versiones
│   ├── install.py git_ops.py staging.py                       instalación y actualización por etapas
│   ├── promotion.py releases.py deploy_category.py            bloqueo, diario, copias, disposiciones
│   ├── signature.py                                           actualizaciones firmadas, claves fijadas
│   ├── evidence.py settings.py console_flags.py               el registro, los ajustes, las opciones
│   ├── main.py                                                la línea de órdenes
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     los ocho idiomas
│   ├── gui.py qt_gui.py qml/                                  la ventana Qt Quick opcional
│   └── data/ assets/                                          allowed_signers; el icono
├── tests/                                                     288 pruebas en 25 módulos
├── docs/                                                      CLI_REFERENCE.md, QML_DESKTOP_GUI.md
├── tools/                                                     las comprobaciones de CI, el lanzador y generate_app_icon.py
├── images/                                                    banner, icono y las imágenes del README
├── .github/                                                   flujo de CI, aviso al panel, plantillas de incidencias y pull requests
├── armor.project.json                                         manifiesto: versión, función, madurez
├── pyproject.toml                                             metadatos del paquete, entradas
├── CHANGELOG.md                                               qué cambió en cada versión
├── run-gui.vbs                                                abre la ventana en Windows sin consola
├── run.sh run.bat                                             arrancar, flujo compartido
├── build.sh build.bat                                         construir y probar, flujo compartido
├── build-test.sh build-test.bat                               construir, probar y empaquetar
├── test.sh test.bat                                           solo las pruebas, nunca la versión
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Hoja de ruta y límites conocidos

**Límites conocidos hoy**

* La ventana Qt Quick solo se ha ejecutado en Windows.
* No se ha ejecutado contra todos los repositorios de la familia de punta a punta.
* Las instalaciones necesitan `git` y las herramientas de construcción de cada repositorio.
* Sin revisión de seguridad independiente.

**Lo siguiente**

* Ejecutarlo de punta a punta contra todos los repositorios de la familia y en Linux y macOS.

## 🌍 Idiomas

El README y los textos existen en inglés, español, francés, italiano, alemán, chino, japonés y portugués de Portugal.

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware de nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nodo eléctrico: medidores, el mensaje de las lecturas de la red y las reglas de maniobra
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nodo y panel de alarma: zonas, armado, retardos, sirena y PIN, con el servidor o sin él
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Panel táctil: el estado del sistema en una pantalla de pared, armar y reconocer, y el hogar del asistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador 2D/3D del emplazamiento
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente de operador Android con radar 2D/3D en vivo
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Cliente de operador para iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferencia visual que explica sus decisiones y nunca actúa
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de cámara, máscaras y reglas de detección para la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenciones de voz sin conexión con una confirmación que no se puede falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Cajas, electrónica y la matriz de aceptación en banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Despliegue, el banco de pruebas de la CM5, copias de seguridad y TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetría sin conexión con fallos repetibles
* **ARMOR-UPDATER** (este repositorio) - Detecta, instala y actualiza los repositorios del propio ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitectura, base de seguridad y la matriz de capacidades

## 📚 Documentación

* [Referencia de la línea de órdenes](docs/CLI_REFERENCE.md): cada orden y opción
* [La ventana Qt Quick](docs/QML_DESKTOP_GUI.md): cómo funciona la ventana de escritorio
* [Matriz de capacidades: qué está demostrado y qué no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de proyectos: versiones y cómo dependen unos repositorios de otros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registro de cambios de este repositorio](CHANGELOG.md)

## 🤝 Contribuir y comunidad

* Antes de un pull request ejecuta `python -I tools/armor_ci_validate.py` y las pruebas: ambos deben pasar. Mira [CONTRIBUTING.md](CONTRIBUTING.md) y el [código de conducta](CODE_OF_CONDUCT.md).
* El README existe en ocho idiomas y se genera desde las fuentes de ARMOR-DOCS: un cambio de texto se hace allí.
* Un cambio en un mensaje entre componentes empieza en ARMOR-COMMON.
* No describas como funcionando en una placa lo que solo se ha compilado.
* Informa de una vulnerabilidad en privado: [SECURITY.md](SECURITY.md). Preguntas, ideas e informes: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
