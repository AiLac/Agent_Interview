package demo;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** 普通Java业务函数：只读内存里的教学语料，不访问Google或任何网络。 */
public final class MockSearch {
    private record Document(String title, String url, String snippet, String tags) {}

    private static final List<Document> DOCUMENTS = List.of(
        new Document("[模拟] Java 虚拟线程入门",
            "https://example.invalid/mock/java-virtual-threads",
            "[模拟摘要] 一篇介绍Java虚拟线程基本概念的教学文档。",
            "java jdk loom virtual threads 虚拟线程 入门"),
        new Document("[模拟] Spring Boot 使用 Java 虚拟线程",
            "https://example.invalid/mock/spring-boot-virtual-threads",
            "[模拟摘要] 一篇介绍Spring Boot中虚拟线程使用方法的教学文档。",
            "java spring boot virtual threads 虚拟线程 配置"),
        new Document("[模拟] Java 虚拟线程使用注意事项",
            "https://example.invalid/mock/java-thread-notes",
            "[模拟摘要] 一篇讨论并发任务与虚拟线程使用边界的教学文档。",
            "java jdk virtual threads 虚拟线程 并发 注意事项"),
        new Document("[模拟] MCP 工具发现入门",
            "https://example.invalid/mock/mcp-discovery",
            "[模拟摘要] 一篇介绍tools/list与工具参数描述的教学文档。",
            "mcp tools discovery tools/list 工具 发现 入门"),
        new Document("[模拟] MCP stdio 通信",
            "https://example.invalid/mock/mcp-stdio",
            "[模拟摘要] 一篇介绍JSON-RPC和标准输入输出通信的教学文档。",
            "mcp stdio json rpc json-rpc 工具 通信 协议"),
        new Document("[模拟] Redis 缓存基础",
            "https://example.invalid/mock/redis-cache",
            "[模拟摘要] 一篇用于演示搜索结果筛选的缓存教学文档。",
            "java redis cache 缓存 基础")
    );

    private MockSearch() {}

    /**
     * 这是本例自定义的业务接口，不是MCP规定的接口。
     * 匹配规则只是“每个查询词都出现在文档文本中”，顺序沿用固定语料顺序。
     */
    public static Map<String, Object> search(String query, int limit) {
        if (query == null || query.isBlank()) throw new IllegalArgumentException("query不能为空");
        if (limit < 1 || limit > 5) throw new IllegalArgumentException("limit必须在1至5之间");
        if (query.equals("__timeout__")) {
            // 立即注入错误；没有真实网络请求，也没有真的等待超时。
            throw new SearchFailure("MOCK_UPSTREAM_TIMEOUT", "模拟搜索上游超时；本次没有访问Google。");
        }

        String[] terms = query.trim().toLowerCase(Locale.ROOT).split("\\s+");
        List<Map<String, Object>> matches = new ArrayList<>();
        for (Document document : DOCUMENTS) {
            String searchable = (document.title() + " " + document.snippet() + " "
                    + document.tags()).toLowerCase(Locale.ROOT);
            boolean matched = true;
            for (String term : terms) {
                if (!searchable.contains(term)) {
                    matched = false;
                    break;
                }
            }
            if (matched) {
                matches.add(Json.object("title", document.title(), "url", document.url(),
                        "snippet", document.snippet()));
            }
        }

        return Json.object("query", query, "mock", true, "totalMatches", matches.size(),
                "results", new ArrayList<>(matches.subList(0, Math.min(limit, matches.size()))));
    }

    /** 区别于参数校验错误：MCP服务端会把这个业务错误包装成isError=true。 */
    public static final class SearchFailure extends RuntimeException {
        private final String code;

        public SearchFailure(String code, String message) {
            super(message);
            this.code = code;
        }

        public String code() {
            return code;
        }
    }
}
