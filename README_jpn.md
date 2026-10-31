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
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Tests-321%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**正直さのチェック - 今日動いているもの:** マニフェストによる検出、バージョン比較、署名の確認、ロック・ジャーナル・バックアップ・ロールバックを備えた段階的なインストールと更新、証跡ログ、8 言語のインターフェース表はテスト済みです（321 件のテスト）。Qt Quick のシェルは Windows で実行されました。ファミリーのすべてのリポジトリに対して端から端まで実行したわけではなく、行うインストールにはマシンに `git` と各リポジトリ自身のビルドツールが必要です。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.1.7` |
| 成熟度 | 確立 |
| 役割 | 1 つずつ、PC 上のファミリーをインストール・更新するデスクトップツール |
| 技術 | Python 3.10+、git。任意で PySide6（Qt Quick） |
| テスト | 321 件（`python -m pytest tests -q`、約 6 分） |
| インターフェース | `armor-updater --cli`（`status`、`install`、`update`、`rollback`、`backups`）と 8 言語の Qt Quick ウィンドウ |
| 動作環境 | Python と git のある PC（ウィンドウは Windows でのみ動作確認） |
| 実機での確認 | 該当なし：デスクトッププログラムで、Qt Quick シェルは Windows で動かしました |
| ライセンス | GPL-3.0-or-later |

**移動先：** [概要](#-概要) · [アーキテクチャ](#-アーキテクチャ) · [セキュリティ](#-セキュリティと安全) · [インターフェース](#-インターフェース) · [設定](#-設定) · [クイックスタート](#-クイックスタート) · [テスト](#-テスト) · [トラブルシューティング](#-トラブルシューティング) · [構成](#-リポジトリの構成) · [関連](#-関連プロジェクト)

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟡 | マニフェストの検出、バージョン比較、段階的なインストールと更新は動作します。ファミリーのすべてのリポジトリに対して端から端まで実行したわけではありません。 |
| テスト | 🟢 | 321 件のテストが通ります（`python -m pytest tests -q`）：検出、バージョン比較、署名の確認、ロック・ジャーナル・バックアップ・ロールバック付きの段階的インストール、証拠ログ、8 言語の表。 |
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

| 連携先 | 方法 | 目的 |
|---|---|---|
| ローカルのワークスペース | 有効な `armor.project.json` を持つフォルダー | インストール済みの内容とバージョン |
| GitHub | `api.github.com`、`raw.githubusercontent.com`、git。`GITHUB_TOKEN` は任意 | アカウントの各リポジトリの最新バージョン |
| ARMOR-COMMON | プロジェクトは `requires` に挙げられる | どのバッチでも最初：すべてのビルドが必要とする |
| ARMOR-DEVOPS | 別物 | ARMOR-STUDIO が CM5 で行う更新はこのツールではなくそちらを通る |

## 🏛️ アーキテクチャ

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-UPDATER architecture: the person, the workspace and GitHub, the modules of the updater and the live checkout and build it changes" width="100%">
</p>

## 🔒 セキュリティと安全

| 脅威 | 防御 |
|---|---|
| 侵害されたコードがインストールされる | コミットは `data/allowed_signers`（OpenSSH 形式）の署名者で検証し、その指紋は `signature.py` に固定。ファイルだけ変えると全検査が失敗します（閉じる側）。`signature_policy` は `warn`（既定：インストールして未署名と表示）か `require`（拒否） |
| 中途半端なインストールや、その場での置き換え | その場では置き換えません。独立したステージングクローンでビルドと検証を終え、ジャーナル付きの 2 回のリネーム（`promotion.json`）で昇格します。置き換えたチェックアウトは `.armor-updater/backups/` に最新 3 つ残します |
| 1 つのワークスペースで 2 つの更新が動く | 6 時間で期限切れになるロック（`.armor-updater/lock`） |
| ビルドされていない依存 | ARMOR-COMMON が最初で、それなしではビルドしません。マニフェストの任意項目 `requires` でバッチの順序を決め、足りなければウィンドウの言語で分かりやすく拒否します |
| ローカルの変更が失われる | すでに入っているコミットへの更新は何もしません。本当にコミットされていないローカル変更があれば完全に拒否します |
| 偽の検出 | `ecosystem: "A.R.M.O.R."` を宣言する有効な `armor.project.json` があるプロジェクトだけが対象です。リモートでもアカウントの公開リポジトリを同様に検査します |
| GitHub が遅い、または停止 | リクエストのタイムアウト 10 秒、同時 8 件まで、3 回再試行（基本待機 0.5 秒）、`ls-remote` は 20 秒。`raw.githubusercontent.com` の数分の遅れも考慮 |

成功か失敗かを問わず、すべての試行がローカルの証跡ログに 1 行追加されます（プロジェクト、前後のバージョンとコミット、失敗の理由）。インストールには `git` と各リポジトリのビルドツールが必要です。署名は `require` を選ばない限り警告のみです。ファミリーの全リポジトリで通しで動かしたことはなく、第三者によるレビューもありません。

## 🔌 インターフェース

| ルート | 認証 | 内容 |
|---|---|---|
| `armor-updater --cli status` | - | インストール済みの内容、バージョン、GitHub 上の最新。`--workspace D`、`--offline`（ローカルのみ）、`--notes`（各プロジェクトの実際のメモ）、`--json`（機械可読） |
| `armor-updater --cli install <project>` | - | まだ入っていないプロジェクト 1 つをクローン・ビルド・インストール。`--no-build` はクローンのみ |
| `armor-updater --cli update <project>` | - | インストール済みを更新（置き換える前にビルドと検証）。`--no-build` は取得のみ |
| `armor-updater --cli rollback <project>` | - | 置き換えたチェックアウトの最新バックアップを戻す |
| `armor-updater --cli backups [<project>]` | - | 置き換えたチェックアウトのバックアップと使用ディスク量を一覧。`--prune N` で各プロジェクトの最新 N 個を残す |
| `armor-updater --version` | - | ツールのバージョン |

ウィンドウ（Qt Quick、`pip install ".[gui]"`、Windows では `run-gui.vbs` で起動）は同じ状態を表示し、プロジェクトを 1 つインストール・更新し、前のコピーを復元または保管コピーを削除し、リビジョンが未署名であることを表示します。8 言語で書かれており（`i18n.py`、`i18n_pt.py`、`i18n_recovery.py`、`result_text.py`）、Windows でのみ動作確認済みです。詳細は [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) と [docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)。

## ⚙️ 設定

| 設定 | 既定値 | 内容 |
|---|---|---|
| `--workspace` | ツールの親フォルダー | スキャンするワークスペースのルート |
| `GITHUB_TOKEN` | 任意 | GitHub の 1 時間 60 リクエストの上限を引き上げる（読むだけで書き込まない） |
| `signature_policy` | warn | `warn` はインストールして未署名と表示、`require` は拒否。`~/.armor_updater_settings.json` に保存 |
| 保管するバックアップ | 3 | 各プロジェクトの最新 3 つ。`backups --prune N` で変更 |
| ロック | 6 h | これより古いロックは無視 |

`.env.example` は、リポジトリのビルドが読む変数を示します。ウィンドウの言語は `~/.armor_updater_settings.json`（と旧 `~/.armor_updater_lang.json`）に従います。

## 🚀 クイックスタート

**要件：** Python 3.10+、`git`、インストールするリポジトリのビルドツール。任意：デスクトップウィンドウ用の PySide6。

```bash
pip install -e ".[dev]"                     # または ".[dev,gui]"（任意の Qt Quick ウィンドウ用）
python -m pytest tests -q                   # 321 件、約 6 分
armor-updater --cli status                  # 各リポジトリのローカルと GitHub の状態
armor-updater --cli install ARMOR-NETWORK   # まだ入っていないリポジトリを 1 つクローン・ビルド・インストール
armor-updater --cli update ARMOR-NETWORK    # インストール済みを更新（置き換え前にビルドと検証）
armor-updater --cli rollback ARMOR-NETWORK  # 置き換えたチェックアウトの最新バックアップを戻す
```

[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

## 🧪 テスト

```powershell
python -m pytest tests -q  # 321 件、約 6 分
python -I tools/armor_ci_validate.py
```

| 分野 | 対象 |
|---|---|
| 検出とバージョン | マニフェスト、レジストリ、ローカルとリモートの検出、バージョン解析、GitHub クライアント |
| インストールと更新 | ステージング、ロック、ジャーナル、バックアップ、ロールバック、要件、証跡ログ |
| 署名 | 固定された鍵、閉じる側の失敗、2 つのポリシー |
| コマンドライン | `status`、`install`、`update`、`rollback`、`backups` とそのオプション |
| 言語とウィンドウ | 8 言語（`test_i18n.py`）と各結果の文言 |

`python -m unittest` では 3 件しか見つかりません。テストは pytest 向けに書かれ（`conftest.py` は `tests/` にあります）、約 6 分かかります。GitHub Actions は push と pull request のたびに A.R.M.O.R. の基本検査（マニフェスト、バージョン、変更履歴、README の一致）と、プロジェクト自身のビルドとテストを実行します。 テスト用スクリプト（`test.sh`、`test.bat`、`build-test` の 2 つ）は、テストの前にリンターと `python -m mypy`（PySide6 が必要）を実行します。2 つのウィンドウとインストール・git ヘルパーのソースはこれを通り、テストがウィンドウの保持する状態を固定します。

## 🏗️ ビルドとリリース

純粋な Python なので、コンパイルするものはありません（`pip install -e .`）。バージョンは `pyproject.toml`、`armor.project.json`、README のバッジ（マニフェストから読み取り）にあり、各バージョンには [CHANGELOG.md](CHANGELOG.md) にエントリーがあります。リリースは GitHub で公開されます。

## 🩺 トラブルシューティング

| 表示 | 原因 | 対処 |
|---|---|---|
| 更新が「何も起きなかった」と言う | プロジェクトはすでに GitHub と同じコミット | 対処不要 |
| ローカルの変更のため更新が拒否される | チェックアウトにコミットされていない変更がある | コミットまたは退避してから更新 |
| 要件が未インストールと表示される | マニフェストの `requires` に挙がっている | そのプロジェクトを先にインストール（バッチは順序付け済み） |
| ウィンドウやコマンドラインが未署名のリビジョンだと表示する | `signature_policy` が `warn` なのでインストールして知らせる | 設定で `require` を選ぶと未署名のリビジョンを拒否 |
| 更新で何かが壊れた | 新しいリビジョンはビルドできるが挙動が悪い | `armor-updater --cli rollback <プロジェクト>` で最新のバックアップを戻す |

## 📂 リポジトリの構成

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-UPDATER" width="100%">
</p>

<details>
<summary>ツリーのテキスト版</summary>

```text
ARMOR-UPDATER/
├── src/armor_updater/
│   ├── project_manifest.py registry.py ecosystem_catalog.py   マニフェスト、一覧、カタログ
│   ├── detect.py github_client.py version_parse.py            ローカルとリモートの検出、バージョン
│   ├── install.py git_ops.py staging.py                       段階的なインストールと更新
│   ├── promotion.py releases.py deploy_category.py            ロック、ジャーナル、バックアップ、配置
│   ├── signature.py                                           署名付き更新と固定された鍵
│   ├── evidence.py settings.py console_flags.py               ログ、設定、フラグ
│   ├── main.py                                                コマンドライン
│   ├── i18n.py i18n_pt.py i18n_recovery.py result_text.py     8 言語
│   ├── gui.py qt_gui.py qml/                                  任意の Qt Quick ウィンドウ
│   └── data/ assets/                                          allowed_signers とアイコン
├── tests/                                                     28 モジュール 321 件
├── docs/                                                      CLI_REFERENCE.md、QML_DESKTOP_GUI.md
├── tools/                                                     共通の CI 検査、ランチャー、generate_app_icon.py
├── images/                                                    バナー、アイコン、README の画像
├── .github/                                                   CI ワークフロー、ダッシュボード通知、Issue と Pull Request のテンプレート
├── armor.project.json                                         マニフェスト：版・役割・成熟度
├── pyproject.toml                                             パッケージ情報とエントリー
├── CHANGELOG.md                                               各バージョンの変更点
├── run-gui.vbs                                                Windows でコンソールなしにウィンドウを開く
├── run.sh run.bat                                             起動（共通フロー）
├── build.sh build.bat                                         ビルドとテスト（共通フロー）
├── build-test.sh build-test.bat                               ビルド、テスト、パッケージ化
├── test.sh test.bat                                           テストのみ（版は変えません）
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ ロードマップと既知の制限

**現時点の既知の制限**

* Qt Quick ウィンドウは Windows でのみ動作確認済みです。
* ファミリーの全リポジトリで通しで動かしたことはありません。
* インストールには `git` と各リポジトリのビルドツールが必要です。
* 第三者によるセキュリティレビューはありません。

**今後**

* ファミリーの全リポジトリで通しで動かし、Linux と macOS でも試す。

## 🌍 言語

README とテキストは、英語、スペイン語、フランス語、イタリア語、ドイツ語、中国語、日本語、ヨーロッパポルトガル語で提供されています。

## 🔗 関連プロジェクト

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）は、独立したリポジトリで構成される境界セキュリティシステムです。各リポジトリは独自のバージョン、テスト、README を持ちます。ファミリーは次のとおりです：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - メッセージのコントラクト、バリデーター、適合ベクトル、生成された型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - 3 つのレーダーと独自の Web パネルを備えた ESP32-S3 向けフィールドノードのファームウェア
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - ソーラーインバーターとバッテリーのプロトコル、ゲートウェイノードのメッセージ
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 電気ノード：メーター、系統の読み取り値のメッセージ、切り替えのルール
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 警報ノードとパネル：ゾーン、警戒、遅延、サイレン、PIN。サーバーありでもなしでも動作
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - タッチパネル：壁面画面でのシステムの状態、警戒と確認応答、そして音声アシスタントの置き場
* **[ARMOR-NETWORK](https://github.com/JuanenRac/ARMOR-NETWORK)** - ローカルネットワーク：そのデバイス、インターネット、そして変化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央コーディネーター：テレメトリ、警報、デバイス、ソーラーの読み取り値、カメラ
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web コンソール：カメラ、レーダー、警報、太陽光エネルギー、2D/3D のサイトデザイナー
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - ライブの 2D/3D レーダーを備えた Android オペレータークライアント
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone オペレータークライアント
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 判断を説明し、決して作動させない視覚推論ポリシー
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Jetson Orin NX 向けのカメラゾーン、マスク、検出ルール
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 偽造できない確認つきのオフライン音声インテント
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 筐体、電子回路、ベンチ受け入れマトリクス
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - デプロイ、CM5 テストベンチ、バックアップ、TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 再現可能な障害を持つオフラインのテレメトリシミュレーター
* **ARMOR-UPDATER**（このリポジトリ） - エコシステム自身のリポジトリを検出、インストール、更新
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - アーキテクチャ、セキュリティのベースライン、機能マトリクス

## 📚 ドキュメント

* [コマンドラインリファレンス](docs/CLI_REFERENCE.md)：全コマンドとオプション
* [Qt Quick ウィンドウ](docs/QML_DESKTOP_GUI.md)：デスクトップウィンドウの仕組み
* [機能マトリクス：何が証明され、何が証明されていないか](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [プロジェクトカタログ：バージョンと、リポジトリ同士の依存関係](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [このリポジトリの変更履歴](CHANGELOG.md)

## 🤝 コントリビュートとコミュニティ

* Pull Request の前に `python -I tools/armor_ci_validate.py` とテストを実行してください。どちらも通る必要があります。[CONTRIBUTING.md](CONTRIBUTING.md) と[行動規範](CODE_OF_CONDUCT.md)を参照してください。
* README は 8 言語で提供され、ARMOR-DOCS のソースから生成されます。文面の変更はそちらで行います。
* コンポーネント間のメッセージの変更は ARMOR-COMMON から始めます。
* ビルドしただけのものを、ボード上で動いているかのように書かないでください。
* 脆弱性は非公開で報告してください：[SECURITY.md](SECURITY.md)。質問、アイデア、報告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE) を参照してください。
