<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Banner di ARMOR-UPDATER" width="100%">
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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 o successiva">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Linguaggio">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Lingue">
  <img src="https://img.shields.io/badge/Tests-288%20passing-2ea44f.svg" alt="Test">
  <img src="https://img.shields.io/badge/Version-0.1.6-0f6cbd.svg" alt="Versione">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturità">
</p>

---

**Controllo di onestà - cosa funziona oggi:** La scoperta per manifesto, il confronto delle versioni, il controllo della firma, l'installazione e l'aggiornamento a tappe con il loro blocco, il loro diario, le copie e il ritorno indietro, il registro delle prove e le tabelle dell'interfaccia in otto lingue sono testati (288 test), e l'interfaccia Qt Quick è stata eseguita su Windows. Non è stata eseguita su ogni repository della famiglia da cima a fondo, e le installazioni che fa richiedono `git` e gli strumenti di compilazione di ciascun repository sulla macchina.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.1.6` |
| Maturità | Consolidato |
| Ruolo | Strumento desktop che installa e aggiorna la famiglia su un PC, un progetto alla volta |
| Tecnologia | Python 3.10+, git; PySide6 (Qt Quick) facoltativo |
| Test | 288 (`python -m pytest tests -q`, circa sei minuti) |
| Interfacce | `armor-updater --cli` con `status`, `install`, `update`, `rollback` e `backups`, e una finestra Qt Quick in otto lingue |
| Gira su | Un PC con Python e git (la finestra ha girato solo su Windows) |
| Su hardware reale | Non applicabile: è un programma da scrivania; la sua interfaccia Qt Quick è stata eseguita su Windows |
| Licenza | GPL-3.0-or-later |

**Vai a:** [Panoramica](#-panoramica) · [Architettura](#-architettura) · [Sicurezza](#-sicurezza-e-protezione) · [Interfacce](#-interfacce) · [Configurazione](#-configurazione) · [Avvio rapido](#-avvio-rapido) · [Test](#-test) · [Problemi](#-risoluzione-dei-problemi) · [Struttura](#-struttura-del-repository) · [Correlati](#-progetti-correlati)

## 🚦 Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi. È scritta in base a ciò che il repository può mostrare (test, compilazioni, esecuzioni), non a ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 Fatto a metà o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Software | 🟡 | La scoperta dei manifesti, il confronto delle versioni e l'installazione e aggiornamento a fasi funzionano; non sono stati eseguiti end to end contro tutti i repository della famiglia. |
| Test | 🟢 | Superano 288 test (`python -m pytest tests -q`): la scoperta, il confronto delle versioni, il controllo della firma, l'installazione a fasi con blocco, diario, copie e ripristino, il registro delle prove e le tabelle delle otto lingue. |
| Interfaccia | 🟡 | L'interfaccia Qt Quick è stata eseguita solo su Windows. |
| Sicurezza | 🟡 | Il controllo della firma e il registro delle prove sono testati sull'host; non c'è stata una revisione indipendente. |
| Aggiornamenti | 🟡 | Le installazioni che esegue richiedono `git` e gli strumenti di compilazione propri di ciascun repository sulla macchina. |
| Documentazione | 🟢 | Otto lingue e il registro delle modifiche sono aggiornati. |

## 🎯 Panoramica

* **Scoperta, senza elenco fisso:** una cartella locale entra appena porta un `armor.project.json` valido che dichiara `ecosystem: "A.R.M.O.R."`; da remoto, ogni repository pubblico dell'account è controllato allo stesso modo. Un `GITHUB_TOKEN` è facoltativo: alza solo il limite di 60 richieste l'ora di GitHub.
* **Installare e aggiornare, mai sul posto:** un nuovo progetto e un aggiornamento sono prima costruiti e verificati in un clone di prova indipendente, e promossi solo - due rinominazioni registrate, la copia sostituita conservata in `.armor-updater/backups/` (le tre più recenti) - quando quella costruzione riesce; un aggiornamento al commit già installato non fa nulla; una vera modifica locale non salvata è rifiutata senza mezzi termini, mai scartata in silenzio; un guasto tra le rinominazioni viene riparato alla prossima esecuzione, e `rollback` rimette la copia più recente.
* **Uno alla volta, e in ordine:** un blocco impedisce a due aggiornatori di lavorare insieme su uno spazio di lavoro; un lotto parte da ARMOR-COMMON (ogni costruzione ne ha bisogno) e un progetto non viene costruito senza di esso.
* **Prove:** ogni tentativo, riuscito o no, aggiunge una riga a un registro locale con il progetto, la versione e il commit prima e dopo, e il motivo di un fallimento.
* **Requisiti:** un manifest può elencare, nel campo facoltativo `requires`, i progetti che devono essere installati prima; un blocco li mette per primi, e un'installazione o un aggiornamento viene rifiutato con un messaggio chiaro, nella lingua della finestra, se ne manca uno.
* **Firme, avvisa per impostazione predefinita:** una revisione senza firma valida viene comunque installata o aggiornata, e la finestra e la riga di comando indicano che non è firmata; scegliere *richiedi* nelle impostazioni (`"signature_policy": "require"`) la rifiuta invece.
* **Copie precedenti:** la finestra può ripristinare la copia precedente di un progetto o eliminare le copie conservate, e `status` mostra quante ce ne sono e lo spazio su disco che occupano.
* **Una CLI e un'interfaccia desktop opzionale:** `armor-updater status`/`install`/`update`, e un'interfaccia Qt Quick (`pip install ".[gui]"`) nelle otto lingue dell'ecosistema.

## 🧩 Ruolo in A.R.M.O.R.

ARMOR-UPDATER è lo strumento da scrivania per chi tiene una copia della famiglia su un PC: trova i repository A.R.M.O.R. della macchina, li confronta con GitHub e installa o aggiorna uno alla volta, verificando prima di sostituire qualcosa. È distinto dagli aggiornamenti che [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) guida sulla CM5 (quelli passano per [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)): questo è per la macchina di uno sviluppatore.

| Parla con | Come | A che scopo |
|---|---|---|
| Cartella di lavoro locale | cartelle con un `armor.project.json` valido | cosa è installato e in quale versione |
| GitHub | `api.github.com`, `raw.githubusercontent.com` e git; `GITHUB_TOKEN` facoltativo | l'ultima versione di ogni repository dell'account |
| ARMOR-COMMON | un progetto può elencarlo in `requires` | va per primo in ogni lotto: ogni compilazione ne ha bisogno |
| ARMOR-DEVOPS | separato | gli aggiornamenti che ARMOR-STUDIO guida sulla CM5 passano da lui, non da questo strumento |

## 🏛️ Architettura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 Sicurezza e protezione

| Minaccia | Difesa |
|---|---|
| Viene installato codice compromesso | I commit sono verificati con i firmatari di `data/allowed_signers` (formato OpenSSH) la cui impronta è fissata in `signature.py`; cambiare il file senza il pin fa fallire ogni controllo (chiuso); `signature_policy` è `warn` (default: installa e dice che non è firmato) o `require` (rifiuta) |
| Un'installazione a metà o una sostituzione sul posto | Mai sul posto: tutto è costruito e verificato in un clone di preparazione indipendente e promosso con due rinomine a diario (`promotion.json`); la copia sostituita resta in `.armor-updater/backups/` (le tre più recenti) |
| Due aggiornatori sulla stessa cartella | Un blocco (`.armor-updater/lock`) che scade dopo 6 ore |
| Una dipendenza non costruita | ARMOR-COMMON va per primo e un progetto non si costruisce senza di lui; il campo facoltativo `requires` del manifesto ordina un lotto e rifiuta un'installazione con un messaggio chiaro nella lingua della finestra |
| Modifiche locali perse | Un aggiornamento al commit già installato non fa nulla; una modifica locale davvero non committata viene rifiutata del tutto |
| Una scoperta falsa | Un progetto conta solo con un `armor.project.json` valido che dichiari `ecosystem: "A.R.M.O.R."`; da remoto, ogni repository pubblico dell'account è verificato allo stesso modo |
| GitHub lento o non raggiungibile | Timeout di 10 s, fino a 8 alla volta, 3 tentativi (attesa base 0,5 s), `ls-remote` 20 s; il ritardo di minuti di `raw.githubusercontent.com` è previsto |

Ogni tentativo, riuscito o no, aggiunge una riga al registro locale delle prove (progetto, versione e commit prima e dopo, motivo di un fallimento). Le installazioni richiedono `git` e gli strumenti di compilazione di ogni repository; la firma viene solo segnalata salvo si scelga `require`; non è stato eseguito contro tutti i repository della famiglia da cima a fondo e non c'è stata una revisione indipendente.

## 🔌 Interfacce

| Rotta | Autenticazione | Cosa fa |
|---|---|---|
| `armor-updater --cli status` | - | cosa è installato, la sua versione e l'ultima su GitHub; `--workspace D`, `--offline` (solo locale), `--notes` (le note reali di ogni progetto), `--json` (leggibile da macchina) |
| `armor-updater --cli install <project>` | - | clona, compila e installa UN progetto non ancora installato; `--no-build` clona soltanto |
| `armor-updater --cli update <project>` | - | aggiorna uno installato, compilato e verificato prima di metterlo a posto; `--no-build` scarica soltanto |
| `armor-updater --cli rollback <project>` | - | rimette la copia più recente del checkout sostituito |
| `armor-updater --cli backups [<project>]` | - | elenca le copie dei checkout sostituiti e il disco che occupano; `--prune N` tiene le N più recenti di ciascuno |
| `armor-updater --version` | - | la versione dello strumento |

La finestra (Qt Quick, `pip install ".[gui]"`, avviata su Windows da `run-gui.vbs`) mostra lo stesso stato, installa e aggiorna un progetto, ripristina la copia precedente di un progetto o elimina le copie conservate, e dice quando una revisione non è firmata; è scritta in otto lingue (`i18n.py`, `i18n_pt.py`, `i18n_recovery.py`, `result_text.py`) e ha girato solo su Windows. Riferimento completo: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) e [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md).

## ⚙️ Configurazione

| Impostazione | Predefinito | Cosa fa |
|---|---|---|
| `--workspace` | la cartella superiore dello strumento | la radice della cartella di lavoro da esaminare |
| `GITHUB_TOKEN` | facoltativo | alza il limite di GitHub di 60 richieste all'ora; si legge soltanto, mai si scrive |
| `signature_policy` | warn | `warn` installa e dice che non è firmato; `require` rifiuta; salvato in `~/.armor_updater_settings.json` |
| Copie conservate | 3 | le tre più recenti di ogni progetto; `backups --prune N` lo cambia |
| Blocco | 6 h | un blocco più vecchio viene ignorato |

`.env.example` mostra le variabili che la compilazione di un repository può leggere. La lingua della finestra segue `~/.armor_updater_settings.json` (e il vecchio `~/.armor_updater_lang.json`).

## 🚀 Avvio rapido

**Requisiti:** Python 3.10+, `git` e gli strumenti di compilazione dei repository che installi; facoltativo: PySide6 per la finestra desktop.

```bash
pip install -e ".[dev]"                     # oppure ".[dev,gui]" per la finestra Qt Quick opzionale
python -m pytest tests -q                   # 288 test, circa sei minuti
armor-updater --cli status                  # stato locale e GitHub di ogni repository
armor-updater --cli install ARMOR-NETWORK   # clona, compila e installa un repository non ancora installato
armor-updater --cli update ARMOR-NETWORK    # aggiorna uno installato (compilato e verificato prima di metterlo)
armor-updater --cli rollback ARMOR-NETWORK  # rimette la copia più recente di un checkout sostituito
```

Vedi [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

## 🧪 Test

```powershell
python -m pytest tests -q  # 288 test, circa sei minuti
python -I tools/armor_ci_validate.py
```

| Area | Cosa copre |
|---|---|
| Scoperta e versioni | il manifesto, il registro, il rilevamento locale e remoto, l'analisi delle versioni e il client GitHub |
| Installazione e aggiornamento | la preparazione, il blocco, il diario, le copie e il ripristino, i requisiti e il registro delle prove |
| Firme | le chiavi fissate, il fallimento chiuso e le due politiche |
| Riga di comando | `status`, `install`, `update`, `rollback` e `backups` con le loro opzioni |
| Lingue e finestra | le otto lingue (`test_i18n.py`) e i testi di ogni risultato |

`python -m unittest` ne trova che tre test: la suite è scritta per pytest (`conftest.py` è in `tests/`) e dura quasi sei minuti. GitHub Actions esegue la base A.R.M.O.R. a ogni push e pull request: la validazione di manifesto, versione, registro delle modifiche e parità dei README, poi la compilazione e i test del progetto.

## 🏗️ Compilazione e rilascio

È Python puro: nulla da compilare (`pip install -e .`). La versione risiede in `pyproject.toml`, in `armor.project.json` e nel badge del README (letto dal manifesto); ogni versione ha la sua voce in [CHANGELOG.md](CHANGELOG.md). Le versioni sono pubblicate su GitHub.

## 🩺 Risoluzione dei problemi

| Vedi | Perché | Fai |
|---|---|---|
| Un aggiornamento dice che non è successo nulla | il progetto è già al commit che ha GitHub | niente da fare |
| Un aggiornamento è rifiutato per modifiche locali | il checkout ha una modifica non committata | fai commit o mettila da parte, poi aggiorna |
| Dice che un requisito non è installato | il manifesto lo elenca in `requires` | installa prima quel progetto (un lotto li ordina già) |
| La finestra o la riga di comando dice che la revisione non è firmata | `signature_policy` è `warn`, quindi installa e lo dice | scegli `require` nelle impostazioni per rifiutare le revisioni non firmate |
| Un aggiornamento ha rotto qualcosa | la nuova revisione compila ma non si comporta bene | `armor-updater --cli rollback <progetto>` rimette la copia più recente |

## 📂 Struttura del repository

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>Versione testuale dell'albero</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   il manifesto, l'elenco, il catalogo
│   ├── detect.py github_client.py version_parse.py            scoperta locale e remota, versioni
│   ├── install.py git_ops.py staging.py                       installazione e aggiornamento a fasi
│   ├── promotion.py releases.py deploy_category.py            blocco, diario, copie, disposizioni
│   ├── signature.py                                           aggiornamenti firmati, chiavi fissate
│   ├── evidence.py settings.py console_flags.py               il registro, le impostazioni, le opzioni
│   ├── main.py                                                la riga di comando
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     le otto lingue
│   ├── gui.py qt_gui.py qml/                                  la finestra Qt Quick opzionale
│   └── data/ assets/                                          allowed_signers; l'icona
├── tests/                                                     288 test in 25 moduli
├── docs/                                                      CLI_REFERENCE.md, QML_DESKTOP_GUI.md
├── tools/                                                     i controlli CI, l'avviatore e generate_app_icon.py
├── images/                                                    banner, icona e immagini del README
├── .github/                                                   workflow CI, avviso alla dashboard, modelli per issue e pull request
├── armor.project.json                                         manifesto: versione, ruolo, maturità
├── pyproject.toml                                             metadati del pacchetto, ingressi
├── CHANGELOG.md                                               cosa è cambiato in ogni versione
├── run-gui.vbs                                                apre la finestra su Windows senza console
├── run.sh run.bat                                             avvio, flusso condiviso
├── build.sh build.bat                                         compila e prova, flusso condiviso
├── build-test.sh build-test.bat                               compila, prova e impacchetta
├── test.sh test.bat                                           solo i test, mai la versione
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap e limiti noti

**Limiti noti oggi**

* La finestra Qt Quick ha girato solo su Windows.
* Non è stato eseguito contro tutti i repository della famiglia da cima a fondo.
* Le installazioni richiedono `git` e gli strumenti di compilazione di ogni repository.
* Nessuna revisione di sicurezza indipendente.

**Prossimi passi**

* Eseguirlo da cima a fondo contro tutti i repository della famiglia e su Linux e macOS.

## 🌍 Lingue

Il README e i testi esistono in inglese, spagnolo, francese, italiano, tedesco, cinese, giapponese e portoghese europeo.

## 🔗 Progetti correlati

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) è un sistema di sicurezza perimetrale fatto di repository indipendenti. Ognuno ha la propria versione, i propri test e il proprio README; ecco la famiglia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratti dei messaggi, validatori, vettori di conformità e tipi generati
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware del nodo di campo per ESP32-S3 con tre radar e un proprio pannello web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolli di inverter e batterie solari e messaggi di un nodo gateway
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nodo elettrico: contatori, il messaggio delle letture della rete e le regole di manovra
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nodo e centrale d'allarme: zone, inserimento, ritardi, sirena e PIN, con il server o senza
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Pannello touch: lo stato del sistema su uno schermo a parete, attivare e riconoscere gli allarmi, e la casa dell'assistente vocale
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - La rete locale: i suoi dispositivi, internet e ciò che cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinatore centrale: telemetria, allarmi, dispositivi, letture solari e telecamere
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web: telecamere, radar, allarmi, energia solare e progettista del sito 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android dell'operatore con radar 2D/3D in tempo reale
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Client operatore per iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politica di inferenza visiva che spiega le sue decisioni e non agisce mai
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zone delle telecamere, maschere e regole di rilevamento per la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenti vocali offline con una conferma impossibile da falsificare
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Contenitori, elettronica e matrice di accettazione da banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Distribuzione, banco di prova CM5, backup e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulatore di telemetria offline con guasti ripetibili
* **ARMOR-UPDATER** (questo repository) - Rileva, installa e aggiorna i repository stessi dell'ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architettura, base di sicurezza e matrice delle capacità

## 📚 Documentazione

* [Riferimento della riga di comando](docs/CLI_REFERENCE.md): ogni comando e opzione
* [La finestra Qt Quick](docs/QML_DESKTOP_GUI.md): come funziona la finestra desktop
* [Matrice delle capacità: cosa è provato e cosa no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogo dei progetti: versioni e dipendenze tra i repository](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Cronologia delle modifiche di questo repository](CHANGELOG.md)

## 🤝 Contribuire e comunità

* Prima di una pull request esegui `python -I tools/armor_ci_validate.py` e i test: devono passare entrambi. Vedi [CONTRIBUTING.md](CONTRIBUTING.md) e il [codice di condotta](CODE_OF_CONDUCT.md).
* Il README esiste in otto lingue ed è generato dalle sorgenti in ARMOR-DOCS: una modifica al testo si fa lì.
* Una modifica a un messaggio tra componenti parte da ARMOR-COMMON.
* Non descrivere come funzionante su una scheda ciò che è stato solo compilato.
* Segnala una vulnerabilità in privato: [SECURITY.md](SECURITY.md). Domande, idee e segnalazioni: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
