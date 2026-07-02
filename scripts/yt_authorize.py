"""YouTubeチャンネル用OAuthトークン発行スクリプト。

ブラウザが開くので、チャンネルを管理するGoogleアカウントでログインし、
「どのチャンネルとして認証するか」を選択する。1チャンネル=1トークン。

usage:
  yt_authorize.py --client ~/youtube-connect/client_secret.json --out ~/youtube-connect/tokens/main.json
  yt_authorize.py --from-token <発行済みトークン> --out <保存先>   # client情報を既存トークンから流用
"""
import argparse
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--client", help="GCPからダウンロードした client_secret*.json")
    ap.add_argument("--from-token", help="発行済みトークンJSONからclient_id/secretを流用")
    ap.add_argument("--out", required=True, help="トークンの保存先パス")
    args = ap.parse_args()

    if args.client:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(Path(args.client).expanduser()), SCOPES)
    elif args.from_token:
        src = json.loads(Path(args.from_token).expanduser().read_text())
        client_config = {
            "installed": {
                "client_id": src["client_id"],
                "client_secret": src["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": src.get("token_uri", "https://oauth2.googleapis.com/token"),
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    else:
        ap.error("--client か --from-token のどちらかを指定してください")

    creds = flow.run_local_server(port=0, prompt="consent")

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(creds.to_json())
    os.chmod(out_path, 0o600)

    yt = build("youtube", "v3", credentials=creds)
    resp = yt.channels().list(part="snippet,statistics", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        print("警告: チャンネル情報を取得できませんでした。ブランドアカウントの選択を確認してください。")
        return

    ch = items[0]
    sn, st = ch["snippet"], ch["statistics"]
    handle = sn.get("customUrl", "")
    print(f"連携チャンネル: {sn['title']} ({handle}) id={ch['id']}")
    print(f"  登録者: {st.get('subscriberCount', '?')} / 動画数: {st.get('videoCount', '?')}")
    print(f"トークン保存先: {out_path}")
    print()
    print("--- channels.yaml に追記するエントリ（呼び名は自由に変更可） ---")
    print("channels:")
    print("  main:")
    print(f'    title: "{sn["title"]}"')
    print(f'    handle: "{handle}"')
    print(f"    token: {out_path}")


if __name__ == "__main__":
    main()
