"""既存動画のタイトル・概要欄・タグ・サムネイル・公開状態を更新するスクリプト。

指定しなかった項目は現状維持。--privacy public はユーザーの明示的な指示があるときだけ使うこと。

usage:
  yt_update.py --token tokens/main.json --video-id XXXX \
    [--title "新タイトル"] [--description-file desc.txt] [--description "本文"] \
    [--tags "a,b"] [--thumbnail thumb.jpg] [--privacy public] [--expect-handle "@my-channel"]
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", required=True)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--expect-handle", default=None,
                    help="指定するとチャンネル不一致時に中止（推奨）")
    ap.add_argument("--title", default=None)
    ap.add_argument("--description", default=None)
    ap.add_argument("--description-file", default=None)
    ap.add_argument("--tags", default=None, help="カンマ区切り（既存タグは置き換え）")
    ap.add_argument("--thumbnail", default=None)
    ap.add_argument("--privacy", default=None,
                    choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    creds = load_creds(args.token)
    yt = build("youtube", "v3", credentials=creds)

    if args.expect_handle:
        ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
        actual = ch["snippet"].get("customUrl", "").lower()
        expect = args.expect_handle.lower()
        if not expect.startswith("@"):
            expect = "@" + expect
        if actual != expect:
            print(f"ABORT: チャンネル不一致 {actual} != {expect}", file=sys.stderr)
            sys.exit(1)

    items = yt.videos().list(part="snippet,status", id=args.video_id).execute()["items"]
    if not items:
        print(f"ABORT: 動画が見つかりません: {args.video_id}", file=sys.stderr)
        sys.exit(1)
    v = items[0]
    sn, st = v["snippet"], v["status"]
    print(f"対象動画: {sn['title']} ({st['privacyStatus']})", flush=True)

    changed = []
    if args.title:
        sn["title"] = args.title
        changed.append("title")
    desc = args.description
    if args.description_file:
        desc = Path(args.description_file).expanduser().read_text(encoding="utf-8")
    if desc is not None:
        sn["description"] = desc
        changed.append("description")
    if args.tags is not None:
        sn["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
        changed.append("tags")

    if changed:
        yt.videos().update(part="snippet", body={
            "id": args.video_id,
            "snippet": {
                "title": sn["title"],
                "description": sn.get("description", ""),
                "tags": sn.get("tags", []),
                "categoryId": sn["categoryId"],
                "defaultLanguage": sn.get("defaultLanguage"),
                "defaultAudioLanguage": sn.get("defaultAudioLanguage"),
            },
        }).execute()
        print("snippet更新:", ", ".join(changed), flush=True)

    if args.privacy:
        yt.videos().update(part="status", body={
            "id": args.video_id,
            "status": {
                "privacyStatus": args.privacy,
                "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
            },
        }).execute()
        print(f"公開状態: {st['privacyStatus']} -> {args.privacy}", flush=True)

    if args.thumbnail:
        thumb = Path(args.thumbnail).expanduser()
        yt.thumbnails().set(videoId=args.video_id,
                            media_body=MediaFileUpload(str(thumb))).execute()
        print("サムネイル設定完了:", thumb.name, flush=True)

    if not changed and not args.privacy and not args.thumbnail:
        print("変更項目が指定されていません。--help を確認してください。")
    else:
        print("URL: https://youtu.be/" + args.video_id)


if __name__ == "__main__":
    main()
