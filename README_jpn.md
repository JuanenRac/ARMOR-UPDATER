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
  🇯🇵 <b>日本語</b> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### 実行中のマシン上のすべての A.R.M.O.R. リポジトリを検出し、インストールし、更新します（必須の依存関係がない Python プログラム）

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

**正直さのチェック - 今日動いているもの:** マニフェストによる検出、バージョン比較、署名の確認、ロック・ジャーナル・バックアップ・ロールバックを備えた段階的なインストールと更新、証跡ログ、8 言語のインターフェース表はテスト済みです（288 件のテスト）。Qt Quick のシェルは Windows で実行されました。ファミリーのすべてのリポジトリに対して端から端まで実行したわけではなく、行うインストールにはマシンに `git` と各リポジトリ自身のビルドツールが必要です。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.1.5` |
| 成熟度 | 確立 |
| テスト | 288 (`python -m pytest tests -q`) |
| 技術 | Python 3.10+ (standard library only; PySide6 optional for the desktop shell) |
| 実機での確認 | 該当なし：デスクトッププログラムで、Qt Quick シェルは Windows で動かしました |

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟡 | マニフェストの検出、バージョン比較、段階的なインストールと更新は動作します。ファミリーのすべてのリポジトリに対して端から端まで実行したわけではありません。 |
| テスト | 🟢 | 288 件のテストが通ります（`python -m pytest tests -q`）：検出、バージョン比較、署名の確認、ロック・ジャーナル・バックアップ・ロールバック付きの段階的インストール、証拠ログ、8 言語の表。 |
| インターフェース | 🟡 | Qt Quick のシェルは Windows でのみ実行しています。 |
| セキュリティ | 🟡 | 署名の確認と証拠ログはホストでテスト済みです。独立したレビューはありません。 |
| アップデート | 🟡 | 実行するインストールには、マシンに `git` と各リポジトリ固有のビルドツールが必要です。 |
| ドキュメント | 🟢 | 8 言語と変更履歴は最新です。 |

## 🎯 概要

* **固定リストのない検出：**ローカルのフォルダーは、`ecosystem: "A.R.M.O.R."` を宣言する有効な `armor.project.json` を持った時点で加わります。リモートでは、アカウントのすべての公開リポジトリが同じ方法で調べられます。`GITHUB_TOKEN` は任意で、GitHub の 1 時間 60 リクエストの上限を上げるだけです。
* **インストールも更新も、その場では行いません：**新しいプロジェクトも更新も、まず独立したステージングのクローンでビルドして検証し、ビルドが成功してから反映します。ジャーナルに記録された 2 回の名前変更を行い、置き換えたチェックアウトは `.armor-updater/backups/` に（最新の 3 件）保存されます。インストール済みと同じコミットへの更新は何もしません。コミットされていない実際のローカル変更は即座に拒否され、黙って破棄されることはありません。名前変更の間のクラッシュは次の実行で修復され、`rollback` は最新のバックアップを戻します。
* **一度に一つ、順番どおりに：**ロックにより、2 つの更新ツールが同じワークスペースで同時に動くことはありません。一括処理は ARMOR-COMMON から始まり（すべてのビルドが必要とします）、それがなければプロジェクトはビルドされません。
* **証跡:** 成功・失敗を問わず、すべての試行はプロジェクト名、前後のバージョンとコミット、失敗の理由をローカルのログに一行追加する。
* **前提条件：**マニフェストは任意のフィールド `requires` に、先にインストールしておくべきプロジェクトを列挙できます。一括処理ではそれらが先頭に置かれ、いずれかが欠けている場合、インストールや更新は、ウィンドウの言語で分かりやすいメッセージとともに拒否されます。
* **署名、既定は警告：**有効な署名のないリビジョンも、そのままインストールまたは更新され、ウィンドウとコマンドラインは署名されていないことを明示します。設定で*必須*（`"signature_policy": "require"`）を選ぶと、代わりに拒否されます。
* **以前のコピー：**ウィンドウからプロジェクトの以前のコピーを復元したり、保管されているコピーを削除したりでき、`status` はコピーの数とそれが使うディスク容量を表示します。
* **CLI と任意のデスクトップシェル:** `armor-updater status`/`install`/`update`、およびエコシステムの 8 言語に対応した Qt Quick インターフェース(`pip install ".[gui]"`)。

## 🧩 A.R.M.O.R. での役割

ARMOR-UPDATER は、PC にファミリーのコピーを持つ人のためのデスクトップツールです。マシン上の A.R.M.O.R. リポジトリを見つけ、GitHub と比較し、何かを置き換える前に検証しながら 1 つずつインストール・更新します。[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) が CM5 上で行う更新（[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS) を通るもの）とは別で、これは開発者のマシン用です。

## 📂 リポジトリの構成

```text
ARMOR-UPDATER/
├── src/armor_updater/  project_manifest, registry, detect (local), github_client, install (staged install and update) + git_ops + staging + promotion (lock, journal, backups), signature (signed updates), evidence, main (CLI), settings, version_parse,
│                       i18n + i18n_pt + i18n_recovery + result_text (eight languages), gui / qt_gui / qml (the Qt Quick shell)
├── tools/              armor_ci_validate.py, _armor_readme_parity.py, armor_project_tool.py (vendored from ARMOR-COMMON), generate_app_icon.py
├── tests/              18 test modules
└── docs/               CLI_REFERENCE.md, QML_DESKTOP_GUI.md
```

## 🛠️ 開発環境

**必要なもの:** Python 3.10+, `git` と、インストールするリポジトリのビルドツール, 任意：デスクトップシェル用の PySide6

```bash
pip install -e ".[dev]"                                # or ".[dev,gui]" for the optional Qt Quick desktop shell
python -m pytest tests -q                              # 288 tests
armor-updater --cli status                              # local + GitHub state of every repository
armor-updater --cli install ARMOR-NETWORK               # clone, build and install one repository that is not installed yet
armor-updater --cli update ARMOR-NETWORK                # update an installed one (built and verified before it is put in place)
armor-updater --cli rollback ARMOR-NETWORK              # put the newest backup of a replaced checkout back
```

`docs/CLI_REFERENCE.md` を参照してください。

## 🔗 関連プロジェクト

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）は、独立したリポジトリで構成される周辺警備システムです。それぞれに独自のバージョン、テスト、README があります。ファミリーは次のとおりです：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - メッセージ契約、検証器、適合性ベクトル、生成された型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - ESP32-S3 用フィールドノードのファームウェア。レーダー 3 基と独自の Web パネル付き
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - 太陽光インバーターとバッテリーのプロトコル、およびゲートウェイノードのメッセージ
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 電気ノード：電力量計、電力網の計測メッセージ、開閉のルール
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 警報ノードと警報盤：警戒区域、警戒セット、遅延、サイレン、PIN。サーバーがあってもなくても
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - タッチパネル：壁面ディスプレイでのシステム状態表示、警戒・確認操作、音声アシスタントの拠点
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - ローカルネットワーク：機器、インターネット、そして変化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央コーディネーター：テレメトリ、アラーム、デバイス、太陽光の測定値、カメラ
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web コンソール：カメラ、レーダー、アラーム、太陽光発電、2D/3D サイト設計
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - リアルタイム 2D/3D レーダー付きの Android オペレータークライアント
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone オペレータークライアント
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 判断を説明し、決して動作しない視覚推論ポリシー
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Jetson Orin NX 向けのカメラのゾーン、マスク、検知ルール
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 偽造できない確認を備えたオフライン音声インテント
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 筐体、電子部品、ベンチ受け入れマトリクス
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - デプロイ、CM5 テストベンチ、バックアップ、TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 再現可能な故障を備えたオフラインのテレメトリシミュレーター
* **ARMOR-UPDATER** (このリポジトリ) - エコシステム自身のリポジトリを検出し、インストールし、更新する
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - アーキテクチャ、セキュリティ基準、機能マトリクス

## 📚 ドキュメントとコミュニティ

詳しくは：

* [機能マトリクス：実証済みのものとそうでないもの](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [プロジェクト一覧：バージョンとリポジトリ間の依存関係](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [ライセンス（GPL-3.0-or-later）](LICENSE)
* 質問・提案・報告：electrohobby3d@gmail.com

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE) を参照。
