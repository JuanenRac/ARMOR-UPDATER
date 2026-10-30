<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Bannière d'ARMOR-UPDATER" width="100%">
</p>

# 🛠️ ARMOR-UPDATER

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Détecte, installe et met à jour chaque dépôt A.R.M.O.R. sur la machine où il tourne (un programme Python sans dépendance obligatoire)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 ou ultérieure">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Langage">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Langues">
  <img src="https://img.shields.io/badge/Tests-288%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.6-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturité">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne aujourd'hui :** La découverte par manifeste, la comparaison des versions, la vérification de signature, l'installation et la mise à jour par étapes avec leur verrou, leur journal, leurs sauvegardes et leur retour arrière, le journal de preuves et les tables de l'interface en huit langues sont testés (288 tests), et l'interface Qt Quick a tourné sous Windows. Elle n'a pas été exécutée de bout en bout sur chaque dépôt de la famille, et les installations qu'elle fait exigent `git` et les outils de compilation de chaque dépôt sur la machine.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.1.6` |
| Maturité | Établi |
| Rôle | Outil de bureau qui installe et met à jour la famille sur un PC, un projet à la fois |
| Technologie | Python 3.10+, git ; PySide6 (Qt Quick) facultatif |
| Tests | 288 (`python -m pytest tests -q`, environ six minutes) |
| Interfaces | `armor-updater --cli` avec `status`, `install`, `update`, `rollback` et `backups`, et une fenêtre Qt Quick en huit langues |
| Fonctionne sur | Un PC avec Python et git (la fenêtre n'a tourné que sous Windows) |
| Sur matériel réel | Sans objet : c'est un programme de bureau ; son interface Qt Quick a été exécutée sous Windows |
| Licence | GPL-3.0-or-later |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Sécurité](#-sécurité-et-protection) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Dépannage](#-dépannage) · [Structure](#-structure-du-dépôt) · [Liés](#-projets-liés)

## 🚦 État du projet

Chaque ligne est une partie de ce dépôt et le feu dit où elle en est aujourd'hui. Elle est écrite d'après ce que le dépôt peut montrer (tests, compilations, exécutions), pas d'après ce qui est prévu.

🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 À moitié fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas

| Domaine | État | Ce que cela veut dire ici |
|---|---|---|
| Logiciel | 🟡 | La découverte des manifestes, la comparaison des versions et l'installation et mise à jour par étapes fonctionnent ; elles n'ont pas été exécutées de bout en bout contre tous les dépôts de la famille. |
| Tests | 🟢 | 288 tests réussissent (`python -m pytest tests -q`) : la découverte, la comparaison des versions, la vérification de la signature, l'installation par étapes avec son verrou, son journal, ses sauvegardes et son retour arrière, le journal de preuves et les tables des huit langues. |
| Interface | 🟡 | L'interface Qt Quick n'a été exécutée que sous Windows. |
| Sécurité | 🟡 | La vérification de la signature et le journal de preuves sont testés sur l'hôte ; il n'y a pas eu de revue indépendante. |
| Mises à jour | 🟡 | Les installations qu'il fait demandent `git` et les outils de compilation propres à chaque dépôt sur la machine. |
| Documentation | 🟢 | Huit langues et le journal des modifications sont à jour. |

## 🎯 Présentation

* **Découverte, sans liste fixe :** un dossier local rejoint l'écosystème dès qu'il porte un `armor.project.json` valide déclarant `ecosystem: "A.R.M.O.R."` ; à distance, chaque dépôt public du compte est examiné de la même façon. Un `GITHUB_TOKEN` est facultatif : il relève seulement la limite de 60 requêtes par heure de GitHub.
* **Installer et mettre à jour, jamais sur place :** un nouveau projet et une mise à jour sont d'abord construits et vérifiés dans un clone de préparation indépendant, puis promus seulement - deux renommages journalisés, la copie remplacée gardée sous `.armor-updater/backups/` (les trois plus récentes) - quand cette construction réussit ; une mise à jour vers le commit déjà installé ne fait rien ; une vraie modification locale non validée est refusée net, jamais écartée en silence ; une panne entre les renommages est réparée à l'exécution suivante, et `rollback` remet la copie la plus récente.
* **Un à la fois, et dans l'ordre :** un verrou empêche deux outils de travailler ensemble sur un espace de travail ; un lot commence par ARMOR-COMMON (toute construction en a besoin) et un projet n'est pas construit sans lui.
* **Preuves :** chaque tentative, réussie ou non, ajoute une ligne à un journal local avec le projet, la version et le commit avant et après, et la raison d'un échec.
* **Prérequis :** un manifeste peut lister, dans le champ facultatif `requires`, les projets à installer d'abord ; un lot les place en premier, et une installation ou une mise à jour est refusée avec un message clair, dans la langue de la fenêtre, si l'un d'eux manque.
* **Signatures, avertir par défaut :** une révision sans signature valide est tout de même installée ou mise à jour, et la fenêtre comme la ligne de commande indiquent qu'elle n'est pas signée ; choisir *exiger* dans les réglages (`"signature_policy": "require"`) la refuse à la place.
* **Copies précédentes :** la fenêtre peut restaurer la copie précédente d'un projet ou supprimer les copies conservées, et `status` indique combien il y en a et l'espace disque qu'elles occupent.
* **Une CLI et une interface de bureau optionnelle :** `armor-updater status`/`install`/`update`, et une interface Qt Quick (`pip install ".[gui]"`) dans les huit langues de l'écosystème.

## 🧩 Rôle dans A.R.M.O.R.

ARMOR-UPDATER est l'outil de bureau pour qui garde une copie de la famille sur un PC : il trouve les dépôts A.R.M.O.R. de la machine, les compare à GitHub et installe ou met à jour un par un, en vérifiant avant de remplacer quoi que ce soit. Il est distinct des mises à jour qu'[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) pilote sur le CM5 (celles-ci passent par [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)) : celui-ci est pour la machine d'un développeur.

| Il parle à | Comment | Pour quoi faire |
|---|---|---|
| Dossier de travail local | dossiers avec un `armor.project.json` valide | ce qui est installé et en quelle version |
| GitHub | `api.github.com`, `raw.githubusercontent.com` et git ; `GITHUB_TOKEN` facultatif | la dernière version de chaque dépôt du compte |
| ARMOR-COMMON | un projet peut le lister dans `requires` | il passe en premier dans chaque lot : chaque build en a besoin |
| ARMOR-DEVOPS | séparé | les mises à jour que ARMOR-STUDIO pilote sur le CM5 passent par lui, pas par cet outil |

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 Sécurité et protection

| Menace | Défense |
|---|---|
| Du code compromis est installé | Les commits sont vérifiés contre les signataires de `data/allowed_signers` (format OpenSSH) dont l'empreinte est épinglée dans `signature.py` ; modifier le fichier sans l'épingle fait échouer toute vérification (fermé) ; `signature_policy` vaut `warn` (défaut : installe et dit que ce n'est pas signé) ou `require` (refuse) |
| Une installation à moitié faite ou un remplacement en place | Jamais en place : tout est construit et vérifié dans un clone de préparation indépendant et promu par deux renommages journalisés (`promotion.json`) ; la copie remplacée est gardée dans `.armor-updater/backups/` (les trois plus récentes) |
| Deux mises à jour sur un même dossier | Un verrou (`.armor-updater/lock`) qui expire après 6 heures |
| Une dépendance non construite | ARMOR-COMMON passe en premier et un projet n'est pas construit sans lui ; le champ facultatif `requires` du manifeste ordonne un lot et refuse une installation avec un message clair dans la langue de la fenêtre |
| Modifications locales perdues | Une mise à jour vers le commit déjà installé ne fait rien ; une modification locale réellement non validée est refusée net |
| Une fausse découverte | Un projet ne compte qu'avec un `armor.project.json` valide qui déclare `ecosystem: "A.R.M.O.R."` ; à distance, chaque dépôt public du compte est vérifié de même |
| GitHub lent ou en panne | Délai de 10 s, jusqu'à 8 à la fois, 3 nouvelles tentatives (attente de base 0,5 s), `ls-remote` 20 s ; le retard de quelques minutes de `raw.githubusercontent.com` est prévu |

Chaque tentative, réussie ou non, ajoute une ligne au journal de preuves local (projet, version et commit avant et après, raison d'un échec). Les installations demandent `git` et les outils de construction de chaque dépôt ; la signature n'est qu'avertie sauf si l'on choisit `require` ; il n'a pas été exécuté contre tous les dépôts de la famille de bout en bout et il n'y a pas eu de revue indépendante.

## 🔌 Interfaces

| Route | Authentification | Ce qu'elle fait |
|---|---|---|
| `armor-updater --cli status` | - | ce qui est installé, sa version et la dernière sur GitHub ; `--workspace D`, `--offline` (local seulement), `--notes` (les vraies notes de chaque projet), `--json` (lisible par machine) |
| `armor-updater --cli install <project>` | - | clone, construit et installe UN projet pas encore installé ; `--no-build` clone seulement |
| `armor-updater --cli update <project>` | - | met à jour un projet installé, construit et vérifié avant d'être mis en place ; `--no-build` récupère seulement |
| `armor-updater --cli rollback <project>` | - | remet la copie la plus récente du dépôt remplacé |
| `armor-updater --cli backups [<project>]` | - | liste les copies des dépôts remplacés et le disque qu'elles occupent ; `--prune N` garde les N plus récentes de chacun |
| `armor-updater --version` | - | la version de l'outil |

La fenêtre (Qt Quick, `pip install ".[gui]"`, lancée sous Windows par `run-gui.vbs`) affiche le même état, installe et met à jour un projet, restaure la copie précédente d'un projet ou supprime les copies gardées, et dit quand une révision n'est pas signée ; elle est rédigée en huit langues (`i18n.py`, `i18n_pt.py`, `i18n_recovery.py`, `result_text.py`) et n'a tourné que sous Windows. Référence complète : [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) et [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md).

## ⚙️ Configuration

| Réglage | Par défaut | Ce qu'il fait |
|---|---|---|
| `--workspace` | le dossier parent de l'outil | la racine du dossier de travail à parcourir |
| `GITHUB_TOKEN` | facultatif | relève la limite de GitHub de 60 requêtes par heure ; il n'est que lu, jamais écrit |
| `signature_policy` | warn | `warn` installe et dit que ce n'est pas signé ; `require` refuse ; gardé dans `~/.armor_updater_settings.json` |
| Copies gardées | 3 | les trois plus récentes de chaque projet ; `backups --prune N` le change |
| Verrou | 6 h | un verrou plus ancien est ignoré |

`.env.example` montre les variables que la construction d'un dépôt peut lire. La langue de la fenêtre suit `~/.armor_updater_settings.json` (et l'ancien `~/.armor_updater_lang.json`).

## 🚀 Démarrage rapide

**Prérequis :** Python 3.10+, `git` et les outils de construction des dépôts que vous installez ; facultatif : PySide6 pour la fenêtre de bureau.

```bash
pip install -e ".[dev]"                     # ou ".[dev,gui]" pour la fenêtre Qt Quick facultative
python -m pytest tests -q                   # 288 tests, environ six minutes
armor-updater --cli status                  # état local et GitHub de chaque dépôt
armor-updater --cli install ARMOR-NETWORK   # clone, construit et installe un dépôt pas encore installé
armor-updater --cli update ARMOR-NETWORK    # met à jour un projet installé (construit et vérifié avant mise en place)
armor-updater --cli rollback ARMOR-NETWORK  # remet la copie la plus récente d'un dépôt remplacé
```

Voir [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

## 🧪 Tests

```powershell
python -m pytest tests -q  # 288 tests, environ six minutes
python -I tools/armor_ci_validate.py
```

| Domaine | Ce qu'il couvre |
|---|---|
| Découverte et versions | le manifeste, le registre, la détection locale et distante, l'analyse des versions et le client GitHub |
| Installation et mise à jour | la préparation, le verrou, le journal, les copies et le retour arrière, les prérequis et le journal de preuves |
| Signatures | les clés épinglées, l'échec fermé et les deux politiques |
| Ligne de commande | `status`, `install`, `update`, `rollback` et `backups` avec leurs options |
| Langues et fenêtre | les huit langues (`test_i18n.py`) et les textes de chaque résultat |

`python -m unittest` n'en trouve que trois : la suite est écrite pour pytest (`conftest.py` est dans `tests/`) et dure près de six minutes. GitHub Actions exécute la base A.R.M.O.R. à chaque push et pull request : la validation du manifeste, de la version, du journal des modifications et de la parité des README, puis le build et les tests propres au projet.

## 🏗️ Compilation et publication

C'est du Python pur : rien à compiler (`pip install -e .`). La version se trouve dans `pyproject.toml`, dans `armor.project.json` et dans le badge du README (lu depuis le manifeste) ; chaque version a son entrée dans [CHANGELOG.md](CHANGELOG.md). Les versions sont publiées sur GitHub.

## 🩺 Dépannage

| Vous voyez | Parce que | Faites |
|---|---|---|
| Une mise à jour dit qu'il ne s'est rien passé | le projet est déjà au commit que GitHub a | rien à faire |
| Une mise à jour est refusée à cause de modifications locales | le dépôt a une modification non validée | validez-la ou mettez-la de côté, puis mettez à jour |
| Il dit qu'un prérequis n'est pas installé | le manifeste le liste dans `requires` | installez d'abord ce projet (un lot les ordonne déjà) |
| La fenêtre ou la ligne de commande dit que la révision n'est pas signée | `signature_policy` vaut `warn`, donc il installe et le dit | choisissez `require` dans les réglages pour refuser les révisions non signées |
| Une mise à jour a cassé quelque chose | la nouvelle révision se construit mais se comporte mal | `armor-updater --cli rollback <projet>` remet la copie la plus récente |

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   le manifeste, la liste, le catalogue
│   ├── detect.py github_client.py version_parse.py            découverte locale et distante, versions
│   ├── install.py git_ops.py staging.py                       installation et mise à jour par étapes
│   ├── promotion.py releases.py deploy_category.py            verrou, journal, copies, dispositions
│   ├── signature.py                                           mises à jour signées, clés épinglées
│   ├── evidence.py settings.py console_flags.py               le journal, les réglages, les options
│   ├── main.py                                                la ligne de commande
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     les huit langues
│   ├── gui.py qt_gui.py qml/                                  la fenêtre Qt Quick facultative
│   └── data/ assets/                                          allowed_signers ; l'icône
├── tests/                                                     288 tests en 25 modules
├── docs/                                                      CLI_REFERENCE.md, QML_DESKTOP_GUI.md
├── tools/                                                     les vérifications CI, le lanceur et generate_app_icon.py
├── images/                                                    bannière, icône et images du README
├── .github/                                                   workflow CI, avis au tableau de bord, modèles d'issues et de pull requests
├── armor.project.json                                         manifeste : version, rôle, maturité
├── pyproject.toml                                             métadonnées du paquet, entrées
├── CHANGELOG.md                                               ce qui a changé à chaque version
├── run-gui.vbs                                                ouvre la fenêtre sous Windows sans console
├── run.sh run.bat                                             démarrer, flux partagé
├── build.sh build.bat                                         construire et tester, flux partagé
├── build-test.sh build-test.bat                               construire, tester, empaqueter
├── test.sh test.bat                                           seulement les tests, jamais la version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Feuille de route et limites connues

**Limites connues aujourd'hui**

* La fenêtre Qt Quick n'a tourné que sous Windows.
* Il n'a pas été exécuté contre tous les dépôts de la famille de bout en bout.
* Les installations demandent `git` et les outils de construction de chaque dépôt.
* Pas de revue de sécurité indépendante.

**Prochainement**

* L'exécuter de bout en bout contre tous les dépôts de la famille, et sous Linux et macOS.

## 🌍 Langues

Le README et les textes existent en anglais, espagnol, français, italien, allemand, chinois, japonais et portugais européen.

## 🔗 Projets liés

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) est un système de sécurité périmétrique composé de dépôts indépendants. Chacun a sa propre version, ses propres tests et son propre README ; voici la famille :

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contrats de messages, validateurs, vecteurs de conformité et types générés
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware du nœud de terrain pour ESP32-S3 avec trois radars et son propre panneau web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocoles des onduleurs et batteries solaires et messages d'un nœud passerelle
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nœud électrique : compteurs, le message des mesures du réseau et les règles de commutation
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nœud et centrale d'alarme : zones, armement, temporisations, sirène et PIN, avec ou sans le serveur
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Panneau tactile : l'état du système sur un écran mural, armer et acquitter, et la maison de l'assistant vocal
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - Le réseau local : ses appareils, internet et ce qui change
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinateur central : télémétrie, alarmes, appareils, relevés solaires et caméras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web : caméras, radar, alarmes, énergie solaire et concepteur de site 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android de l'opérateur avec radar 2D/3D en direct
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Client opérateur iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politique d'inférence visuelle qui explique ses décisions et n'agit jamais
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zones de caméra, masques et règles de détection pour la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intentions vocales hors ligne avec une confirmation impossible à falsifier
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Boîtiers, électronique et matrice d'acceptation sur banc
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Déploiement, banc d'essai CM5, sauvegarde et TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulateur de télémétrie hors ligne avec des pannes reproductibles
* **ARMOR-UPDATER** (ce dépôt) - Détecte, installe et met à jour les propres dépôts de l'écosystème
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, base de sécurité et matrice des capacités

## 📚 Documentation

* [Référence de la ligne de commande](docs/CLI_REFERENCE.md) : chaque commande et option
* [La fenêtre Qt Quick](docs/QML_DESKTOP_GUI.md) : comment fonctionne la fenêtre de bureau
* [Matrice des capacités : ce qui est prouvé et ce qui ne l'est pas](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogue des projets : versions et dépendances entre les dépôts](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historique des modifications de ce dépôt](CHANGELOG.md)

## 🤝 Contribuer et communauté

* Avant une pull request, exécutez `python -I tools/armor_ci_validate.py` et les tests : les deux doivent réussir. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).
* Le README existe en huit langues et est généré à partir des sources d'ARMOR-DOCS : une modification du texte se fait là-bas.
* Une modification d'un message entre composants commence dans ARMOR-COMMON.
* Ne décrivez pas comme fonctionnant sur une carte ce qui a seulement été compilé.
* Signalez une vulnérabilité en privé : [SECURITY.md](SECURITY.md). Questions, idées et rapports : electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
