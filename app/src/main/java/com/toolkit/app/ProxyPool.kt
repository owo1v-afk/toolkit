package com.toolkit.app

import java.util.Base64

data class ProxyEndpoint(
    val kind: String,
    val host: String,
    val port: Int,
    val user: String? = null,
    val pass: String? = null,
)

val EMBEDDED_PROXIES = """
    socks5://208.102.51.6:58208
    socks5://69.61.200.104:36181
    socks5://66.42.224.229:41679
    socks5://192.252.208.67:14287
    socks5://72.195.34.35:27360
    socks5://174.77.111.198:49547
    socks5://184.178.172.25:15291
    socks5://184.178.172.18:15280
    socks5://184.178.172.5:15303
    socks5://72.195.34.41:4145
    socks5://103.174.122.197:8199
    socks5://186.26.95.249:61445
    socks5://121.169.46.116:1090
    socks5://5.255.117.127:1080
    socks5://115.127.53.114:1080
    socks5://149.62.186.244:1080
    socks5://110.235.240.223:1080
    socks5://43.230.193.154:1080
    socks5://110.235.246.62:1080
    socks5://202.62.52.20:1080
    http://85.208.200.185:8081
    http://189.50.45.46:1995
    http://103.171.255.106:8080
    http://36.92.199.158:8080
    http://217.76.243.2:999
    http://177.234.217.83:999
    http://38.158.83.161:999
    http://41.33.245.139:1981
""".trimIndent()

fun parseProxies(text: String): List<ProxyEndpoint> {
    val out = ArrayList<ProxyEndpoint>()
    for (part in text.split('\n', ',', ';', ' ')) {
        var s = part.trim()
        if (s.isEmpty()) continue
        var kind = "http"
        when {
            s.startsWith("socks5://") -> { kind = "socks5"; s = s.substringAfter("//") }
            s.startsWith("socks://") -> { kind = "socks5"; s = s.substringAfter("//") }
            s.startsWith("https://") -> { kind = "https"; s = s.substringAfter("//") }
            s.startsWith("http://") -> { kind = "http"; s = s.substringAfter("//") }
        }
        var user: String? = null
        var pass: String? = null
        if (s.contains("@")) {
            val auth = s.substringBefore("@")
            s = s.substringAfter("@")
            user = auth.substringBefore(":").takeIf { it.isNotEmpty() }
            pass = auth.substringAfter(":", "").takeIf { it.isNotEmpty() }
        }
        val host = s.substringBefore(":")
        val port = s.substringAfter(":", "").trim().toIntOrNull()
        if (host.isEmpty() || port == null || port !in 1..65535) continue
        out.add(ProxyEndpoint(kind, host, port, user, pass))
    }
    return out
}

fun basicAuth(user: String, pass: String): String =
    Base64.getEncoder().encodeToString("$user:$pass".toByteArray(Charsets.UTF_8))
