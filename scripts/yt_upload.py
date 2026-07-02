"""動画アップロードスクリプト（誤爆防止ガード付き）。

--expect-handle は必須。トークンのチャンネルが一致しなければ何もせず中止する。
privacyの既定は private（Studioで確認してから公開する運用のため）。

usage:
  yt_upload.py --token tokens/main.json --expect-handle "@my-channel" \
    --video final.mp4 --title "タイトル" --description-file desc.txt \
    [--tags "a,b,c"] [--thumbnail thumb.jpg] [--privacy private] [--category 27] [--lang ja]
"""
import argparse
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def load_creds(token_path: str) -> Credentials:
    p = Path(token_path).expanduser()
    creds = Credentials.from_authorized_user_file(str(p))
    if not creds.valid:
        creds.refresh(Request())
        p.write_text(creds.to_json())
    return creds


def check_channel(yt, expect_handle: str) -> dict:
    ch = yt.channels().list(part="snippet,contentDetails", mine=True).execute()["items"][0]
    actual = ch["snippet"].get("customUrl", "").lower()
    expect = expect_handle.lower()
    if not expect.startswith("@"):
        expect = "@" + expect
    if actual != expect:
        print(f"ABORT: トークンのチャンネル {actual} が想定 {expect} と一致しません。", file=sys.stderr)
        sys.exit(1)
    print(f"対象チャンネル: {ch['snippet']['title']} ({actual})", flush=True)
    return ch


def inherit_category(yt, ch) -> str:
    """直近アップロード動画のcategoryIdを踏襲。取れなければ27(教育)。"""
    try:
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        items = yt.playlistItems().list(
            part="contentDetails", playlistId=uploads, maxResults=1).execute()["items"]
        vid = items[0]["contentDetails"]["videoId"]
        return yt.videos().list(part="snippet", id=vid).execute()[
            "items"][0]["snippet"].get("categoryId", "27")
    except Exception:
        return "27"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", required=True)
    ap.add_argument("--expect-handle", required=True,
                    help="アップロード先チャンネルのハンドル（@付き）。不一致なら中止")
    ap.add_argument("--video", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default=None)
    ap.add_argument("--description-file", default=None)
    ap.add_argument("--tags", default="", help="カンマ区切り")
    ap.add_argument("--thumbnail", default=None)
    ap.add_argument("--privacy", default="private",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--category", default=None, help="未指定なら直近動画から継承")
    ap.add_argument("--lang", default="ja")
    args = ap.parse_args()

    desc = args.description or ""
    if args.description_file:
        desc = Path(args.description_file).expanduser().read_text(encoding="utf-8")

    video_path = Path(args.video).expanduser()
    if not video_path.exists():
        print(f"ABORT: 動画ファイルが見つかりません: {video_path}", file=sys.stderr)
        sys.exit(1)

    creds = load_creds(args.token)
    yt = build("youtube", "v3", credentials=creds)
    ch = check_channel(yt, args.expect_handle)
    category = args.category or inherit_category(yt, ch)
    print(f"categoryId: {category} / privacy: {args.privacy}", flush=True)

    body = {
        "snippet": {
            "title": args.title,
            "description": desc,
            "categoryId": category,
            "defaultLanguage": args.lang,
            "defaultAudioLanguage": args.lang,
        },
        "status": {"privacyStatus": args.privacy, "selfDeclaredMadeForKids": False},
    }
    if args.tags:
        body["snippet"]["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]

    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  uploading {int(status.progress() * 100)}%", flush=True)
    vid = resp["id"]
    print("DONE video_id:", vid, flush=True)

    if args.thumbnail:
        thumb = Path(args.thumbnail).expanduser()
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        print("サムネイル設定完了:", thumb.name, flush=True)

    print("URL: https://youtu.be/" + vid)
    print("Studio: https://studio.youtube.com/video/" + vid + "/edit")


if __name__ == "__main__":
    main()
