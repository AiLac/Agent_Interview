package demo;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/** 教学客户端：真正使用 MCP 管道通信；工具选择由代码指定，没有调用大模型。 */
public final class McpClientDemo {
    private static final String PROTOCOL_VERSION = "2025-06-18";

    public static void main(String[] args) {
        try {
            if (args.length > 2) throw new IllegalArgumentException("用法：McpClientDemo [query] [limit]");
            String query = args.length > 0 ? args[0] : "Java 虚拟线程";
            int limit = args.length > 1 ? Integer.parseInt(args[1]) : 3;
            run(query, limit);
        } catch (Exception e) {
            System.err.println("[客户端失败] " + e.getMessage());
            System.exit(1);
        }
    }

    private static void run(String query, int limit) throws Exception {
        System.out.println("教学演示：真实 MCP 进程通信 + 模拟搜索数据；不调用大模型。");
        try (RpcSession session = new RpcSession()) {
            // 1. 客户端声明自己支持的版本和能力，检查服务端选择的版本。
            Map<String, Object> initialized = session.request("initialize", Json.object(
                "protocolVersion", PROTOCOL_VERSION,
                "capabilities", Json.object(),
                "clientInfo", Json.object("name", "java-mcp-teaching-client", "version", "1.0.0")));
            if (!PROTOCOL_VERSION.equals(initialized.get("protocolVersion"))) {
                throw new IOException("客户端不支持服务端选择的协议版本：" + initialized.get("protocolVersion"));
            }
            Map<String, Object> capabilities = object(initialized.get("capabilities"));
            if (!(capabilities.get("tools") instanceof Map<?, ?>)) {
                throw new IOException("服务端没有声明 tools 能力");
            }

            // 2. 通知没有 id，也没有响应；这里绝不能再调用 readLine() 等回复。
            session.notify("notifications/initialized");

            // 3. 从实际服务端发现工具。这个例子只需要一页静态工具列表。
            Map<String, Object> listing = session.request("tools/list", Json.object());
            if (listing.get("nextCursor") != null) throw new IOException("教学客户端未实现工具列表分页");
            if (!(listing.get("tools") instanceof List<?> tools)) throw new IOException("tools 必须是数组");
            Map<String, Object> selected = null;
            for (Object item : tools) {
                Map<String, Object> tool = object(item);
                System.out.println("[发现工具] " + tool.get("name"));
                System.out.println("  用途：" + tool.get("description"));
                System.out.println("  参数：" + Json.stringify(tool.get("inputSchema")));
                if ("google_search".equals(tool.get("name"))) selected = tool;
            }
            if (selected == null) throw new IOException("服务端实际返回的工具列表中没有 google_search");

            // 4. 本例固定选择搜索工具，但调用名取自 tools/list 的真实返回值。
            Map<String, Object> result = session.request("tools/call", Json.object(
                "name", selected.get("name"),
                "arguments", Json.object("query", query, "limit", limit)));
            if (!(result.get("content") instanceof List<?>)) throw new IOException("工具结果缺少 content 数组");
            if (result.containsKey("isError") && !(result.get("isError") instanceof Boolean)) {
                throw new IOException("isError 必须是布尔值");
            }
            if (Boolean.TRUE.equals(result.get("isError"))) {
                throw new IOException("工具执行失败（isError=true）：" + Json.stringify(result.get("content")));
            }
            System.out.println("[搜索成功，数据为模拟] " + Json.stringify(
                result.containsKey("structuredContent") ? result.get("structuredContent") : result.get("content")));
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(Object value) throws IOException {
        if (!(value instanceof Map<?, ?>)) throw new IOException("期望 JSON object，实际为：" + value);
        return (Map<String, Object>) value;
    }

    /** 一个会话对应一个服务端子进程；这里只允许依次发送请求。 */
    private static final class RpcSession implements AutoCloseable {
        private final Process process;
        private final BufferedWriter toServer;
        private final BufferedReader fromServer;
        private final ExecutorService reader = Executors.newSingleThreadExecutor(task -> {
            Thread thread = new Thread(task, "mcp-response-reader");
            thread.setDaemon(true);
            return thread;
        });
        private long nextId = 1;

        RpcSession() throws IOException {
            String executable = System.getProperty("os.name").startsWith("Windows") ? "java.exe" : "java";
            String java = Path.of(System.getProperty("java.home"), "bin", executable).toString();
            process = new ProcessBuilder(java, "-cp", System.getProperty("java.class.path"), "demo.McpServer")
                .redirectError(ProcessBuilder.Redirect.INHERIT).start(); // 不合并 stderr 和 stdout。
            toServer = new BufferedWriter(new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8));
            fromServer = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
        }

        Map<String, Object> request(String method, Map<String, Object> params) throws Exception {
            long id = nextId++;
            send(Json.object("jsonrpc", "2.0", "id", id, "method", method, "params", params));
            Future<String> pending = reader.submit(fromServer::readLine);
            String line;
            try {
                line = pending.get(5, TimeUnit.SECONDS);
            } catch (TimeoutException e) {
                pending.cancel(true);
                throw new IOException("等待 " + method + " 超过5秒，结束此教学会话", e);
            }
            if (line == null) throw new IOException("服务端 stdout 提前结束（EOF）");
            System.out.println("S→C " + line);
            Map<String, Object> response = object(Json.parse(line));
            if (response.containsKey("method")) {
                throw new IOException("教学客户端不处理服务端主动请求或通知：" + response.get("method"));
            }
            if (!"2.0".equals(response.get("jsonrpc"))) throw new IOException("响应 jsonrpc 不是 2.0");
            Object actualId = response.get("id");
            if (!(actualId instanceof Number number)
                    || new BigDecimal(number.toString()).compareTo(BigDecimal.valueOf(id)) != 0) {
                throw new IOException("响应 id 不匹配，期望 " + id + "，实际 " + actualId);
            }
            boolean hasResult = response.containsKey("result");
            boolean hasError = response.containsKey("error");
            if (hasResult == hasError) throw new IOException("响应必须恰好包含 result 或 error 中的一个");
            if (hasError) throw new IOException("JSON-RPC 协议错误：" + Json.stringify(response.get("error")));
            return object(response.get("result"));
        }

        void notify(String method) throws IOException {
            send(Json.object("jsonrpc", "2.0", "method", method));
        }

        private void send(Map<String, Object> message) throws IOException {
            String line = Json.stringify(message);
            toServer.write(line);
            toServer.write('\n');
            toServer.flush();
            System.out.println("C→S " + line); // 这是客户端控制台，不是服务端协议 stdout。
        }

        @Override
        public void close() throws Exception {
            // MCP 没有 shutdown RPC：关闭服务端 stdin，用 EOF 告知子进程退出。
            try {
                toServer.close();
            } finally {
                if (!process.waitFor(2, TimeUnit.SECONDS)) {
                    process.destroy();
                    if (!process.waitFor(1, TimeUnit.SECONDS)) {
                        process.destroyForcibly();
                        process.waitFor(1, TimeUnit.SECONDS);
                    }
                }
                reader.shutdownNow();
                fromServer.close();
            }
        }
    }
}
