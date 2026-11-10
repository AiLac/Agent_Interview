"""Black-box checks for the teaching MCP server; Python standard library only.

Run: python verify.py
Uses the bundled dist/mock-google-mcp.jar, or compiled out/ as a fallback.
This checks the documented teaching subset, not full MCP conformance.
"""

import json
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "verification"
TIMEOUT = 3.0
PROTOCOL = "2025-06-18"
CLASSPATH = ROOT / "dist" / "mock-google-mcp.jar"
if not CLASSPATH.exists():
    CLASSPATH = ROOT / "out"
OUT.mkdir(exist_ok=True)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class WireLog:
    def __init__(self):
        self.file = (OUT / "wire-transcript.jsonl").open("w", encoding="utf-8")
        self.lock = threading.Lock()
        self.sequence = 0

    def record(self, session, direction, message, valid_json=True):
        with self.lock:
            self.sequence += 1
            self.file.write(json.dumps({
                "sequence": self.sequence, "session": session,
                "direction": direction, "message": message,
                "valid_json": valid_json,
            }, ensure_ascii=False) + "\n")
            self.file.flush()


class Server:
    def __init__(self, label, wire):
        self.label = label
        self.wire = wire
        self.next_id = 1
        self.responses = queue.Queue()
        self.stderr = []
        self.stdout_errors = []
        self.process = subprocess.Popen(
            ["java", "-cp", str(CLASSPATH), "demo.McpServer"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )
        self.out_reader = threading.Thread(target=self._read_stdout, daemon=True)
        self.err_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self.out_reader.start()
        self.err_reader.start()

    def _read_stdout(self):
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                    require(isinstance(message, dict), "stdout message must be an object")
                    require(message.get("jsonrpc") == "2.0", "missing jsonrpc on stdout")
                    self.wire.record(self.label, "server->client", message)
                    self.responses.put(message)
                except Exception as error:
                    self.stdout_errors.append(str(error))
                    self.wire.record(self.label, "server->client", line.rstrip("\n"), False)
                    self.responses.put(error)
        finally:
            self.responses.put(EOFError("server stdout closed"))

    def _read_stderr(self):
        for line in self.process.stderr:
            self.stderr.append(line)

    def send(self, message):
        self.wire.record(self.label, "client->server", message)
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def send_raw(self, text):
        self.wire.record(self.label, "client->server", text, False)
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()

    def receive(self, request_id):
        try:
            response = self.responses.get(timeout=TIMEOUT)
        except queue.Empty as error:
            raise TimeoutError("no response within 3 seconds") from error
        if isinstance(response, Exception):
            raise response
        require(response.get("id") == request_id, "response id does not match request")
        require(("result" in response) != ("error" in response), "expected result XOR error")
        return response

    def request(self, method, params=None, request_id=None):
        if request_id is None:
            request_id = self.next_id
            self.next_id += 1
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        return self.receive(request_id)

    def initialize(self, version=PROTOCOL, finish=True):
        response = self.request("initialize", {
            "protocolVersion": version, "capabilities": {},
            "clientInfo": {"name": "blackbox-teaching-client", "version": "1.0.0"},
        })
        require(response.get("result", {}).get("protocolVersion") == PROTOCOL,
                "server must select its supported protocol version")
        require("tools" in response["result"]["capabilities"], "tools capability not declared")
        require(bool(response["result"].get("serverInfo", {}).get("name")), "missing serverInfo")
        if finish:
            self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            self.expect_silence()
        return response

    def expect_silence(self):
        try:
            message = self.responses.get(timeout=0.15)
        except queue.Empty:
            return
        raise AssertionError("notification produced output: " + repr(message))

    def call(self, arguments, name="google_search", request_id=None):
        return self.request("tools/call", {"name": name, "arguments": arguments}, request_id)

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            code = self.process.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=TIMEOUT)
            raise AssertionError("server did not exit after stdin EOF")
        self.out_reader.join(timeout=TIMEOUT)
        self.err_reader.join(timeout=TIMEOUT)
        require(code == 0, "server exit code must be zero")
        require(not self.stdout_errors, "stdout contained invalid protocol lines")
        require(bool("".join(self.stderr).strip()), "expected logs on stderr")


def protocol_error(response, code):
    require(response.get("error", {}).get("code") == code, "unexpected protocol error: " + repr(response))
    require("result" not in response, "protocol errors must not include result")


def data_result(response):
    require("error" not in response, "unexpected protocol error")
    result = response["result"]
    require(result.get("isError") is False, "expected successful tool result")
    data = result["structuredContent"]
    require(data.get("mock") is True, "mock data must be labelled")
    require(json.loads(result["content"][0]["text"]) == data,
            "text and structuredContent must represent the same result")
    return data


def main():
    wire = WireLog()
    checks = []
    sessions = []

    def check(name, action):
        started = time.monotonic()
        try:
            action()
            entry = {"name": name, "status": "PASS"}
        except Exception as error:
            entry = {"name": name, "status": "FAIL", "detail": str(error)}
        entry["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        checks.append(entry)
        print(entry["status"], name, entry.get("detail", ""))

    def new_server(label):
        server = Server(label, wire)
        sessions.append(server)
        return server

    server = new_server("main")
    check("tool listing before initialization is rejected",
          lambda: protocol_error(server.request("tools/list", {}), -32002))
    check("initialize returns selected version and tools capability",
          lambda: server.initialize(finish=False))
    check("tool calls before initialized notification are rejected",
          lambda: protocol_error(server.call({"query": "MCP"}), -32002))

    def initialized():
        server.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        server.expect_silence()
    check("initialized is a notification with no response", initialized)

    def tool_list():
        response = server.request("tools/list", {})
        tools = response["result"]["tools"]
        require(len(tools) == 1 and tools[0]["name"] == "google_search", "unexpected discovered tool")
        schema = tools[0]["inputSchema"]
        require(schema["type"] == "object", "inputSchema must describe an object")
        require("query" in schema["required"], "query must be required")
        require(schema["properties"]["query"]["type"] == "string", "query must be string")
        limit = schema["properties"]["limit"]
        require((limit["type"], limit["minimum"], limit["maximum"], limit["default"])
                == ("integer", 1, 5, 3), "limit contract differs")
        require(schema["additionalProperties"] is False, "unexpected additional fields policy")
        require("nextCursor" not in response["result"], "one-page catalog must not advertise next page")
    check("tools/list exposes callable name and parameter schema", tool_list)

    def search_limit():
        data = data_result(server.call({"query": "Java 虚拟线程", "limit": 2}))
        require(data["query"] == "Java 虚拟线程", "query echo differs")
        require(data["totalMatches"] == 3 and len(data["results"]) == 2, "limit/count behavior differs")
    check("mock search returns two results from three matches", search_limit)

    def default_limit():
        data = data_result(server.call({"query": "Java 虚拟线程"}))
        require(len(data["results"]) == 3 and data["totalMatches"] == 3, "omitted limit should default to 3")
    check("omitted limit uses default 3", default_limit)

    def empty_result():
        data = data_result(server.call({"query": "unmatched_case_73d98a"}))
        require(data["results"] == [] and data["totalMatches"] == 0, "zero matches should be success with empty list")
    check("zero matches is a successful empty result", empty_result)

    invalid_arguments = [
        ("missing query", {}), ("empty query", {"query": ""}),
        ("whitespace query", {"query": " \t\n"}), ("numeric query", {"query": 42}),
        ("null query", {"query": None}), ("limit below range", {"query": "MCP", "limit": 0}),
        ("limit above range", {"query": "MCP", "limit": 6}),
        ("boolean limit", {"query": "MCP", "limit": True}),
        ("fractional limit", {"query": "MCP", "limit": 2.5}),
        ("string limit", {"query": "MCP", "limit": "2"}),
        ("null limit", {"query": "MCP", "limit": None}),
        ("unexpected argument", {"query": "MCP", "extra": 1}),
        ("arguments array", []),
    ]
    for name, arguments in invalid_arguments:
        check("invalid arguments: " + name,
              lambda arguments=arguments: protocol_error(server.call(arguments), -32602))

    check("unknown MCP method returns -32601",
          lambda: protocol_error(server.request("not/a/method", {}), -32601))
    check("unknown tool returns -32602",
          lambda: protocol_error(server.call({"query": "MCP"}, name="absent_tool"), -32602))

    def timeout_result():
        response = server.call({"query": "__timeout__"})
        require("error" not in response and response["result"]["isError"] is True,
                "business failure must be a tool execution error")
        require("MOCK_UPSTREAM_TIMEOUT" in response["result"]["content"][0]["text"],
                "missing mock failure detail")
    check("mock upstream failure returns result.isError", timeout_result)

    def malformed_json():
        server.send_raw('{"jsonrpc":')
        protocol_error(server.receive(None), -32700)
    check("malformed JSON returns -32700", malformed_json)

    def malformed_envelope():
        server.send({"jsonrpc": "1.0", "id": "bad-envelope", "method": "tools/list"})
        protocol_error(server.receive("bad-envelope"), -32600)
    check("invalid JSON-RPC envelope returns -32600", malformed_envelope)

    def string_id():
        response = server.call({"query": "MCP"}, request_id="查询-req-001")
        require(response["id"] == "查询-req-001", "string id must be preserved")
        data_result(response)
    check("UTF-8 string request id is preserved", string_id)

    def escaped_query():
        query = '中文 "引号" \\path\n第二行'
        data = data_result(server.call({"query": query}))
        require(data["query"] == query, "UTF-8 or JSON escapes were changed")
    check("Chinese quotes backslash and newline round-trip", escaped_query)

    check("main session EOF exits and logs stay on stderr", server.close)
    mismatch = new_server("version-negotiation")
    check("unsupported requested version selects server supported version",
          lambda: mismatch.initialize("2025-11-25"))
    check("negotiated session can discover tools",
          lambda: require(mismatch.request("tools/list", {})["result"]["tools"][0]["name"]
                          == "google_search", "catalog unavailable after version negotiation"))
    check("version session EOF exits cleanly", mismatch.close)

    for instance in sessions:
        if instance.process.poll() is None:
            instance.process.kill()
            instance.process.wait(timeout=TIMEOUT)
    wire.file.close()
    report = {
        "kind": "black-box teaching-subset verification",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_version": PROTOCOL, "request_timeout_seconds": TIMEOUT,
        "command": ["java", "-cp", str(CLASSPATH.relative_to(ROOT)), "demo.McpServer"],
        "python_version": sys.version.split()[0],
        "total": len(checks), "passed": sum(c["status"] == "PASS" for c in checks),
        "failed": sum(c["status"] == "FAIL" for c in checks), "checks": checks,
        "scope": "Real child-process stdin/stdout; mock search only; not full MCP conformance.",
    }
    (OUT / "verification-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "failed")}, ensure_ascii=False))
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
