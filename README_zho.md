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
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### 检测、安装并更新所在机器上的每个 A.R.M.O.R. 仓库（一个没有必需依赖的 Python 程序）

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-321%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**诚实性检查 - 今天真正能运行的部分：** 清单发现、版本比较、签名检查、带锁、日志、备份和回退的分阶段安装与更新、证据日志以及八种语言的界面表格都已测试（321 个测试），Qt Quick 界面已在 Windows 上运行过。它没有对家族中的每个仓库从头到尾运行过，它所做的安装需要机器上有 `git` 和各仓库自己的构建工具。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.1.7` |
| 成熟度 | 成熟 |
| 角色 | 在 PC 上逐个安装和更新整个家族的桌面工具 |
| 技术栈 | Python 3.10+、git；可选 PySide6（Qt Quick） |
| 测试 | 321 项（`python -m pytest tests -q`，约六分钟） |
| 接口 | `armor-updater --cli`（`status`、`install`、`update`、`rollback`、`backups`）以及八种语言的 Qt Quick 窗口 |
| 运行位置 | 装有 Python 和 git 的 PC（窗口只在 Windows 上运行过） |
| 真实硬件 | 不适用：这是桌面程序；其 Qt Quick 界面已在 Windows 上运行过 |
| 许可证 | GPL-3.0-or-later |

**跳转到：** [概述](#-概述) · [架构](#-架构) · [安全](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [故障排除](#-故障排除) · [结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟡 | 清单发现、版本比较以及分阶段安装与更新都能工作；尚未对家族中的每个仓库完整运行过。 |
| 测试 | 🟢 | 321 项测试通过（`python -m pytest tests -q`）：发现、版本比较、签名检查、带锁、日志、备份和回滚的分阶段安装、证据日志以及八种语言的表。 |
| 界面 | 🟡 | Qt Quick 界面只在 Windows 上运行过。 |
| 安全 | 🟡 | 签名检查和证据日志已在主机上测试；没有经过独立审查。 |
| 更新 | 🟡 | 它所做的安装需要机器上有 `git` 以及每个仓库自己的构建工具。 |
| 文档 | 🟢 | 八种语言和更新日志均为最新。 |

## 🎯 概述

* **无固定列表的发现：**本地文件夹只要带有声明 `ecosystem: "A.R.M.O.R."` 的有效 `armor.project.json` 就会加入；远程则以同样方式检查账户的每个公开仓库。`GITHUB_TOKEN` 是可选的：它只是提高 GitHub 每小时 60 次请求的限制。
* **安装和更新，从不原地进行：**新项目和更新都先在独立的暂存克隆中构建并验证，构建成功后才升级——两次有日志的重命名，被替换的检出保存在 `.armor-updater/backups/`（最近三份）；更新到已安装的提交不会做任何事；真正未提交的本地修改会被直接拒绝，绝不会被悄悄丢弃；两次重命名之间的崩溃会在下次运行时修复，`rollback` 会放回最近的备份。
* **一次一个，并有顺序：**锁可防止两个更新器同时处理一个工作区；批量操作先处理 ARMOR-COMMON（每个构建都需要它），没有它就不会构建项目。
* **证据:** 每一次尝试,无论成功与否,都会在本地日志里追加一行,记录项目、前后的版本与提交,以及失败的原因。
* **前置要求：**清单可以在可选字段 `requires` 中列出必须先安装的项目；批量操作会把它们排在前面，若其中任何一个缺失，安装或更新会被拒绝，并以窗口所用的语言给出清晰的提示。
* **签名，默认为警告：**没有有效签名的修订仍会被安装或更新，窗口和命令行都会明确指出它没有签名；在设置中选择*要求*（`"signature_policy": "require"`）则会改为拒绝它。
* **先前副本：**窗口可以恢复项目的先前副本，或删除保留的副本，`status` 会显示副本数量及其占用的磁盘空间。
* **一个命令行工具和一个可选的桌面界面:** `armor-updater status`/`install`/`update`,以及一个 Qt Quick 界面(`pip install ".[gui]"`),覆盖生态系统的八种语言。

## 🧩 在 A.R.M.O.R. 中的角色

ARMOR-UPDATER 是为在 PC 上保存家族副本的人准备的桌面工具：它找出机器上的 A.R.M.O.R. 仓库，与 GitHub 对比，并逐个安装或更新，替换任何东西之前都先验证。它与 [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) 在 CM5 上驱动的更新不同（那些经过 [ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)）：这个是给开发者的机器用的。

| 对话对象 | 方式 | 用途 |
|---|---|---|
| 本地工作区 | 带有效 `armor.project.json` 的文件夹 | 已安装什么、什么版本 |
| GitHub | `api.github.com`、`raw.githubusercontent.com` 和 git；`GITHUB_TOKEN` 可选 | 账户中每个仓库的最新版本 |
| ARMOR-COMMON | 项目可在 `requires` 中列出它 | 每批都排在最前：每次构建都需要它 |
| ARMOR-DEVOPS | 另一套 | ARMOR-STUDIO 在 CM5 上驱动的更新走它，而不是本工具 |

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 安全与防护

| 威胁 | 防御 |
|---|---|
| 安装了被攻破的代码 | 提交会用 `data/allowed_signers`（OpenSSH 格式）中的签名者校验，其指纹固定在 `signature.py`；只改文件不改固定值会使所有检查失败（保持关闭）；`signature_policy` 为 `warn`（默认：照常安装并说明未签名）或 `require`（拒绝） |
| 安装到一半或原地替换 | 从不原地替换：全部在独立的暂存克隆中构建并验证，再用两次带日志的重命名（`promotion.json`）提升；被替换的副本保存在 `.armor-updater/backups/`（最新三份） |
| 两个更新程序同时操作一个工作区 | 6 小时后过期的锁（`.armor-updater/lock`） |
| 未构建的依赖 | ARMOR-COMMON 排在最前，没有它就不构建项目；清单的可选字段 `requires` 决定批次顺序，并用窗口所用语言清楚地拒绝安装 |
| 本地修改丢失 | 更新到已安装的提交时什么也不做；真正未提交的本地修改会被直接拒绝 |
| 虚假发现 | 只有带有效 `armor.project.json` 且声明 `ecosystem: "A.R.M.O.R."` 的项目才算数；远程时对账户的每个公开仓库做同样的检查 |
| GitHub 缓慢或宕机 | 请求超时 10 秒，最多同时 8 个，重试 3 次（基础等待 0.5 秒），`ls-remote` 20 秒；已考虑 `raw.githubusercontent.com` 数分钟的延迟 |

每次尝试无论成败，都会在本地证据日志中追加一行（项目、前后的版本和提交、失败原因）。安装需要 `git` 和每个仓库的构建工具；除非选择 `require`，签名只给出警告；尚未对家族的每个仓库端到端运行，也没有独立审查。

## 🔌 接口

| 路由 | 认证 | 作用 |
|---|---|---|
| `armor-updater --cli status` | - | 已安装内容、其版本以及 GitHub 上的最新版本；`--workspace D`、`--offline`（仅本地）、`--notes`（各项目的真实说明）、`--json`（机器可读） |
| `armor-updater --cli install <project>` | - | 克隆、构建并安装一个尚未安装的项目；`--no-build` 只克隆 |
| `armor-updater --cli update <project>` | - | 更新已安装的项目，先构建并验证再就位；`--no-build` 只拉取 |
| `armor-updater --cli rollback <project>` | - | 放回被替换副本的最新备份 |
| `armor-updater --cli backups [<project>]` | - | 列出被替换副本的备份及其占用磁盘；`--prune N` 每个项目只保留最新 N 份 |
| `armor-updater --version` | - | 工具版本 |

窗口（Qt Quick，`pip install ".[gui]"`，在 Windows 上由 `run-gui.vbs` 启动）显示同样的状态，安装和更新一个项目，恢复某项目的上一份副本或删除保留的副本，并说明某个修订未签名；它有八种语言（`i18n.py`、`i18n_pt.py`、`i18n_recovery.py`、`result_text.py`），只在 Windows 上运行过。完整参考：[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) 和 [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)。

## ⚙️ 配置

| 设置 | 默认值 | 作用 |
|---|---|---|
| `--workspace` | 工具的上级文件夹 | 要扫描的工作区根目录 |
| `GITHUB_TOKEN` | 可选 | 提高 GitHub 每小时 60 次请求的限制；只读取，从不写入 |
| `signature_policy` | warn | `warn` 照常安装并说明未签名；`require` 拒绝；保存在 `~/.armor_updater_settings.json` |
| 保留的备份 | 3 | 每个项目最新的三份；`backups --prune N` 可更改 |
| 锁 | 6 h | 超过此时间的锁会被忽略 |

`.env.example` 列出仓库构建可能读取的变量。窗口语言跟随 `~/.armor_updater_settings.json`（以及旧的 `~/.armor_updater_lang.json`）。

## 🚀 快速开始

**要求：** Python 3.10+、`git` 以及所装仓库的构建工具；可选：桌面窗口用的 PySide6。

```bash
pip install -e ".[dev]"                     # 或 ".[dev,gui]"（可选的 Qt Quick 窗口）
python -m pytest tests -q                   # 321 项，约六分钟
armor-updater --cli status                  # 每个仓库的本地和 GitHub 状态
armor-updater --cli install ARMOR-NETWORK   # 克隆、构建并安装一个尚未安装的仓库
armor-updater --cli update ARMOR-NETWORK    # 更新已安装的仓库（先构建并验证再就位）
armor-updater --cli rollback ARMOR-NETWORK  # 放回被替换副本的最新备份
```

请参阅 [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)。

## 🧪 测试

```powershell
python -m pytest tests -q  # 321 项，约六分钟
python -I tools/armor_ci_validate.py
```

| 领域 | 覆盖内容 |
|---|---|
| 发现与版本 | 清单、注册表、本地与远程检测、版本解析和 GitHub 客户端 |
| 安装与更新 | 暂存、锁、日志、备份与回滚、前置要求和证据日志 |
| 签名 | 固定密钥、失败时关闭以及两种策略 |
| 命令行 | `status`、`install`、`update`、`rollback`、`backups` 及其选项 |
| 语言与窗口 | 八种语言（`test_i18n.py`）与每个结果的文本 |

`python -m unittest` 只能找到其中三项：测试套件是为 pytest 写的（`conftest.py` 在 `tests/` 中），耗时接近六分钟。GitHub Actions 在每次推送和拉取请求时运行 A.R.M.O.R. 基线：清单、版本、更新日志和 README 一致性的校验，然后是项目自身的构建和测试。 测试脚本（`test.sh`、`test.bat` 和一对 `build-test`）在测试前先运行代码检查器,再运行 `python -m mypy`（需安装 PySide6）；两个窗口以及安装和 git 辅助模块的源代码都能通过,测试则固定窗口所保持的状态。

## 🏗️ 构建与发布

这是纯 Python：无需编译（`pip install -e .`）。版本记录在 `pyproject.toml`、`armor.project.json` 和 README 徽章中（读取自清单）；每个版本在 [CHANGELOG.md](CHANGELOG.md) 中都有对应条目。发布版本发布在 GitHub 上。

## 🩺 故障排除

| 你看到 | 原因 | 处理 |
|---|---|---|
| 更新提示什么也没发生 | 项目已处于 GitHub 上的提交 | 无需处理 |
| 因本地修改而拒绝更新 | 副本有未提交的修改 | 提交或暂存后再更新 |
| 提示某个前置要求未安装 | 清单在 `requires` 中列出了它 | 先安装该项目（批量操作已排好顺序） |
| 窗口或命令行提示该修订未签名 | `signature_policy` 为 `warn`，所以照常安装并提示 | 在设置中选择 `require` 以拒绝未签名的修订 |
| 更新弄坏了东西 | 新修订能构建但行为不对 | `armor-updater --cli rollback <项目>` 放回最新备份 |

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   清单、列表、目录
│   ├── detect.py github_client.py version_parse.py            本地与远程发现、版本
│   ├── install.py git_ops.py staging.py                       分阶段安装与更新
│   ├── promotion.py releases.py deploy_category.py            锁、日志、备份、布局
│   ├── signature.py                                           签名更新与固定密钥
│   ├── evidence.py settings.py console_flags.py               日志、设置、选项
│   ├── main.py                                                命令行
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     八种语言
│   ├── gui.py qt_gui.py qml/                                  可选的 Qt Quick 窗口
│   └── data/ assets/                                          allowed_signers 与图标
├── tests/                                                     28 个模块 321 项测试
├── docs/                                                      CLI_REFERENCE.md、QML_DESKTOP_GUI.md
├── tools/                                                     共用的 CI 检查、启动器和 generate_app_icon.py
├── images/                                                    横幅图、图标和 README 的图片
├── .github/                                                   CI 工作流、仪表板通知、议题和 pull request 模板
├── armor.project.json                                         清单：版本、角色、成熟度
├── pyproject.toml                                             包元数据、入口
├── CHANGELOG.md                                               每个版本的变化
├── run-gui.vbs                                                在 Windows 上无控制台地打开窗口
├── run.sh run.bat                                             启动（共用流程）
├── build.sh build.bat                                         构建并测试（共用流程）
├── build-test.sh build-test.bat                               构建、测试并打包
├── test.sh test.bat                                           只运行测试，不改版本
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

* Qt Quick 窗口只在 Windows 上运行过。
* 尚未对家族的每个仓库端到端运行。
* 安装需要 `git` 和每个仓库的构建工具。
* 没有独立的安全审查。

**下一步**

* 对家族的每个仓库端到端运行，并在 Linux 和 macOS 上试用。

## 🌍 语言

README 和文本提供英语、西班牙语、法语、意大利语、德语、汉语、日语和欧洲葡萄牙语版本。

## 🔗 相关项目

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）是一个由相互独立的仓库组成的周界安全系统。每个仓库都有自己的版本、自己的测试和自己的 README；这是整个系列：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - 消息契约、验证器、一致性向量和生成的类型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - 面向 ESP32-S3 的现场节点固件，配三个雷达和自带的网页面板
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - 太阳能逆变器和电池的协议，以及网关节点的消息
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 电气节点：电表、电网读数的消息和切换规则
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 报警节点与面板：防区、布防、延时、警笛和 PIN，可配合服务器也可独立使用
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - 触摸面板：壁挂屏幕上的系统状态、布防与确认，以及语音助手的所在
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - 本地网络：其设备、互联网以及变化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央协调器：遥测、报警、设备、太阳能读数和摄像头
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - 网页控制台：摄像头、雷达、报警、太阳能以及 2D/3D 场地设计器
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - 带实时 2D/3D 雷达的 Android 操作员客户端
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone 操作员客户端
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 视觉推理策略，会解释其决策且从不驱动设备
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - 面向 Jetson Orin NX 的摄像头区域、遮罩和检测规则
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 离线语音意图，附带无法伪造的确认
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 外壳、电子器件和台架验收矩阵
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - 部署、CM5 测试台、备份和 TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 带可重复故障的离线遥测模拟器
* **ARMOR-UPDATER**（本仓库） - 检测、安装和更新生态系统自身的仓库
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 架构、安全基线和能力矩阵

## 📚 文档

* [命令行参考](docs/CLI_REFERENCE.md)：每个命令和选项
* [Qt Quick 窗口](docs/QML_DESKTOP_GUI.md)：桌面窗口的工作方式
* [能力矩阵：哪些已被证明，哪些没有](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [项目目录：版本以及各仓库之间如何相互依赖](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [本仓库的更新日志](CHANGELOG.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `python -I tools/armor_ci_validate.py` 和测试：两者都必须通过。请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 和[行为准则](CODE_OF_CONDUCT.md)。
* README 提供八种语言，由 ARMOR-DOCS 中的源文件生成：文本的修改在那里进行。
* 组件之间消息的变更从 ARMOR-COMMON 开始。
* 不要把仅仅构建过的东西描述为已在板子上运行。
* 请私下报告漏洞：[SECURITY.md](SECURITY.md)。问题、想法和报告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - 见 [LICENSE](LICENSE)。
