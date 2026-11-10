package demo;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 教学配套 JSON 编解码器，让本例只需 JDK 即可运行。
 * 它不是 MCP 的核心；阅读 MCP 时可以先跳过本文件。
 * 正式项目应使用成熟 JSON 库和 MCP SDK。
 */
public final class Json {
    private static final int MAX_DEPTH = 64;

    private Json() {}

    public static Object parse(String text) {
        if (text == null) throw new IllegalArgumentException("JSON must not be null");
        Parser parser = new Parser(text);
        Object result = parser.value(0);
        parser.whitespace();
        if (parser.index != text.length()) throw parser.error("Unexpected trailing input");
        return result;
    }

    /** 紧凑输出；字符串内的换行被转义，不会产生额外物理行。 */
    public static String stringify(Object value) {
        StringBuilder output = new StringBuilder();
        write(value, output, 0);
        return output.toString();
    }

    /** 例如 object("jsonrpc", "2.0", "id", 1L)，保留字段顺序且允许 null 值。 */
    public static Map<String, Object> object(Object... keyValues) {
        if (keyValues == null || keyValues.length % 2 != 0) {
            throw new IllegalArgumentException("Keys and values must occur in pairs");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            if (!(keyValues[i] instanceof String key)) {
                throw new IllegalArgumentException("Object keys must be strings");
            }
            if (result.containsKey(key)) throw new IllegalArgumentException("Duplicate key: " + key);
            result.put(key, keyValues[i + 1]);
        }
        return result;
    }

    private static void write(Object value, StringBuilder output, int depth) {
        if (depth > MAX_DEPTH) throw new IllegalArgumentException("JSON nesting is too deep");
        if (value == null) {
            output.append("null");
        } else if (value instanceof String text) {
            quote(text, output);
        } else if (value instanceof Boolean) {
            output.append(value);
        } else if (value instanceof Number number) {
            // BigDecimal 同时排除 Double.NaN / Infinity 等非 JSON 数值。
            try {
                new BigDecimal(number.toString());
            } catch (NumberFormatException exception) {
                throw new IllegalArgumentException("Invalid JSON number", exception);
            }
            output.append(number);
        } else if (value instanceof Map<?, ?> map) {
            output.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!(entry.getKey() instanceof String key)) {
                    throw new IllegalArgumentException("Object keys must be strings");
                }
                if (!first) output.append(',');
                quote(key, output);
                output.append(':');
                write(entry.getValue(), output, depth + 1);
                first = false;
            }
            output.append('}');
        } else if (value instanceof List<?> list) {
            output.append('[');
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) output.append(',');
                write(list.get(i), output, depth + 1);
            }
            output.append(']');
        } else {
            throw new IllegalArgumentException("Unsupported JSON value: " + value.getClass().getName());
        }
    }

    private static void quote(String text, StringBuilder output) {
        output.append('"');
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            switch (ch) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\b' -> output.append("\\b");
                case '\f' -> output.append("\\f");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (ch < 0x20 || Character.isSurrogate(ch)) {
                        output.append("\\u");
                        String hex = Integer.toHexString(ch);
                        output.append("0".repeat(4 - hex.length())).append(hex);
                    } else {
                        output.append(ch);
                    }
                }
            }
        }
        output.append('"');
    }

    private static final class Parser {
        private final String text;
        private int index;

        private Parser(String text) {
            this.text = text;
        }

        private Object value(int depth) {
            if (depth > MAX_DEPTH) throw error("JSON nesting is too deep");
            whitespace();
            if (index >= text.length()) throw error("Expected a value");
            return switch (text.charAt(index)) {
                case '{' -> objectValue(depth);
                case '[' -> arrayValue(depth);
                case '"' -> stringValue();
                case 't' -> literal("true", Boolean.TRUE);
                case 'f' -> literal("false", Boolean.FALSE);
                case 'n' -> literal("null", null);
                default -> numberValue();
            };
        }

        private Map<String, Object> objectValue(int depth) {
            index++;
            Map<String, Object> result = new LinkedHashMap<>();
            whitespace();
            if (take('}')) return result;
            while (true) {
                whitespace();
                if (index >= text.length() || text.charAt(index) != '"') {
                    throw error("Expected an object key");
                }
                String key = stringValue();
                if (result.containsKey(key)) throw error("Duplicate object key");
                whitespace();
                expect(':');
                result.put(key, value(depth + 1));
                whitespace();
                if (take('}')) return result;
                expect(',');
            }
        }

        private List<Object> arrayValue(int depth) {
            index++;
            List<Object> result = new ArrayList<>();
            whitespace();
            if (take(']')) return result;
            while (true) {
                result.add(value(depth + 1));
                whitespace();
                if (take(']')) return result;
                expect(',');
            }
        }

        private String stringValue() {
            expect('"');
            StringBuilder result = new StringBuilder();
            while (index < text.length()) {
                char ch = text.charAt(index++);
                if (ch == '"') return result.toString();
                if (ch < 0x20) throw error("Unescaped control character");
                if (ch != '\\') {
                    result.append(ch);
                    continue;
                }
                if (index == text.length()) throw error("Incomplete string escape");
                char escape = text.charAt(index++);
                switch (escape) {
                    case '"', '\\', '/' -> result.append(escape);
                    case 'b' -> result.append('\b');
                    case 'f' -> result.append('\f');
                    case 'n' -> result.append('\n');
                    case 'r' -> result.append('\r');
                    case 't' -> result.append('\t');
                    case 'u' -> {
                        if (index + 4 > text.length()) throw error("Incomplete Unicode escape");
                        int code = 0;
                        for (int i = 0; i < 4; i++) {
                            char digit = text.charAt(index++);
                            int hex = digit >= '0' && digit <= '9' ? digit - '0'
                                    : digit >= 'a' && digit <= 'f' ? digit - 'a' + 10
                                    : digit >= 'A' && digit <= 'F' ? digit - 'A' + 10 : -1;
                            if (hex < 0) throw error("Invalid Unicode escape");
                            code = code * 16 + hex;
                        }
                        result.append((char) code);
                    }
                    default -> throw error("Unknown string escape");
                }
            }
            throw error("Unterminated string");
        }

        private Object literal(String expected, Object result) {
            if (!text.startsWith(expected, index)) throw error("Invalid literal");
            index += expected.length();
            return result;
        }

        private Number numberValue() {
            int start = index;
            take('-');
            if (take('0')) {
                if (index < text.length() && digit(text.charAt(index))) {
                    throw error("Leading zero in number");
                }
            } else {
                digits();
            }
            boolean integer = true;
            if (take('.')) {
                integer = false;
                digits();
            }
            if (take('e') || take('E')) {
                integer = false;
                if (!take('+')) take('-');
                digits();
            }
            String number = text.substring(start, index);
            try {
                if (integer) {
                    try {
                        return Long.valueOf(number);
                    } catch (NumberFormatException ignored) {
                        // 超出Long范围的合法JSON整数保留为BigDecimal，不截断精度。
                    }
                }
                return new BigDecimal(number);
            } catch (NumberFormatException exception) {
                throw error("Invalid number");
            }
        }

        private void digits() {
            int start = index;
            while (index < text.length() && digit(text.charAt(index))) index++;
            if (index == start) throw error("Expected a digit");
        }

        private static boolean digit(char ch) {
            return ch >= '0' && ch <= '9';
        }

        private void whitespace() {
            while (index < text.length()) {
                char ch = text.charAt(index);
                if (ch != ' ' && ch != '\t' && ch != '\r' && ch != '\n') return;
                index++;
            }
        }

        private boolean take(char expected) {
            if (index < text.length() && text.charAt(index) == expected) {
                index++;
                return true;
            }
            return false;
        }

        private void expect(char expected) {
            if (!take(expected)) throw error("Expected '" + expected + "'");
        }

        private IllegalArgumentException error(String message) {
            return new IllegalArgumentException(message + " at character " + index);
        }
    }
}
