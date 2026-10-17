<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-UPDATER banner" width="100%">
</p>

# 🛠️ ARMOR-UPDATER

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  🇮🇹 <b>Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Rileva, installa e aggiorna ogni repository A.R.M.O.R. sulla macchina in cui gira (un programma Python senza dipendenze obbligatorie)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-140-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Controllo di onestà - cosa funziona oggi:** La scoperta per manifesto, il confronto delle versioni, il controllo della firma, l'installazione e l'aggiornamento a tappe con il loro blocco, il loro diario, le copie e il ritorno indietro, il registro delle prove e le tabelle dell'interfaccia in otto lingue sono testati (140 test), e l'interfaccia Qt Quick è stata eseguita su Windows. Non è stata eseguita su ogni repository della famiglia da cima a fondo, e le installazioni che fa richiedono `git` e gli strumenti di compilazione di ciascun repository sulla macchina.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.1.2` |
| Maturità | Consolidato |
| Test | 140 (`python -m pytest tests -q`) |
| Tecnologia | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| Su hardware reale | Non applicabile: è un programma da scrivania; la sua interfaccia Qt Quick è stata eseguita su Windows |

## 🎯 Panoramica

* **Scoperta, senza elenco fisso:** una cartella locale entra appena porta un `armor.project.json` valido che dichiara `ecosystem: "A.R.M.O.R."`; da remoto, ogni repository pubblico dell'account è controllato allo stesso modo. Un `GITHUB_TOKEN` è facoltativo: alza solo il limite di 60 richieste l'ora di GitHub.
* **Installare e aggiornare, mai sul posto:** un nuovo progetto e un aggiornamento sono prima costruiti e verificati in un clone di prova indipendente, e promossi solo - due rinominazioni registrate, la copia sostituita conservata in `.armor-updater/backups/` (le tre più recenti) - quando quella costruzione riesce; un aggiornamento al commit già installato non fa nulla; una vera modifica locale non salvata è rifiutata senza mezzi termini, mai scartata in silenzio; un guasto tra le rinominazioni viene riparato alla prossima esecuzione, e `rollback` rimette la copia più recente.
* **Uno alla volta, e in ordine:** un blocco impedisce a due aggiornatori di lavorare insieme su uno spazio di lavoro; un lotto parte da ARMOR-COMMON (ogni costruzione ne ha bisogno) e un progetto non viene costruito senza di esso.
* **Prove:** ogni tentativo, riuscito o no, aggiunge una riga a un registro locale con il progetto, la versione e il commit prima e dopo, e il motivo di un fallimento.
* **Una CLI e un'interfaccia desktop opzionale:** `armor-updater status`/`install`/`update`, e un'interfaccia Qt Quick (`pip install ".[gui]"`) nelle otto lingue dell'ecosistema.

## 🧩 Ruolo in A.R.M.O.R.

ARMOR-UPDATER è lo strumento da scrivania per chi tiene una copia della famiglia su un PC: trova i repository A.R.M.O.R. della macchina, li confronta con GitHub e installa o aggiorna uno alla volta, verificando prima di sostituire qualcosa. È distinto dagli aggiornamenti che [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) guida sulla CM5 (quelli passano per [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)): questo è per la macchina di uno sviluppatore.

## 📂 Struttura del repository

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              13 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Ambiente di sviluppo

**Requisiti:** Python 3.10+, `git` and the build tools of the repositories you install, optional: PySide6 for the desktop shell

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 140 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

Vedi `docs/CLI_REFERENCE.md`.

## 🔗 Progetti correlati

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) è un sistema di sicurezza perimetrale fatto di repository indipendenti. Ognuno ha la propria versione, i propri test e il proprio README; ecco la famiglia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratti dei messaggi, validatori, vettori di conformità e tipi generati
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware del nodo di campo per ESP32-S3 con tre radar e un proprio pannello web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolli di inverter e batterie solari e messaggi di un nodo gateway
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nodo elettrico: contatori, il messaggio delle letture della rete e le regole di manovra
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - Nodo e centrale d'allarme: zone, inserimento, ritardi, sirena e PIN, con il server o senza
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Pannello touch: lo stato del sistema su uno schermo a parete, attivare e riconoscere gli allarmi, e la casa dell'assistente vocale
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La rete locale: i suoi dispositivi, internet e ciò che cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinatore centrale: telemetria, allarmi, dispositivi, letture solari e telecamere
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web: telecamere, radar, allarmi, energia solare e progettista del sito 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android dell'operatore con radar 2D/3D in tempo reale
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politica di inferenza visiva che spiega le sue decisioni e non agisce mai
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zone delle telecamere, maschere e regole di rilevamento per la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenti vocali offline con una conferma impossibile da falsificare
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Contenitori, elettronica e matrice di accettazione da banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Distribuzione, banco di prova CM5, backup e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulatore di telemetria offline con guasti ripetibili
* **ARMOR-UPDATER** (questo repository) - Rileva, installa e aggiorna i repository stessi dell'ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architettura, base di sicurezza e matrice delle capacità

## 📚 Documentazione e comunità

Dove leggere di più:

* [Matrice delle capacità: cosa è provato e cosa no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogo dei progetti: versioni e dipendenze tra i repository](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Cronologia delle modifiche di questo repository](CHANGELOG.md)
* [Licenza (GPL-3.0-or-later)](LICENSE)
* Domande, idee e segnalazioni: electrohobby3d@gmail.com

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
