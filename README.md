# clbs-youtube-connect

自分のYouTubeチャンネルを Claude Code に接続し、次の操作をClaudeに任せられるようにするスキルです。

- 動画のアップロード（非公開で上げて確認後に公開、の安全運用）
- タイトル・概要欄・タグの編集
- サムネイルの設定
- アナリティクス取得（再生数・視聴維持率・登録者増減・トラフィックソース）
- 週次プロデューサーレポートの自動化（自チャンネル分析＋競合リサーチ＋次企画3案を定期実行）

初回はGoogle Cloud側の設定（無料）が必要ですが、Claudeが1ステップずつガイドします。
「YouTubeチャンネルをつなげたい」と話しかけるだけで始められます。

## 導入方法

```bash
git clone https://github.com/conlab-clbs/clbs-youtube-connect.git
mkdir -p ~/.claude/skills
cp -r clbs-youtube-connect ~/.claude/skills/
```

コピー後、Claude Code を完全再起動（`Cmd+Q` → 再度起動）してください。

## 初回セットアップの流れ（所要 15〜30分）

Claudeに「YouTubeチャンネルをつなげたい」と伝えると、以下を順番にガイドします。

1. Google Cloud プロジェクト作成（ブラウザ操作・無料）
2. YouTube Data API v3 / YouTube Analytics API の有効化
3. OAuth認証情報の作成とダウンロード
4. チャンネルの認証（ブラウザでログイン→チャンネル選択→許可）
5. 動作確認（アナリティクス取得）

複数チャンネルを持っている場合は、チャンネルごとに手順4を繰り返します。

## 必要なもの

- Claude Code（デスクトップアプリ）
- Python 3.9以上（macOSは標準搭載）
- YouTubeチャンネルの管理者権限を持つGoogleアカウント
- サムネイル設定を使う場合: YouTubeの電話番号確認（ https://www.youtube.com/verify ）

## 安全設計

- アップロードは常に**非公開（private）**で行い、確認後に公開へ切り替える運用
- チャンネル誤爆防止ガード付き（想定と違うチャンネルへの操作は自動中止）
- 認証情報は `~/youtube-connect/` にのみ保存（gitやスキルフォルダに置かない）
- トークンは自分のPCから出ません。第三者のサーバーを経由しない、Google公式APIのみの構成です

## 注意

- `client_secret.json` とトークンファイルは**パスワードと同等の秘密情報**です。
  人に送らない・スクショに写さない・gitにコミットしないでください
- YouTube Data APIの無料枠は1日10,000ユニット（動画アップロード約6本分）です
