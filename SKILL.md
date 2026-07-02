---
name: clbs-youtube-connect
description: >-
  自分のYouTubeチャンネルをClaude Codeに接続し、動画アップロード・タイトル/概要欄の編集・
  サムネイル設定・アナリティクス取得（再生数・視聴維持率・登録者増減・トラフィックソース）を
  Claudeが自律実行できるようにするスキル。初回は Google Cloud プロジェクト作成→API有効化→
  OAuth認証→トークン保存までを対話で完全ガイドし、2回目以降は「動画をアップして」
  「概要欄を直して」「サムネ設定して」「今週の再生数を見て」だけで操作できる。
  「YouTubeをつなげたい」「チャンネル連携」「チャンネル接続」「YouTube API」「動画をアップロードして」
  「概要欄を更新」「サムネイルを設定」「YouTubeアナリティクス」「再生数を取得」「視聴維持率」
  「youtube-connect」などのキーワードで必ず使用すること。
  動画の編集や台本作成は対象外（clbs-youtube-edit / clbs-youtube-script-pro を使う）。
---

# clbs-youtube-connect — YouTubeチャンネル接続・運用スキル

自分のYouTubeチャンネルを YouTube Data API v3 + YouTube Analytics API v2 で
Claude Code に接続し、アップロード・メタデータ編集・サムネ設定・分析を自動化する。

## 仕組みの全体像（最初に理解する）

特別な連携機能は使わない。構成要素は3つだけ。

1. **Google Cloud の OAuth クライアント**（client_secret.json）… ユーザー本人が自分のGCPプロジェクトで1回だけ作る
2. **チャンネルごとの OAuth トークン**（JSONファイル）… 1チャンネル = 1トークン。同じGoogleアカウントに複数チャンネルがあっても、認証時のブラウザ画面でチャンネルを選ぶため、チャンネル数だけ発行する
3. **Google APIクライアントの入った Python venv** … 同梱スクリプトをこの venv で実行する

秘密情報（client_secret / トークン）はすべて **`~/youtube-connect/`** に置く。
スキルフォルダやgit管理下のプロジェクトに置いてはいけない
（スキル更新で消える・誤ってGitHubにコミットする事故を防ぐため）。

```
~/youtube-connect/
├── .venv/                  # Python環境（setup_env.sh が作る）
├── client_secret.json      # GCPからダウンロードしたOAuthクライアント情報
├── channels.yaml           # チャンネル台帳（下記フォーマット）
└── tokens/
    ├── main.json           # チャンネルごとのトークン
    └── sub.json
```

### channels.yaml のフォーマット

```yaml
channels:
  main:                       # Claudeとの会話で使う呼び名（自由）
    title: "メインチャンネル"
    handle: "@my-channel"     # 誤爆防止ガードに使う。YouTubeのハンドル
    token: ~/youtube-connect/tokens/main.json
```

## フェーズ判定（毎回最初にやる）

`~/youtube-connect/channels.yaml` の有無を確認する。

- **ない** → セットアップモードへ（初回導入）
- **ある** → 読み込んで運用モードへ。ユーザーの依頼がどのチャンネル宛てか曖昧なら確認する

## セットアップモード（初回のみ）

ユーザーは非エンジニアの可能性が高い。専門用語は都度短く説明し、
**1ステップずつ進めて、完了を確認してから次へ進む**こと。

### STEP 1: Google Cloud 側の準備（ユーザーのブラウザ操作）

`references/gcp_setup.md` を読み、その内容に沿ってユーザーをガイドする。
ブラウザ操作は本人にやってもらい、各ステップの完了報告を待つ。要点:

- ユーザー**自身の** GCPプロジェクトを作る。講師や他人の client_secret を共有してはいけない
  （秘密情報の共有になる上、APIクォータも共有されてしまう）
- 有効化するAPIは2つ: **YouTube Data API v3** と **YouTube Analytics API**
- OAuth同意画面は External で作成し、**公開ステータスを「本番環境」に移行**する
  （テスト中のままだとトークンが7日で失効し、毎週認証し直しになるため）
- OAuthクライアントは「**デスクトップアプリ**」で作成し、JSONを
  `~/youtube-connect/client_secret.json` に保存してもらう

### STEP 2: Python環境の作成

```bash
bash <スキルのパス>/scripts/setup_env.sh
```

`~/youtube-connect/.venv` が作られ、google-api-python-client 等が入る。
以降のスクリプトは必ず `~/youtube-connect/.venv/bin/python` で実行する。

### STEP 3: チャンネルの認証（チャンネル数だけ繰り返す）

```bash
~/youtube-connect/.venv/bin/python <スキルのパス>/scripts/yt_authorize.py \
  --client ~/youtube-connect/client_secret.json \
  --out ~/youtube-connect/tokens/main.json
```

ブラウザが開くので、ユーザーに次を伝える:

1. チャンネルを管理しているGoogleアカウントでログイン
2. **アカウント選択の次に出る画面で「どのチャンネルとして認証するか」を選ぶ**（ここが肝）
3. 「このアプリはGoogleで確認されていません」と警告が出たら「詳細」→「（安全でないページに）移動」で進む（自分で作ったアプリなので問題ない）
4. 権限をすべて許可

成功するとチャンネル名・ハンドルが表示され、channels.yaml 用のエントリが出力される。
それを `~/youtube-connect/channels.yaml` に追記する（初回はファイルごと作成）。

### STEP 4: 動作確認

アナリティクス取得（読み取りのみ・安全）で疎通確認する:

```bash
~/youtube-connect/.venv/bin/python <スキルのパス>/scripts/yt_analytics.py \
  --token ~/youtube-connect/tokens/main.json --days 7
```

チャンネル名と数字が返ればセットアップ完了。ユーザーに完了を報告し、
今後できること（アップロード/概要欄/サムネ/分析）を一覧で伝える。

## 運用モード

すべて `~/youtube-connect/.venv/bin/python` で実行する。
`<スキルのパス>/scripts/` の各スクリプトは `--help` で全オプションを確認できる。

### 動画アップロード

```bash
.venv/bin/python scripts/yt_upload.py \
  --token ~/youtube-connect/tokens/main.json \
  --expect-handle "@my-channel" \
  --video /path/to/final.mp4 \
  --title "動画タイトル" \
  --description-file /path/to/description.txt \
  --tags "タグ1,タグ2" \
  --thumbnail /path/to/thumb.jpg \
  --privacy private
```

- `--expect-handle` は**必須**。トークンのチャンネルが想定と違えば中止する（複数チャンネル運用の誤爆防止）
- `--privacy` は常に `private` で上げる。ユーザーが動画をStudioで確認してから、
  依頼を受けて `yt_update.py --privacy public` で公開する。
  ユーザーが「公開でアップして」と明示した場合のみ最初から public にしてよい
- カテゴリは未指定ならチャンネルの直近動画から自動継承する

### タイトル・概要欄・サムネ・公開状態の変更（既存動画）

```bash
.venv/bin/python scripts/yt_update.py \
  --token ~/youtube-connect/tokens/main.json \
  --video-id VIDEO_ID \
  --description-file new_description.txt   # 変えたい項目だけ指定
# 他: --title / --tags / --thumbnail / --privacy public
```

指定しなかった項目は現状維持される。**公開（--privacy public）への変更は、
ユーザーの明示的な指示があるときだけ**実行する。

### アナリティクス取得

```bash
.venv/bin/python scripts/yt_analytics.py --token ... --days 7          # チャンネル週次
.venv/bin/python scripts/yt_analytics.py --token ... --video-id XXXX   # 動画単体
```

チャンネル合計・期間メトリクス（再生/総再生時間/平均視聴率/登録者増減）・
動画別ランキング・トラフィックソースが出る。
結果を報告するときは数字を並べるだけでなく、前週比や異常値など解釈を添える。

**注意**: トラフィックソース別の数字は、再生が急増しているときに SUBSCRIBER が
過剰計上されるなど Studio 画面とズレることがある。重要な判断（ブラウジング流入の
判定など）は「Studio画面が正、APIは定点観測用」とユーザーに案内する。

### 週次レポートの自動化（ルーチン）

ユーザーが「毎週自動で分析して」「定期レポートがほしい」「競合も見て企画まで提案してほしい」
と言ったら、`references/weekly_report_routine.md` を読み、その手順で
週次プロデューサーレポートのスケジュールタスクを組む。

## 安全ルール（常に適用）

- トークン・client_secret の**中身を画面に表示しない**、gitリポジトリにコピーしない
- アップロードは private が既定。**公開系の操作（public化・動画削除）は必ずユーザーの明示的指示を待つ**
- `--expect-handle` ガードを省略しない
- APIクォータは1日10,000ユニット、アップロード1本=約1,600ユニット。
  1日に5本以上アップする場合や大量操作の前はユーザーに伝える
- エラーが出たら `references/troubleshooting.md` を読んで対処する
  （invalid_grant / accessNotConfigured / quotaExceeded / サムネ403 など主要パターンを網羅済み）

## このスキルの守備範囲外

- 動画ファイルそのものの編集 → clbs-youtube-edit
- 台本・企画 → clbs-youtube-script-pro
- コメント返信・コミュニティ投稿 → 未対応（要望があれば拡張可能とだけ伝える）
