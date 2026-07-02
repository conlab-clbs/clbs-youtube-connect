#!/bin/bash
# YouTube接続用のPython環境を ~/youtube-connect/ に作る
set -e

BASE="${1:-$HOME/youtube-connect}"
mkdir -p "$BASE/tokens"

if [ ! -d "$BASE/.venv" ]; then
  python3 -m venv "$BASE/.venv"
fi

"$BASE/.venv/bin/pip" install --quiet --upgrade pip
"$BASE/.venv/bin/pip" install --quiet google-api-python-client google-auth-oauthlib pyyaml

echo "OK: Python環境を作成しました -> $BASE/.venv"
echo "次: client_secret.json を $BASE/ に置き、yt_authorize.py で認証してください"
