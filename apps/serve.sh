#!/usr/bin/env bash
# 启动本地 HTTP 服务用于调试 apps/ 下的网页工具
# 用法：./apps/serve.sh [port]

PORT="${1:-8000}"

# 切到项目根目录（本脚本所在目录的上级）
cd "$(dirname "$0")/.."

echo "🚀 启动本地服务: http://localhost:$PORT/"
echo "   打开工具："
for app in apps/*/; do
  name=$(basename "$app")
  [ "$name" = "serve.sh" ] && continue
  echo "   → http://localhost:$PORT/$app"
done
echo ""
echo "按 Ctrl+C 停止"
echo ""

python3 -m http.server "$PORT"
