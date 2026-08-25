#!/bin/zsh
set -eu

PROJECT_DIR=${0:A:h}
cd "$PROJECT_DIR"

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run dev &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

for attempt in {1..60}; do
  if curl --silent --fail --output /dev/null http://localhost:3000/; then
    open http://localhost:3000/
    echo "Q-Forge 已在本机启动：http://localhost:3000/"
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "本地网站启动失败，请保留此窗口中的错误信息。"
    exit 1
  fi
  sleep 1
done

wait "$SERVER_PID"

