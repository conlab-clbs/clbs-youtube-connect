"""チャンネル/動画のアナリティクス取得スクリプト（読み取り専用）。

YouTube Data API v3（公開統計・動画一覧）と YouTube Analytics API v2（視聴維持率・
登録者増減・トラフィックソース等）を併用する。

usage:
  yt_analytics.py --token tokens/main.json --days 7            # チャンネル定点観測
  yt_analytics.py --token tokens/main.json --video-id XXXX     # 動画単体
"""
import argparse
import datetime
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

METRICS = ("views,estimatedMinutesWatched,averageViewDuration,"
           "averageViewPercentage,subscribersGained,subscribersLost")


def load_creds(token_path: str) -> Credentials:
    p = Path(token_path).expanduser()
    creds = Credentials.from_authorized_user_file(str(p))
    if not creds.valid:
        creds.refresh(Request())
        p.write_text(creds.to_json())
    return creds


def pretty(resp):
    if "error" in resp:
        return json.dumps(resp, ensure_ascii=False)
    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    lines = ["\t".join(headers)]
    for row in resp.get("rows", []):
        lines.append("\t".join(str(x) for x in row))
    return "\n".join(lines) if resp.get("rows") else "(データなし)"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--top", type=int, default=10, help="動画別ランキングの件数")
    ap.add_argument("--video-id", default=None, help="指定すると動画単体レポート")
    ap.add_argument("--start", default="2020-01-01", help="累計の起点日")
    args = ap.parse_args()

    creds = load_creds(args.token)
    yt = build("youtube", "v3", credentials=creds)
    ya = build("youtubeAnalytics", "v2", credentials=creds)

    today = datetime.date.today()
    start = (today - datetime.timedelta(days=args.days)).isoformat()
    end = today.isoformat()

    def q(**kw):
        try:
            return ya.reports().query(ids="channel==MINE", **kw).execute()
        except Exception as e:
            return {"error": str(e)}

    ch = yt.channels().list(part="snippet,statistics", mine=True).execute()["items"][0]
    sn, st = ch["snippet"], ch["statistics"]
    print("=== CHANNEL ===")
    print(f"{sn['title']} ({sn.get('customUrl', '')})")
    print(f"登録者: {st.get('subscriberCount', '?')} / 累計再生: {st.get('viewCount', '?')}"
          f" / 動画数: {st.get('videoCount', '?')}")

    if args.video_id:
        v = yt.videos().list(part="snippet,statistics,contentDetails",
                             id=args.video_id).execute()["items"][0]
        print(f"\n=== VIDEO: {v['snippet']['title']} ===")
        vs = v["statistics"]
        print(f"公開日: {v['snippet']['publishedAt']} / 尺: {v['contentDetails']['duration']}")
        print(f"再生: {vs.get('viewCount', '?')} / 高評価: {vs.get('likeCount', '?')}"
              f" / コメント: {vs.get('commentCount', '?')}")
        flt = f"video=={args.video_id}"
        print(f"\n--- 直近{args.days}日 ---")
        print(pretty(q(startDate=start, endDate=end, metrics=METRICS, filters=flt)))
        print("\n--- 累計 ---")
        print(pretty(q(startDate=args.start, endDate=end, metrics=METRICS, filters=flt)))
        print("\n--- トラフィックソース（累計）---")
        print(pretty(q(startDate=args.start, endDate=end, metrics="views",
                       dimensions="insightTrafficSourceType", sort="-views", filters=flt)))
        return

    print(f"\n=== 直近{args.days}日（チャンネル全体）===")
    print(pretty(q(startDate=start, endDate=end, metrics=METRICS)))

    print("\n=== 累計（チャンネル全体）===")
    print(pretty(q(startDate=args.start, endDate=end, metrics=METRICS)))

    print(f"\n=== 動画別 直近{args.days}日 TOP{args.top} ===")
    r = q(startDate=start, endDate=end, metrics=METRICS,
          dimensions="video", sort="-views", maxResults=args.top)
    if "error" not in r and r.get("rows"):
        ids = [row[0] for row in r["rows"]]
        titles = {}
        vr = yt.videos().list(part="snippet", id=",".join(ids)).execute()
        for it in vr["items"]:
            titles[it["id"]] = it["snippet"]["title"]
        headers = [h["name"] for h in r["columnHeaders"]]
        print("\t".join(headers) + "\ttitle")
        for row in r["rows"]:
            print("\t".join(str(x) for x in row) + "\t" + titles.get(row[0], "?")[:50])
    else:
        print(pretty(r))

    print(f"\n=== トラフィックソース 直近{args.days}日 ===")
    print(pretty(q(startDate=start, endDate=end, metrics="views",
                   dimensions="insightTrafficSourceType", sort="-views")))


if __name__ == "__main__":
    main()
