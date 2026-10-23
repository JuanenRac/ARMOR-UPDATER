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
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-191-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.4-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**诚实性检查 - 今天真正能运行的部分:** 清单发现、版本比较、签名检查、带锁、日志、备份和回退的分阶段安装与更新、证据日志以及八种语言的界面表格都已测试（191 个测试），Qt Quick 界面已在 Windows 上运行过。它没有对家族中的每个仓库从头到尾运行过，它所做的安装需要机器上有 `git` 和各仓库自己的构建工具。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.1.4` |
| 成熟度 | 成熟 |
| 测试 | 191 (`python -m pytest tests -q`) |
| 技术栈 | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| 真实硬件 | 不适用：这是桌面程序；其 Qt Quick 界面已在 Windows 上运行过 |

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

## 📂 仓库结构

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              18 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ 开发环境

**环境要求:** Python 3.10+, `git` and the build tools of the repositories you install, optional: PySide6 for the desktop shell

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 191 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

参见 `docs/CLI_REFERENCE.md`。

## 🔗 相关项目

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）是由若干独立仓库组成的周界安防系统。每个仓库都有自己的版本、测试和 README；家族成员如下：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - 消息契约、验证器、一致性向量和生成的类型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - 适用于 ESP32-S3 的现场节点固件，带三个雷达和自带网页面板
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - 太阳能逆变器与电池的协议，以及网关节点的消息
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 电气节点：电表、电网读数消息和开关规则
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 报警节点与报警主机：防区、布防、延时、警笛和 PIN，有无服务器均可
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - 触摸面板：墙面屏幕上的系统状态、布防与确认，以及语音助手的所在
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - 本地网络：其设备、互联网以及变化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央协调器：遥测、报警、设备、太阳能读数和摄像头
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - 网页控制台：摄像头、雷达、报警、太阳能和 2D/3D 场地设计器
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - 带实时 2D/3D 雷达的 Android 操作员客户端
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 会解释决策且从不执行动作的视觉推理策略
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Jetson Orin NX 上的摄像头区域、遮罩与检测规则
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 带无法伪造确认的离线语音意图
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 外壳、电子器件和台架验收矩阵
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - 部署、CM5 测试台、备份与 TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 带可重复故障的离线遥测模拟器
* **ARMOR-UPDATER** (本仓库) - 发现、安装并更新生态系统自身的仓库
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 架构、安全基线和能力矩阵

## 📚 文档与社区

更多阅读：

* [能力矩阵：哪些已被证实，哪些没有](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [项目目录：版本以及各仓库之间的依赖](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [本仓库的变更记录](CHANGELOG.md)
* [许可证（GPL-3.0-or-later）](LICENSE)
* 问题、想法与反馈：electrohobby3d@gmail.com

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - 见 [LICENSE](LICENSE)。
