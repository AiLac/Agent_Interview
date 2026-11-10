package demo;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static demo.Json.object;

/** 手写 MCP 2025-06-18 的 stdio + tools 教学子集。搜索数据是模拟的。 */
public final class McpServer {
    public static final String PROTOCOL_VERSION = "2025-06-18";
    private enum State { NEW, INITIALIZING, READY }
    private State state = State.NEW;

    // 这是工具的说明书，tools/list 会把它交给客户端。它不会自动执行参数校验。
    private static final Map<String, Object> SEARCH_TOOL = object(
        "name", "google_search",
        "description", "教学用模拟 Google 搜索：只查固定本地数据，不访问网络。"
            + " query=__timeout__ 可演示上游超时。",
        "inputSchema", object(
            "type", "object",
            "properties", object(
                "query", object("type", "string", "minLength", 1, "pattern", "\\S",
                    "description", "搜索词，例如 Java 虚拟线程 或 MCP"),
                "limit", object("type", "integer", "minimum", 1, "maximum", 5,
                    "default", 3, "description", "最多返回几条结果，默认3，范围1至5")
            ),
            "required", List.of("query"),
            "additionalProperties", false
        )
    );

    public static void main(String[] args) throws Exception {
        new McpServer().run();
    }

    private void run() throws Exception {
        // stdout 是协议管道。普通日志必须写 stderr，否则客户端会把日志当 JSON 解析。
        System.err.println("[server] 模拟搜索 MCP 已启动；等待 stdin 中的 JSON-RPC 消息。");
        var input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        var output = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8));
        String line;
        while ((line = input.readLine()) != null) {
            Map<String, Object> response = handle(line);
            if (response != null) {
                output.write(Json.stringify(response));
                output.write('\n');
                output.flush(); // 没有 flush，对端可能一直等不到消息。
            }
        }
        System.err.println("[server] stdin 已关闭，服务端退出。");
    }

    private Map<String, Object> handle(String line) {
        Object parsed;
        try {
            parsed = Json.parse(line);
        } catch (IllegalArgumentException e) {
            return error(null, -32700, "Parse error: 非法 JSON");
        }
        if (!(parsed instanceof Map<?, ?> request)) {
            return error(null, -32600, "Invalid Request: 必须是一条对象消息，不支持批量数组");
        }
        Object id = request.get("id");
        boolean hasId = request.containsKey("id");
        if (!"2.0".equals(request.get("jsonrpc"))
                || !(request.get("method") instanceof String)
                || (hasId && !validId(id))) {
            return error(validId(id) ? id : null, -32600, "Invalid Request: 检查 jsonrpc、method、id");
        }

        String method = (String) request.get("method");
        // 没有 id 的合法消息是通知：不得回复，也不得当普通请求执行。
        if (!hasId) {
            if ("notifications/initialized".equals(method) && state == State.INITIALIZING) {
                state = State.READY;
                System.err.println("[server] 收到 initialized 通知，会话可接受工具请求。");
            }
            return null;
        }

        try {
            Object rawParams = request.containsKey("params") ? request.get("params") : Map.of();
            Map<?, ?> params = requireObject(rawParams, "params 必须是对象");
            Object result = dispatch(method, params);
            return object("jsonrpc", "2.0", "id", id, "result", result);
        } catch (RpcFailure e) {
            return error(id, e.code, e.getMessage());
        } catch (RuntimeException e) {
            System.err.println("[server] 未预期内部异常: " + e.getClass().getSimpleName());
            return error(id, -32603, "Internal error");
        }
    }

    // 第一层分发：MCP 标准方法，例如 tools/list、tools/call。
    private Object dispatch(String method, Map<?, ?> params) {
        return switch (method) {
            case "initialize" -> initialize(params);
            case "ping" -> object();
            case "tools/list" -> {
                requireReady();
                if (params.containsKey("cursor")) {
                    throw new RpcFailure(-32602, "本例工具列表只有一页，不接受 cursor");
                }
                yield object("tools", List.of(SEARCH_TOOL));
            }
            case "tools/call" -> {
                requireReady();
                yield callTool(params);
            }
            default -> throw new RpcFailure(-32601, "Method not found: " + method);
        };
    }

    private Object initialize(Map<?, ?> params) {
        if (state != State.NEW) {
            throw new RpcFailure(-32600, "本会话已经初始化；请建立新的连接");
        }
        requireString(params.get("protocolVersion"), "protocolVersion");
        requireObject(params.get("capabilities"), "capabilities 必须是对象");
        Map<?, ?> info = requireObject(params.get("clientInfo"), "clientInfo 必须是对象");
        requireString(info.get("name"), "clientInfo.name");
        requireString(info.get("version"), "clientInfo.version");
        state = State.INITIALIZING;
        // 只支持这一个版本。即便对端请求其他版本，也先返回本端支持的版本供对端判断。
        return object(
            "protocolVersion", PROTOCOL_VERSION,
            "capabilities", object("tools", object()),
            "serverInfo", object("name", "mock-google-search-java", "version", "1.0.0"),
            "instructions", "全部结果都是教学模拟数据；本服务不会请求 Google 或其他外部服务。"
        );
    }

    // 第二层分发：从 tools/call.params.name 找到业务函数。
    private Object callTool(Map<?, ?> params) {
        String name = requireString(params.get("name"), "name");
        if (!"google_search".equals(name)) {
            throw new RpcFailure(-32602, "Unknown tool: " + name);
        }
        Object rawArguments = params.containsKey("arguments") ? params.get("arguments") : Map.of();
        Map<?, ?> arguments = requireObject(rawArguments, "arguments 必须是对象");
        if (!Set.of("query", "limit").containsAll(arguments.keySet())) {
            throw new RpcFailure(-32602, "google_search 只接受 query 和 limit");
        }
        String query = requireString(arguments.get("query"), "query");
        Object rawLimit = arguments.containsKey("limit") ? arguments.get("limit") : 3;
        int limit = requireLimit(rawLimit);

        try {
            Map<String, Object> data = MockSearch.search(query, limit);
            // 同时给文本和结构化内容：旧客户端可以读文本，程序可以直接读结构化数据。
            return object(
                "content", List.of(object("type", "text", "text", Json.stringify(data))),
                "structuredContent", data,
                "isError", false
            );
        } catch (MockSearch.SearchFailure e) {
            // 请求已路由到工具，失败发生在业务执行中：不是 JSON-RPC error。
            return object(
                "content", List.of(object("type", "text", "text", e.code() + ": " + e.getMessage())),
                "isError", true
            );
        }
    }

    private void requireReady() {
        if (state != State.READY) {
            // -32002 是本例自定义的服务端错误码，不是 MCP 标准定义的固定含义。
            throw new RpcFailure(-32002, "Session not ready: 先 initialize，再发送 notifications/initialized");
        }
    }

    private static String requireString(Object value, String field) {
        if (!(value instanceof String text) || text.isBlank()) {
            throw new RpcFailure(-32602, field + " 必须是非空白字符串");
        }
        return text;
    }

    private static Map<?, ?> requireObject(Object value, String message) {
        if (!(value instanceof Map<?, ?> map)) throw new RpcFailure(-32602, message);
        return map;
    }

    private static int requireLimit(Object value) {
        if (value instanceof Number number) {
            try {
                int limit = new BigDecimal(number.toString()).intValueExact();
                if (limit >= 1 && limit <= 5) return limit;
            } catch (ArithmeticException | NumberFormatException ignored) { }
        }
        throw new RpcFailure(-32602, "limit 必须是1至5的整数");
    }

    private static boolean validId(Object id) {
        if (id instanceof String) return true;
        if (!(id instanceof Number number)) return false;
        try {
            new BigDecimal(number.toString()).toBigIntegerExact();
            return true;
        } catch (ArithmeticException | NumberFormatException e) { return false; }
    }

    private static Map<String, Object> error(Object id, int code, String message) {
        return object("jsonrpc", "2.0", "id", id,
            "error", object("code", code, "message", message));
    }

    private static final class RpcFailure extends RuntimeException {
        final int code;
        RpcFailure(int code, String message) { super(message); this.code = code; }
    }
}
