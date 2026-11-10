"""Interop check using the installed official MCP Python SDK.

Optional: python -m pip install mcp==1.29.0
Run: python verify_sdk.py
Uses the bundled dist/mock-google-mcp.jar, or compiled out/ as a fallback.
"""

import asyncio
import importlib.metadata
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "verification"
CLASSPATH = ROOT / "dist" / "mock-google-mcp.jar"
if not CLASSPATH.exists():
    CLASSPATH = ROOT / "out"


async def verify():
    checks = []

    def check(name, condition, detail=None):
        entry = {"name": name, "status": "PASS" if condition else "FAIL"}
        if detail is not None:
            entry["detail"] = detail
        checks.append(entry)
        print(entry["status"], name)

    OUT.mkdir(exist_ok=True)
    server = StdioServerParameters(command="java", args=["-cp", str(CLASSPATH), "demo.McpServer"], cwd=str(ROOT))
    try:
        with (OUT / "sdk-server.stderr.txt").open("w", encoding="utf-8") as stderr:
            async with stdio_client(server, errlog=stderr) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=3)) as session:
                    initialized = await session.initialize()
                    check("official SDK negotiates 2025-06-18", initialized.protocolVersion == "2025-06-18",
                          {"selected_protocol_version": initialized.protocolVersion})
                    catalog = await session.list_tools()
                    check("official SDK discovers google_search", [tool.name for tool in catalog.tools] == ["google_search"])
                    found = next(tool for tool in catalog.tools if tool.name == "google_search")
                    result = await session.call_tool(found.name, {"query": "Java 虚拟线程", "limit": 2})
                    data = result.structuredContent
                    check("official SDK calls discovered tool with Chinese query",
                          result.isError is False and data["mock"] is True and data["totalMatches"] == 3
                          and len(data["results"]) == 2 and data["query"] == "Java 虚拟线程")
                    check("official SDK reads matching text and structured content",
                          json.loads(result.content[0].text) == data)
                    empty = await session.call_tool(found.name, {"query": "unmatched_case_73d98a"})
                    check("official SDK accepts successful empty result", empty.isError is False
                          and empty.structuredContent["totalMatches"] == 0
                          and empty.structuredContent["results"] == [])
                    failure = await session.call_tool(found.name, {"query": "__timeout__"})
                    check("official SDK receives tool execution error", failure.isError is True
                          and "MOCK_UPSTREAM_TIMEOUT" in failure.content[0].text)
        check("official SDK context managers close the stdio session", True)
    except Exception as error:
        check("official SDK run completed", False, repr(error))
    report = {
        "kind": "official Python MCP SDK interoperability smoke test",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sdk_package": "mcp", "sdk_version": importlib.metadata.version("mcp"),
        "python_version": sys.version.split()[0],
        "command": ["java", "-cp", str(CLASSPATH.relative_to(ROOT)), "demo.McpServer"],
        "total": len(checks), "passed": sum(c["status"] == "PASS" for c in checks),
        "failed": sum(c["status"] == "FAIL" for c in checks), "checks": checks,
        "scope": "Official SDK client to the Java teaching server over real stdio; not Codex end-to-end validation.",
    }
    (OUT / "sdk-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("sdk_version", "total", "passed", "failed")}))
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(verify()))
