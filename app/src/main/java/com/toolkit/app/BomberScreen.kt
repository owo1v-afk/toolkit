package com.toolkit.app

import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
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
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

val BombRed = Color(0xFFFF6B6B)

private val ansiStrip = Regex("\u001B\\[[0-9;]*[A-Za-z]")

@Composable
fun BombIcon(modifier: Modifier, color: Color, animated: Boolean = false) {
    val pulse = if (animated) {
        val t = rememberInfiniteTransition(label = "bomb")
        val a = t.animateFloat(
            initialValue = 0.3f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(650), RepeatMode.Reverse),
            label = "pulse",
        )
        a.value
    } else 1f
    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w * 0.5f
        val cy = h * 0.62f
        val r = w * 0.26f
        val fuse = Path()
        fuse.moveTo(cx + r * 0.4f, cy - r * 0.5f)
        fuse.cubicTo(
            cx + r * 0.75f, cy - r * 1.05f,
            cx + r * 0.95f, cy - r * 1.05f,
            cx + r * 1.15f, cy - r * 0.6f,
        )
        drawPath(fuse, color.copy(alpha = pulse), style = Stroke(width = w * 0.06f, cap = StrokeCap.Round))
        drawCircle(Color(0xFFFFD479).copy(alpha = pulse), radius = w * 0.055f, center = Offset(cx + r * 1.15f, cy - r * 0.6f))
        drawCircle(color, radius = r, center = Offset(cx, cy))
        drawCircle(color.copy(alpha = 0.3f), radius = r * 0.45f, center = Offset(cx - r * 0.32f, cy - r * 0.32f))
        val shine = Path()
        shine.moveTo(cx - r * 0.22f, cy)
        shine.lineTo(cx + r * 0.22f, cy)
        drawPath(shine, Color(0xFF0E1013).copy(alpha = 0.5f), style = Stroke(width = w * 0.045f, cap = StrokeCap.Round))
        drawCircle(Color(0xFFFFD479).copy(alpha = pulse * 0.9f), radius = w * 0.028f, center = Offset(cx - r * 1.15f, cy - r * 0.85f))
    }
}

private data class BomberLogLine(val text: String, val color: Color)

@Composable
fun BomberScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    var number by remember { mutableStateOf("") }
    var proxy by remember { mutableStateOf("") }
    var running by remember { mutableStateOf(false) }
    val logs = remember { mutableStateListOf<BomberLogLine>() }
    val listState = rememberLazyListState()
    val outBuffer = remember { StringBuilder() }

    BackHandler(enabled = true, onBack = onBack)

    fun addLog(text: String, color: Color = TextDim) {
        val ts = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        logs.add(BomberLogLine("[$ts] $text", color))
        if (logs.size > 150) logs.removeAt(0)
    }

    LaunchedEffect(logs.size) {
        if (logs.isNotEmpty()) runCatching { listState.scrollToItem(logs.size - 1) }
    }

    fun stopBomber() {
        running = false
        TerminalIO.cancel()
        addLog("Останавливаю…", WarnOrange)
    }

    fun startBomber() {
        val n = number.trim()
        if (n.isEmpty()) {
            addLog("Введите номер телефона", WarnOrange)
            return
        }
        if (PythonRunner.running) return
        val scriptPath = PythonRunner.bundledScript(ctx)
        val scriptsDir = File(scriptPath).parentFile
        if (proxy.isNotBlank()) {
            val pr = proxy.trim()
            runCatching {
                File(scriptsDir, "proxy.txt").writeText("$pr\n")
            }
            addLog("Прокси: $pr", AccentSoft)
        } else {
            runCatching { File(scriptsDir, "proxy.txt").delete() }
            addLog("Прокси не задан — работаем с текущего IP", TextDim)
        }
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
                                line.contains("успеш") || line.contains("отправлено") ||
                                    line.contains("sent") || line.contains("✓") ||
                                    line.contains("Успех") -> OkGreen
                                line.contains("ошибк") || line.contains("fail") ||
                                    line.contains("Ошиб") || line.contains("✗") -> BombRed
                                line.contains("ЗАПУСК") || line.contains("СТАТИСТИКА") ||
                                    line.contains("Прокси:") || line.contains("эндпоинт") -> Accent
                                else -> TextDim
                            }
                            logs.add(BomberLogLine(line, color))
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
            if (rest.isNotBlank()) logs.add(BomberLogLine(rest, TextDim))
            outBuffer.clear()
        }
        TerminalIO.onProgress = null
        addLog("Запуск бомбера (встроен в приложение)", Accent)
        addLog("Номер: $n", TextDim)
        TerminalIO.clearInput()
        TerminalIO.submit(n)
        TerminalIO.submit(if (proxy.isBlank()) "n" else "y")
        TerminalIO.submit("")
        TerminalIO.submit("")
        PythonRunner.runWithArgs(ctx, scriptPath, emptyList())
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
                "Phone Bomber",
                color = TextMain,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.weight(1f))
            BombIcon(
                modifier = Modifier.size(30.dp),
                color = Accent,
                animated = running,
            )
        }

        Spacer(Modifier.height(14.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    "Телефонный бомбер (заказы обратных звонков, 540+ сервисов). " +
                        "Введите номер и, при желании, прокси (ip:port). Без прокси работает с текущего IP.",
                    color = TextDim,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    "● встроен в приложение, готов к запуску",
                    color = OkGreen,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                OutlinedTextField(
                    value = number,
                    onValueChange = { number = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Номер телефона", color = TextDim, fontSize = 13.sp) },
                    placeholder = { Text("+7…", color = TextDim.copy(alpha = 0.5f), fontSize = 14.sp) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace,
                    ),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Phone,
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
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = proxy,
                    onValueChange = { proxy = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Прокси (необязательно)", color = TextDim, fontSize = 13.sp) },
                    placeholder = { Text("ip:port", color = TextDim.copy(alpha = 0.5f), fontSize = 14.sp) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TextMain,
                        fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace,
                    ),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Text,
                        imeAction = ImeAction.Done,
                    ),
                    keyboardActions = KeyboardActions(onDone = { if (!running) startBomber() }),
                    shape = RoundedCornerShape(14.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Accent,
                        unfocusedBorderColor = BorderGlass,
                        focusedTextColor = TextMain,
                        cursorColor = Accent,
                        focusedLabelColor = AccentSoft,
                    ),
                )
                Spacer(Modifier.height(12.dp))
                Button(
                    onClick = { if (running) stopBomber() else startBomber() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (running) Color(0xFFB3261E) else Accent,
                        contentColor = if (running) Color.White else Color(0xFF0E1013),
                    ),
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
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
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Text(
                    "Логи",
                    color = TextMain,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(6.dp))
                if (logs.isEmpty()) {
                    Text(
                        "Запустите бомбер — здесь появится лог.",
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