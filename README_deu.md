<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-UPDATER banner" width="100%">
</p>

# 🛠️ ARMOR-UPDATER

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  🇩🇪 <b>Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Erkennt, installiert und aktualisiert jedes A.R.M.O.R.-Repository auf dem Rechner, auf dem es läuft (ein Python-Programm ohne Pflichtabhängigkeiten)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-288-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Ehrlichkeitsprüfung - was heute läuft:** Die Manifest-Erkennung, der Versionsvergleich, die Signaturprüfung, die gestufte Installation und Aktualisierung mit Sperre, Journal, Sicherungen und Rückkehr, das Nachweisprotokoll und die Oberflächentabellen in acht Sprachen sind getestet (288 Tests), und die Qt-Quick-Oberfläche lief unter Windows. Sie wurde nicht gegen jedes Repository der Familie von Anfang bis Ende ausgeführt, und die Installationen brauchen `git` und die Build-Werkzeuge jedes Repositorys auf dem Rechner.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.1.5` |
| Reifegrad | Etabliert |
| Tests | 288 (`python -m pytest tests -q`) |
| Technik | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| Auf echter Hardware | Nicht zutreffend: es ist ein Desktop-Programm; seine Qt-Quick-Oberfläche wurde unter Windows ausgeführt |

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟡 | Die Manifest-Erkennung, der Versionsvergleich und die gestufte Installation und Aktualisierung funktionieren; sie wurden nicht durchgängig gegen jedes Repository der Familie ausgeführt. |
| Tests | 🟢 | 288 Tests bestehen (`python -m pytest tests -q`): die Erkennung, der Versionsvergleich, die Signaturprüfung, die gestufte Installation mit Sperre, Journal, Sicherungen und Rückfall, das Beweisprotokoll und die Tabellen der acht Sprachen. |
| Oberfläche | 🟡 | Die Qt-Quick-Oberfläche lief nur unter Windows. |
| Sicherheit | 🟡 | Die Signaturprüfung und das Beweisprotokoll sind auf dem Host getestet; es gab keine unabhängige Prüfung. |
| Aktualisierungen | 🟡 | Die Installationen, die er vornimmt, brauchen `git` und die eigenen Build-Werkzeuge jedes Repositorys auf dem Rechner. |
| Dokumentation | 🟢 | Acht Sprachen und das Änderungsprotokoll sind aktuell. |

## 🎯 Überblick

* **Erkennung ohne feste Liste:** Ein lokaler Ordner gehört dazu, sobald er ein gültiges `armor.project.json` mit `ecosystem: "A.R.M.O.R."` trägt; entfernt wird jedes öffentliche Repository des Kontos genauso geprüft. Ein `GITHUB_TOKEN` ist optional: Er hebt nur GitHubs Grenze von 60 Anfragen pro Stunde an.
* **Installieren und aktualisieren, nie an Ort und Stelle:** Ein neues Projekt und eine Aktualisierung werden zuerst in einem unabhängigen Staging-Klon gebaut und geprüft und erst danach übernommen - zwei protokollierte Umbenennungen, die ersetzte Kopie unter `.armor-updater/backups/` aufbewahrt (die drei neuesten) -, wenn der Build gelingt; eine Aktualisierung auf den schon installierten Commit tut nichts; eine echte nicht eingecheckte lokale Änderung wird glatt abgelehnt, nie stillschweigend verworfen; ein Absturz zwischen den Umbenennungen wird beim nächsten Lauf geheilt, und `rollback` stellt die neueste Kopie wieder her.
* **Eines nach dem anderen, und der Reihe nach:** Eine Sperre verhindert, dass zwei Updater gleichzeitig an einem Arbeitsbereich arbeiten; ein Stapel beginnt mit ARMOR-COMMON (jeder Build braucht es), und ein Projekt wird ohne es nicht gebaut.
* **Nachweis:** jeder Versuch, erfolgreich oder nicht, fügt einer lokalen Protokolldatei eine Zeile mit Projekt, Version und Commit davor und danach sowie dem Grund eines Fehlschlags hinzu.
* **Voraussetzungen:** Ein Manifest kann im optionalen Feld `requires` die Projekte nennen, die zuerst installiert sein müssen; eine Sammelaktion stellt sie voran, und eine Installation oder Aktualisierung wird mit einer klaren Meldung in der Sprache des Fensters abgelehnt, wenn eines davon fehlt.
* **Signaturen, standardmäßig warnen:** Eine Revision ohne gültige Signatur wird trotzdem installiert oder aktualisiert, und das Fenster wie die Befehlszeile weisen darauf hin, dass sie nicht signiert ist; wer in den Einstellungen *verlangen* wählt (`"signature_policy": "require"`), lehnt sie stattdessen ab.
* **Frühere Kopien:** Das Fenster kann die frühere Kopie eines Projekts wiederherstellen oder die aufbewahrten Kopien löschen, und `status` zeigt, wie viele es sind und wie viel Speicherplatz sie belegen.
* **Eine CLI und eine optionale Desktop-Oberfläche:** `armor-updater status`/`install`/`update`, sowie eine Qt-Quick-Oberfläche (`pip install ".[gui]"`) in den acht Sprachen des Ökosystems.

## 🧩 Rolle in A.R.M.O.R.

ARMOR-UPDATER ist das Desktop-Werkzeug für alle, die eine Kopie der Familie auf einem PC halten: Es findet die A.R.M.O.R.-Repositorys der Maschine, vergleicht sie mit GitHub und installiert oder aktualisiert eines nach dem anderen und prüft, bevor es etwas ersetzt. Es ist getrennt von den Updates, die [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) auf dem CM5 steuert (die laufen über [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)): dieses ist für die Maschine eines Entwicklers.

## 📂 Struktur des Repositorys

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              25 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Entwicklungsumgebung

**Voraussetzungen:** Python 3.10+, `git` und die Build-Werkzeuge der Repositories, die Sie installieren, optional: PySide6 für die Desktop-Oberfläche

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 288 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

Siehe `docs/CLI_REFERENCE.md`.

## 🔗 Verwandte Projekte

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) ist ein Perimeter-Sicherheitssystem aus unabhängigen Repositorys. Jedes hat eine eigene Version, eigene Tests und ein eigenes README; hier ist die Familie:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Nachrichtenverträge, Validierer, Konformitätsvektoren und generierte Typen
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Feldknoten-Firmware für ESP32-S3 mit drei Radaren und eigenem Web-Panel
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protokolle für Solar-Wechselrichter und -Batterien und die Nachrichten eines Gateway-Knotens
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Elektroknoten: Zähler, die Nachricht der Netzmesswerte und die Regeln fürs Schalten
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Alarmknoten und Alarmzentrale: Zonen, Scharfschalten, Verzögerungen, Sirene und PIN, mit dem Server oder ohne ihn
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Touch-Panel: der Systemzustand auf einem Wandbildschirm, Scharf- und Quittieren sowie das Zuhause des Sprachassistenten
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - Das lokale Netzwerk: seine Geräte, das Internet und was sich ändert
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Zentraler Koordinator: Telemetrie, Alarme, Geräte, Solarmesswerte und Kameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web-Konsole: Kameras, Radar, Alarme, Solarenergie und 2D/3D-Standortdesigner
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android-Bedienclient mit Live-Radar in 2D/3D
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone-Bedienclient
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Visuelle Inferenzrichtlinie, die ihre Entscheidungen erklärt und nie handelt
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Kamerazonen, Masken und Erkennungsregeln für den Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline-Sprachabsichten mit einer nicht fälschbaren Bestätigung
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Gehäuse, Elektronik und die Abnahmematrix am Prüfstand
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Bereitstellung, CM5-Prüfstand, Backup und TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline-Telemetriesimulator mit wiederholbaren Fehlern
* **ARMOR-UPDATER** (dieses Repository) - Erkennt, installiert und aktualisiert die eigenen Repositories des Ökosystems
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architektur, Sicherheitsgrundlage und die Fähigkeitsmatrix

## 📚 Dokumentation und Community

Hier gibt es mehr zu lesen:

* [Fähigkeitsmatrix: was belegt ist und was nicht](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Projektkatalog: Versionen und wie die Repositorys voneinander abhängen](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Änderungsverlauf dieses Repositorys](CHANGELOG.md)
* [Lizenz (GPL-3.0-or-later)](LICENSE)
* Fragen, Ideen und Meldungen: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - siehe [LICENSE](LICENSE).
