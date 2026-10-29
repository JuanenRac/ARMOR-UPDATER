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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-288%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que funciona hoje:** A descoberta por manifesto, a comparação de versões, a verificação de assinatura, a instalação e a atualização por etapas com o seu bloqueio, diário, cópias e volta atrás, o registo de evidências e as tabelas da interface em oito idiomas estão testados (288 testes), e a interface Qt Quick correu no Windows. Não foi executada contra todos os repositórios da família de ponta a ponta, e as instalações que faz precisam de `git` e das ferramentas de compilação de cada repositório na máquina.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.1.5` |
| Maturidade | Estabelecido |
| Função | Ferramenta de secretária que instala e atualiza a família num PC, um projeto de cada vez |
| Tecnologia | Python 3.10+, git; PySide6 (Qt Quick) opcional |
| Testes | 288 (`python -m pytest tests -q`, cerca de seis minutos) |
| Interfaces | `armor-updater --cli` com `status`, `install`, `update`, `rollback` e `backups`, e uma janela Qt Quick em oito idiomas |
| Funciona em | Um PC com Python e git (a janela só correu no Windows) |
| Em hardware real | Não se aplica: é um programa de ambiente de trabalho; a sua interface Qt Quick foi executada no Windows |
| Licença | GPL-3.0-or-later |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Segurança](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Configuração](#-configuração) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Problemas](#-resolução-de-problemas) · [Estrutura](#-estrutura-do-repositório) · [Relacionados](#-projetos-relacionados)

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟡 | A descoberta de manifestos, a comparação de versões e a instalação e atualização por fases funcionam; não foram executadas de ponta a ponta contra todos os repositórios da família. |
| Testes | 🟢 | Passam 288 testes (`python -m pytest tests -q`): a descoberta, a comparação de versões, a verificação da assinatura, a instalação por fases com o seu bloqueio, diário, cópias e retrocesso, o registo de provas e as tabelas dos oito idiomas. |
| Interface | 🟡 | A interface Qt Quick só foi executada em Windows. |
| Segurança | 🟡 | A verificação da assinatura e o registo de provas estão testados no anfitrião; não houve revisão independente. |
| Atualizações | 🟡 | As instalações que faz precisam de `git` e das ferramentas de compilação próprias de cada repositório na máquina. |
| Documentação | 🟢 | Oito idiomas e o registo de alterações estão atualizados. |

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

| Fala com | Como | Para quê |
|---|---|---|
| Pasta de trabalho local | pastas com um `armor.project.json` válido | o que está instalado e em que versão |
| GitHub | `api.github.com`, `raw.githubusercontent.com` e git; `GITHUB_TOKEN` opcional | a última versão de cada repositório da conta |
| ARMOR-COMMON | um projeto pode listá-lo em `requires` | vai primeiro em cada lote: toda a compilação precisa dele |
| ARMOR-DEVOPS | à parte | as atualizações que o ARMOR-STUDIO conduz no CM5 passam por ele, não por esta ferramenta |

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 Segurança e proteção

| Ameaça | Defesa |
|---|---|
| Instala-se código comprometido | Os commits são verificados com assinantes de `data/allowed_signers` (formato OpenSSH) cuja impressão digital está fixada em `signature.py`; mudar o ficheiro sem mudar o pin faz falhar toda a verificação (fecha); `signature_policy` é `warn` (predefinição: instala e diz que não está assinado) ou `require` (recusa) |
| Uma instalação a meio ou uma substituição no sítio | Nunca no sítio: tudo é construído e verificado num clone de preparação independente e promovido com duas mudanças de nome com diário (`promotion.json`); a cópia substituída fica em `.armor-updater/backups/` (as três mais recentes) |
| Dois atualizadores na mesma pasta | Um bloqueio (`.armor-updater/lock`) que caduca às 6 horas |
| Uma dependência por construir | ARMOR-COMMON vai primeiro e um projeto não se constrói sem ele; o campo opcional `requires` do manifesto ordena um lote e recusa uma instalação com uma mensagem clara no idioma da janela |
| Alterações locais perdidas | Uma atualização para o commit já instalado não faz nada; uma alteração local realmente sem commit é recusada de vez |
| Uma descoberta falsa | Um projeto só conta com um `armor.project.json` válido que declare `ecosystem: "A.R.M.O.R."`; remotamente, cada repositório público da conta é verificado do mesmo modo |
| GitHub lento ou em baixo | Tempo limite de 10 s, até 8 de cada vez, 3 repetições (espera base de 0,5 s), `ls-remote` 20 s; o atraso de minutos de `raw.githubusercontent.com` está previsto |

Cada tentativa, bem-sucedida ou não, acrescenta uma linha ao registo local de provas (projeto, versão e commit antes e depois, razão de uma falha). As instalações precisam de `git` e das ferramentas de compilação de cada repositório; a assinatura só avisa, a menos que se escolha `require`; não foi executado contra todos os repositórios da família de ponta a ponta e não houve revisão independente.

## 🔌 Interfaces

| Rota | Autenticação | O que faz |
|---|---|---|
| `armor-updater --cli status` | - | o que está instalado, a sua versão e a última no GitHub; `--workspace D`, `--offline` (só local), `--notes` (as notas reais de cada projeto), `--json` (legível por máquina) |
| `armor-updater --cli install <project>` | - | clona, constrói e instala UM projeto ainda não instalado; `--no-build` só clona |
| `armor-updater --cli update <project>` | - | atualiza um instalado, construído e verificado antes de o pôr no lugar; `--no-build` só obtém |
| `armor-updater --cli rollback <project>` | - | repõe a cópia mais recente do checkout substituído |
| `armor-updater --cli backups [<project>]` | - | lista as cópias dos checkouts substituídos e o disco que ocupam; `--prune N` mantém as N mais recentes de cada um |
| `armor-updater --version` | - | a versão da ferramenta |

A janela (Qt Quick, `pip install ".[gui]"`, no Windows iniciada por `run-gui.vbs`) mostra o mesmo estado, instala e atualiza um projeto, restaura a cópia anterior de um projeto ou apaga as cópias guardadas, e diz quando uma revisão não está assinada; está redigida em oito idiomas (`i18n.py`, `i18n_pt.py`, `i18n_recovery.py`, `result_text.py`) e só correu no Windows. Referência completa: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) e [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md).

## ⚙️ Configuração

| Definição | Predefinição | O que faz |
|---|---|---|
| `--workspace` | a pasta-mãe da ferramenta | a raiz da pasta de trabalho a examinar |
| `GITHUB_TOKEN` | opcional | sobe o limite do GitHub de 60 pedidos por hora; só se lê, nunca se escreve |
| `signature_policy` | warn | `warn` instala e diz que não está assinado; `require` recusa; guardada em `~/.armor_updater_settings.json` |
| Cópias guardadas | 3 | as três mais recentes de cada projeto; `backups --prune N` muda-o |
| Bloqueio | 6 h | um bloqueio mais antigo é ignorado |

`.env.example` mostra as variáveis que a compilação de um repositório pode ler. O idioma da janela segue `~/.armor_updater_settings.json` (e o antigo `~/.armor_updater_lang.json`).

## 🚀 Início rápido

**Requisitos:** Python 3.10+, `git` e as ferramentas de compilação dos repositórios que instalar; opcional: PySide6 para a janela de secretária.

```bash
pip install -e ".[dev]"                     # ou ".[dev,gui]" para a janela Qt Quick opcional
python -m pytest tests -q                   # 288 testes, cerca de seis minutos
armor-updater --cli status                  # estado local e do GitHub de cada repositório
armor-updater --cli install ARMOR-NETWORK   # clona, constrói e instala um repositório ainda não instalado
armor-updater --cli update ARMOR-NETWORK    # atualiza um instalado (construído e verificado antes de o pôr)
armor-updater --cli rollback ARMOR-NETWORK  # repõe a cópia mais recente de um checkout substituído
```

Consulte [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

## 🧪 Testes

```powershell
python -m pytest tests -q  # 288 testes, cerca de seis minutos
python -I tools/armor_ci_validate.py
```

| Área | O que cobre |
|---|---|
| Descoberta e versões | o manifesto, o registo, a deteção local e remota, a análise de versões e o cliente do GitHub |
| Instalação e atualização | a preparação, o bloqueio, o diário, as cópias e a reversão, os requisitos e o registo de provas |
| Assinaturas | as chaves fixadas, a falha fechada e as duas políticas |
| Linha de comandos | `status`, `install`, `update`, `rollback` e `backups` com as suas opções |
| Idiomas e janela | os oito idiomas (`test_i18n.py`) e os textos de cada resultado |

`python -m unittest` só encontra três: a bateria está escrita para pytest (`conftest.py` está em `tests/`) e demora quase seis minutos. O GitHub Actions executa a base do A.R.M.O.R. em cada push e pull request: a validação do manifesto, da versão, do registo de alterações e da paridade dos README, e depois a compilação e os testes do próprio projeto.

## 🏗️ Compilação e publicação

É Python puro: não há nada para compilar (`pip install -e .`). A versão está em `pyproject.toml`, em `armor.project.json` e no emblema do README (lido do manifesto); cada versão tem a sua entrada em [CHANGELOG.md](CHANGELOG.md). As versões são publicadas no GitHub.

## 🩺 Resolução de problemas

| Vê | Porque | Faça |
|---|---|---|
| Uma atualização diz que nada aconteceu | o projeto já está no commit que o GitHub tem | nada a fazer |
| Uma atualização é recusada por alterações locais | o checkout tem uma alteração sem commit | faça commit ou guarde à parte e atualize |
| Diz que um requisito não está instalado | o manifesto lista-o em `requires` | instale primeiro esse projeto (um lote já os ordena) |
| A janela ou a linha de comandos diz que a revisão não está assinada | `signature_policy` é `warn`, por isso instala e di-lo | escolha `require` nas definições para recusar revisões sem assinatura |
| Uma atualização estragou algo | a nova revisão compila mas não se comporta | `armor-updater --cli rollback <projeto>` repõe a cópia mais recente |

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   o manifesto, a lista, o catálogo
│   ├── detect.py github_client.py version_parse.py            descoberta local e remota, versões
│   ├── install.py git_ops.py staging.py                       instalação e atualização por fases
│   ├── promotion.py releases.py deploy_category.py            bloqueio, diário, cópias, disposições
│   ├── signature.py                                           atualizações assinadas, chaves fixadas
│   ├── evidence.py settings.py console_flags.py               o registo, as definições, as opções
│   ├── main.py                                                a linha de comandos
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     os oito idiomas
│   ├── gui.py qt_gui.py qml/                                  a janela Qt Quick opcional
│   └── data/ assets/                                          allowed_signers; o ícone
├── tests/                                                     288 testes em 25 módulos
├── docs/                                                      CLI_REFERENCE.md, QML_DESKTOP_GUI.md
├── tools/                                                     as verificações de CI, o lançador e generate_app_icon.py
├── images/                                                    faixa, ícone e as imagens do README
├── .github/                                                   fluxo de CI, aviso ao painel, modelos de issues e pull requests
├── armor.project.json                                         manifesto: versão, função, maturidade
├── pyproject.toml                                             metadados do pacote, entradas
├── CHANGELOG.md                                               o que mudou em cada versão
├── run-gui.vbs                                                abre a janela no Windows sem consola
├── run.sh run.bat                                             arrancar, fluxo partilhado
├── build.sh build.bat                                         compilar e testar, fluxo partilhado
├── build-test.sh build-test.bat                               compilar, testar e empacotar
├── test.sh test.bat                                           só os testes, nunca a versão
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roteiro e limites conhecidos

**Limites conhecidos hoje**

* A janela Qt Quick só correu no Windows.
* Não foi executado contra todos os repositórios da família de ponta a ponta.
* As instalações precisam de `git` e das ferramentas de compilação de cada repositório.
* Sem revisão de segurança independente.

**A seguir**

* Executá-lo de ponta a ponta contra todos os repositórios da família e em Linux e macOS.

## 🌍 Idiomas

O README e os textos existem em inglês, espanhol, francês, italiano, alemão, chinês, japonês e português europeu.

## 🔗 Projetos relacionados

O **A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) é um sistema de segurança perimetral feito de repositórios independentes. Cada um tem a sua própria versão, os seus próprios testes e o seu próprio README; esta é a família:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensagens, validadores, vetores de conformidade e tipos gerados
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware de nó de campo para ESP32-S3 com três radares e o seu próprio painel web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolos de inversores e baterias solares e as mensagens de um nó porta de ligação
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nó elétrico: contadores, a mensagem das leituras da rede e as regras de comutação
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nó e painel de alarme: zonas, armar, atrasos, sirene e PIN, com o servidor ou sem ele
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Painel tátil: o estado do sistema num ecrã de parede, armar e reconhecer, e a casa do assistente de voz
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - A rede local: os seus dispositivos, a internet e o que muda
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordenador central: telemetria, alarmes, dispositivos, leituras solares e câmaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: câmaras, radar, alarmes, energia solar e o desenhador 2D/3D do local
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente de operador Android com radar 2D/3D em direto
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Cliente de operador para iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferência visual que explica as suas decisões e nunca atua
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de câmara, máscaras e regras de deteção para o Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenções de voz offline com uma confirmação que não pode ser falsificada
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Caixas, eletrónica e a matriz de aceitação em bancada
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Implantação, a bancada de testes do CM5, cópias de segurança e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetria offline com falhas repetíveis
* **ARMOR-UPDATER** (este repositório) - Deteta, instala e atualiza os repositórios do próprio ecossistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitetura, base de segurança e a matriz de capacidades

## 📚 Documentação

* [Referência da linha de comandos](docs/CLI_REFERENCE.md): cada comando e opção
* [A janela Qt Quick](docs/QML_DESKTOP_GUI.md): como funciona a janela de secretária
* [Matriz de capacidades: o que está demonstrado e o que não está](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de projetos: versões e como os repositórios dependem uns dos outros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registo de alterações deste repositório](CHANGELOG.md)

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `python -I tools/armor_ci_validate.py` e os testes: ambos têm de passar. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).
* O README existe em oito idiomas e é gerado a partir das fontes do ARMOR-DOCS: uma alteração ao texto faz-se lá.
* Uma alteração a uma mensagem entre componentes começa no ARMOR-COMMON.
* Não descreva como a funcionar numa placa aquilo que só foi compilado.
* Comunique uma vulnerabilidade em privado: [SECURITY.md](SECURITY.md). Perguntas, ideias e relatórios: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - consulte [LICENSE](LICENSE).
