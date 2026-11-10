#!/usr/bin/env sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$project_dir"
mkdir -p out dist
javac --release 17 -encoding UTF-8 -d out src/demo/*.java
jar --create --file dist/mock-google-mcp.jar --main-class demo.McpServer -C out .
