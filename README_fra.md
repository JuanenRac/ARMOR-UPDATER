<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-UPDATER banner" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-191-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.4-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne aujourd'hui:** La découverte par manifeste, la comparaison des versions, la vérification de signature, l'installation et la mise à jour par étapes avec leur verrou, leur journal, leurs sauvegardes et leur retour arrière, le journal de preuves et les tables de l'interface en huit langues sont testés (191 tests), et l'interface Qt Quick a tourné sous Windows. Elle n'a pas été exécutée de bout en bout sur chaque dépôt de la famille, et les installations qu'elle fait exigent `git` et les outils de compilation de chaque dépôt sur la machine.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.1.4` |
| Maturité | Établi |
| Tests | 191 (`python -m pytest tests -q`) |
| Technologie | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| Sur matériel réel | Sans objet : c'est un programme de bureau ; son interface Qt Quick a été exécutée sous Windows |

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

## 📂 Structure du dépôt

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              18 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Environnement de développement

**Prérequis:** Python 3.10+, `git` and the build tools of the repositories you install, optional: PySide6 for the desktop shell

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 191 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

Voir `docs/CLI_REFERENCE.md`.

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
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politique d'inférence visuelle qui explique ses décisions et n'agit jamais
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zones de caméra, masques et règles de détection pour la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intentions vocales hors ligne avec une confirmation impossible à falsifier
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Boîtiers, électronique et matrice d'acceptation sur banc
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Déploiement, banc d'essai CM5, sauvegarde et TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulateur de télémétrie hors ligne avec des pannes reproductibles
* **ARMOR-UPDATER** (ce dépôt) - Détecte, installe et met à jour les propres dépôts de l'écosystème
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, base de sécurité et matrice des capacités

## 📚 Documentation et communauté

Pour en savoir plus :

* [Matrice des capacités : ce qui est prouvé et ce qui ne l'est pas](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogue des projets : versions et dépendances entre les dépôts](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historique des modifications de ce dépôt](CHANGELOG.md)
* [Licence (GPL-3.0-or-later)](LICENSE)
* Questions, idées et rapports : electrohobby3d@gmail.com

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
