<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-UPDATER banner" width="100%">
</p>

# 🛠️ ARMOR-UPDATER

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  🇵🇹 <b>Português</b>
</p>

### Deteta, instala e atualiza cada repositório A.R.M.O.R. na máquina onde corre (um programa em Python sem dependências obrigatórias)

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

**Verificação de honestidade - o que funciona hoje:** A descoberta por manifesto, a comparação de versões, a verificação de assinatura, a instalação e a atualização por etapas com o seu bloqueio, diário, cópias e volta atrás, o registo de evidências e as tabelas da interface em oito idiomas estão testados (191 testes), e a interface Qt Quick correu no Windows. Não foi executada contra todos os repositórios da família de ponta a ponta, e as instalações que faz precisam de `git` e das ferramentas de compilação de cada repositório na máquina.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.1.4` |
| Maturidade | Estabelecido |
| Testes | 191 (`python -m pytest tests -q`) |
| Tecnologia | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| Em hardware real | Não se aplica: é um programa de ambiente de trabalho; a sua interface Qt Quick foi executada no Windows |

## 🎯 Visão geral

* **Descoberta, sem lista fixa:** uma pasta local junta-se assim que tem um `armor.project.json` válido que declara `ecosystem: "A.R.M.O.R."`; em remoto, cada repositório público da conta é verificado da mesma forma. Um `GITHUB_TOKEN` é opcional: só sobe o limite de 60 pedidos por hora do GitHub.
* **Instalar e atualizar, nunca no próprio sítio:** um projeto novo e uma atualização são primeiro construídos e verificados num clone de ensaio independente, e só depois promovidos - dois renomeamentos com diário, a cópia substituída guardada em `.armor-updater/backups/` (as três mais recentes) - quando essa construção tem êxito; atualizar para o commit já instalado não faz nada; uma alteração local a sério por commitar é recusada de vez, nunca descartada em silêncio; uma falha entre os renomeamentos é reparada na execução seguinte, e `rollback` repõe a cópia mais recente.
* **Um de cada vez, e por ordem:** um bloqueio impede que dois atualizadores trabalhem juntos num espaço de trabalho; um lote começa por ARMOR-COMMON (todas as construções precisam dele) e um projeto não é construído sem ele.
* **Provas:** cada tentativa, bem-sucedida ou não, acrescenta uma linha a um registo local com o projeto, a versão e o commit antes e depois, e o motivo de uma falha.
* **Requisitos:** um manifesto pode listar, no campo opcional `requires`, os projetos que têm de estar instalados primeiro; um lote coloca-os à frente, e uma instalação ou atualização é recusada com uma mensagem clara, na língua da janela, se algum deles faltar.
* **Assinaturas, avisar por omissão:** uma revisão sem assinatura válida é instalada ou atualizada na mesma, e a janela e a linha de comandos indicam que não está assinada; escolher *exigir* nas definições (`"signature_policy": "require"`) recusa-a em vez disso.
* **Cópias anteriores:** a janela pode restaurar a cópia anterior de um projeto ou apagar as cópias guardadas, e o `status` mostra quantas existem e o disco que ocupam.
* **Uma CLI e uma consola de ambiente de trabalho opcional:** `armor-updater status`/`install`/`update`, e uma interface Qt Quick (`pip install ".[gui]"`) nos oito idiomas do ecossistema.

## 🧩 Papel no A.R.M.O.R.

O ARMOR-UPDATER é a ferramenta de ambiente de trabalho para quem guarda uma cópia da família num PC: encontra os repositórios A.R.M.O.R. da máquina, compara-os com o GitHub e instala ou atualiza um a um, verificando antes de substituir seja o que for. É distinto das atualizações que o [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) comanda no CM5 (essas passam pelo [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)): este é para a máquina de um programador.

## 📂 Estrutura do repositório

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              18 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ Ambiente de desenvolvimento

**Requisitos:** Python 3.10+, `git` and the build tools of the repositories you install, optional: PySide6 for the desktop shell

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 191 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

Veja `docs/CLI_REFERENCE.md`.

## 🔗 Projetos relacionados

O **A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) é um sistema de segurança perimetral feito de repositórios independentes. Cada um tem a sua própria versão, os seus próprios testes e o seu próprio README; esta é a família:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensagens, validadores, vetores de conformidade e tipos gerados
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware de nó de campo para ESP32-S3 com três radares e o seu próprio painel web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolos de inversores e baterias solares e as mensagens de um nó de ligação
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nó elétrico: contadores, a mensagem das leituras da rede e as regras de comutação
* **[ARMOR-ALARM](https://github.com/JuanenRac/ARMOR-ALARM)** - Nó e central de alarme: zonas, armar, atrasos, sirene e PIN, com o servidor ou sem ele
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Painel tátil: o estado do sistema num ecrã de parede, armar e reconhecer, e a casa do assistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - A rede local: os seus dispositivos, a internet e o que muda
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordenador central: telemetria, alarmes, dispositivos, leituras solares e câmaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: câmaras, radar, alarmes, energia solar e o desenhador de local 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente Android de operador com um radar 2D/3D em direto
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferência visual que explica as suas decisões e nunca atua
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de câmara, máscaras e regras de deteção para o Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenções de voz offline com uma confirmação que não se pode falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Caixas, eletrónica e a matriz de aceitação de bancada
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Implementação, a bancada de testes CM5, cópias de segurança e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetria offline com falhas repetíveis
* **ARMOR-UPDATER** (este repositório) - Deteta, instala e atualiza os próprios repositórios do ecossistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitetura, linha de base de segurança e a matriz de capacidades

## 📚 Documentação e comunidade

Onde ler mais:

* [Matriz de capacidades: o que está provado e o que não](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de projetos: versões e como os repositórios dependem uns dos outros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença (GPL-3.0-or-later)](LICENSE)
* Perguntas, ideias e relatórios: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - veja [LICENSE](LICENSE).
