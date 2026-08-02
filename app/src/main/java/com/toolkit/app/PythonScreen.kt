package com.toolkit.app

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.toolkit.app.ui.Accent
import com.toolkit.app.ui.CardGlass
import com.toolkit.app.ui.GlassCard
import com.toolkit.app.ui.OkGreen
import com.toolkit.app.ui.TerminalBg
import com.toolkit.app.ui.TerminalText
import com.toolkit.app.ui.TextDim
import com.toolkit.app.ui.TextMain
import com.toolkit.app.ui.WarnOrange
import java.io.File
import kotlinx.coroutines.delay

private val bundledDeps = mapOf(
    "requests" to "requests",
    "colorama" to "colorama",
    "bs4" to "beautifulsoup4",
    "httpx" to "httpx",
)

private val stdlib = setOf(
    "abc", "argparse", "array", "asyncio", "base64", "binascii", "bisect", "builtins",
    "bz2", "calendar", "codecs", "collections", "colorsys", "concurrent", "configparser",
    "contextlib", "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "email", "enum", "errno", "faulthandler", "fnmatch", "fractions", "functools",
    "gc", "getpass", "glob", "gzip", "hashlib", "heapq", "hmac", "html", "http", "importlib",
    "inspect", "io", "ipaddress", "itertools", "json", "linecache", "locale", "logging",
    "lzma", "math", "mimetypes", "mmap", "multiprocessing", "numbers", "operator", "optparse",
    "os", "pathlib", "pdb", "pickle", "platform", "plistlib", "posixpath", "pprint",
    "profile", "pstats", "queue", "random", "re", "readline", "reprlib", "resource",
    "select", "selectors", "shelve", "shlex", "shutil", "signal", "site", "socket", "sqlite3",
    "ssl", "stat", "statistics", "string", "stringprep", "struct", "subprocess", "sys",
    "sysconfig", "tarfile", "tempfile", "textwrap", "threading", "time", "timeit", "tkinter",
    "token", "tokenize", "trace", "traceback", "tracemalloc", "types", "typing", "unicodedata",
    "unittest", "urllib", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser", "xml",
    "xmlrpc", "zipfile", "zipimport", "zlib", "zoneinfo",
)

private val importRegex = Regex("""(?m)^\s*(?:from\s+([A-Za-z_][A-Za-z0-9_]*)\s+import|import\s+([A-Za-z_][A-Za-z0-9_]*))""")

data class DepStatus(
    val ok: List<String>,
    val missing: List<String>,
)

fun scanDeps(source: String): DepStatus {
    val found = importRegex.findAll(source)
        .map { m -> m.groupValues[1].takeIf { it.isNotEmpty() } ?: m.groupValues[2] }
        .toSet()
    val ok = mutableListOf<String>()
    val missing = mutableListOf<String>()
    for (name in found) {
        val base = name.split(".").first()
        if (base in stdlib) {
            ok.add(base)
        } else if (base in bundledDeps) {
            ok.add("${base} (${bundledDeps[base]})")
        } else {
            missing.add(base)
        }
    }
    return DepStatus(ok.sorted(), missing.sorted())
}

private val ansiSgr = Regex("\u001B\\[([0-9;]*)m")
private val ansiOther = Regex(
    "\u001B(?:\\[[0-9;?]*[A-Za-z]|\\][^\u0007]*(?:\u0007|\u001B\\\\)|" +
        "[()][0-9A-Za-z]|[=>]|[cEGKHPZ]|\\[[0-9]*[A-Z])"
)

private val ansi16 = listOf(
    Color(0xFF1B1D20), Color(0xFFE06C75), Color(0xFF98C379), Color(0xFFE5C07B),
    Color(0xFF61AFEF), Color(0xFFC678DD), Color(0xFF56B6C2), Color(0xFFDCDFE4),
    Color(0xFF5C6370), Color(0xFFF06070), Color(0xFFA8E08A), Color(0xFFF0C070),
    Color(0xFF70B8F0), Color(0xFFD088E0), Color(0xFF60C0C8), Color(0xFFF8F8F8),
)

private fun ansiColor256(n: Int): Color {
    if (n < 16) return ansi16[n]
    if (n < 232) {
        val i = n - 16
        fun step(x: Int) = if (x == 0) 0 else 55 + x * 40
        return Color(step(i / 36), step((i % 36) / 6), step(i % 6))
    }
    val v = 8 + (n - 232) * 10
    return Color(v, v, v)
}

fun parseAnsi(raw: String): AnnotatedString = buildAnnotatedString {
    var fg: Color? = null
    var bg: Color? = null
    var bold = false
    var italic = false
    var underline = false
    var i = 0
    val n = raw.length
    while (i < n) {
        if (raw[i] != '\u001B') {
            val next = raw.indexOf('\u001B', i)
            val end = if (next == -1) n else next
            val span = raw.substring(i, end)
            if (span.isNotEmpty()) {
                withStyle(
                    SpanStyle(
                        color = fg ?: TerminalText,
                        background = bg,
                        fontWeight = if (bold) FontWeight.Bold else null,
                        fontStyle = if (italic) FontStyle.Italic else null,
                        textDecoration = if (underline) TextDecoration.Underline else null,
                    )
                ) {
                    append(span)
                }
            }
            i = end
            continue
        }
        val m = ansiSgr.find(raw, i)
        if (m != null && m.range.first == i) {
            val codes = if (m.groupValues[1].isEmpty()) {
                listOf(0)
            } else {
                m.groupValues[1].split(';').mapNotNull { it.toIntOrNull() }
            }
            var k = 0
            while (k < codes.size) {
                when (val code = codes[k]) {
                    0 -> { fg = null; bg = null; bold = false; italic = false; underline = false }
                    1 -> bold = true
                    3 -> italic = true
                    4 -> underline = true
                    in 30..37 -> fg = ansi16[code - 30]
                    in 90..97 -> fg = ansi16[code - 90 + 8]
                    in 40..47 -> bg = ansi16[code - 40]
                    in 100..107 -> bg = ansi16[code - 100 + 8]
                    39 -> fg = null
                    49 -> bg = null
                    38, 48 -> {
                        val isFg = code == 38
                        if (k + 1 < codes.size) {
                            when (codes[k + 1]) {
                                5 -> if (k + 2 < codes.size) {
                                    val color = ansiColor256(codes[k + 2])
                                    if (isFg) fg = color else bg = color
                                    k += 2
                                }
                                2 -> if (k + 4 < codes.size) {
                                    val color = Color(codes[k + 2], codes[k + 3], codes[k + 4])
                                    if (isFg) fg = color else bg = color
                                    k += 4
                                }
                            }
                        }
                    }
                }
                k++
            }
            i = m.range.last + 1
            continue
        }
        val mo = ansiOther.find(raw, i)
        if (mo != null && mo.range.first == i) {
            i = mo.range.last + 1
            continue
        }
        i++
    }
}

@Composable
fun PythonScreen(onBack: () -> Unit) {
    val ctx = LocalContext.current
    var fileName by remember { mutableStateOf<String?>(null) }
    var fileSize by remember { mutableStateOf(0L) }
    var filePath by remember { mutableStateOf<String?>(null) }
    var preview by remember { mutableStateOf("") }
    var deps by remember { mutableStateOf<DepStatus?>(null) }
    var output by remember { mutableStateOf("") }
    var input by remember { mutableStateOf("") }
    var running by remember { mutableStateOf(false) }
    var startedOnce by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var progress by remember { mutableStateOf<Pair<String, Int>?>(null) }
    val outBuffer = remember { StringBuilder() }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        try {
            val bytes = ctx.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                ?: throw IllegalStateException("не удалось прочитать файл")
            val content = String(bytes, Charsets.UTF_8)
            val rawName = uri.lastPathSegment?.substringAfterLast('/') ?: "script.py"
            val safeName = rawName.replace(Regex("""[^A-Za-z0-9._-]"""), "_").ifBlank { "script.py" }
            val dir = File(ctx.filesDir, "scripts").apply { mkdirs() }
            val dest = File(dir, safeName)
            dest.writeBytes(bytes)
            fileName = safeName
            fileSize = bytes.size.toLong()
            filePath = dest.absolutePath
            preview = content.lines().take(8).joinToString("\n").ifBlank { "(пустой файл)" }
            deps = scanDeps(content)
            error = null
            output = ""
            outBuffer.clear()
            startedOnce = false
            running = false
        } catch (t: Throwable) {
            error = t.message ?: "ошибка загрузки"
        }
    }

    fun startScript() {
        val path = filePath ?: return
        if (PythonRunner.running) return
        outBuffer.clear()
        output = ""
        startedOnce = true
        running = true
        TerminalIO.onAppend = { chunk ->
            synchronized(outBuffer) {
                outBuffer.append(chunk)
                if (outBuffer.length > 300_000) {
                    outBuffer.delete(0, 150_000)
                }
                output = outBuffer.toString()
            }
        }
        TerminalIO.onFinished = {
            running = false
            output = synchronized(outBuffer) { outBuffer.toString() }
        }
        TerminalIO.onProgress = { pkg, pct ->
            progress = if (pct < 0) null else pkg to pct
        }
        PythonRunner.run(ctx, path)
    }

    BackHandler(enabled = startedOnce) {
        onBack()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 22.dp, vertical = 24.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "←",
                color = Accent,
                fontSize = 20.sp,
                modifier = Modifier
                    .padding(end = 12.dp)
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null,
                        onClick = onBack,
                    ),
            )
            Text(
                "Запуск Python софтов",
                color = TextMain,
                fontSize = 20.sp,
            )
        }
        Spacer(Modifier.height(18.dp))

        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp)) {
                Text(
                    "Загрузите ваш .py файл, он отобразится в окне СРАЗУ после загрузки, " +
                        "без лишних команд. Вы сможете писать, проще говоря у вас будет мини " +
                        "терминал прямо у нас, мы скачаем все нужные вашему софту зависимости :)",
                    color = TextDim,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                )
            }
        }
        Spacer(Modifier.height(16.dp))

        Button(
            onClick = { picker.launch(arrayOf("*/*")) },
            colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color(0xFF0E1013)),
            shape = RoundedCornerShape(18.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                if (fileName == null) "Загрузить .py файл" else "Заменить файл",
                fontSize = 15.sp,
                modifier = Modifier.padding(vertical = 6.dp),
            )
        }

        if (error != null) {
            Spacer(Modifier.height(12.dp))
            Text(error!!, color = WarnOrange, fontSize = 13.sp)
        }

        if (fileName != null) {
            Spacer(Modifier.height(16.dp))
            GlassCard(modifier = Modifier.fillMaxWidth(), radius = 20.dp) {
                Column(Modifier.padding(16.dp)) {
                    Text(fileName!!, color = TextMain, fontSize = 15.sp)
                    Text(
                        "размер: ${fileSize / 1024} КБ",
                        color = TextDim,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        preview,
                        color = TextDim,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        lineHeight = 14.sp,
                        modifier = Modifier
                            .horizontalScroll(rememberScrollState())
                            .fillMaxWidth(),
                    )
                    val status = deps
                    if (status != null) {
                        Spacer(Modifier.height(12.dp))
                        if (status.missing.isEmpty()) {
                            Text(
                                "зависимости: всё встроено ✓",
                                color = OkGreen,
                                fontSize = 12.sp,
                            )
                        } else {
                            Text(
                                "не найдено: ${status.missing.joinToString(", ")} — скачаются сами при первом import",
                                color = WarnOrange,
                                fontSize = 12.sp,
                            )
                        }
                        if (status.ok.isNotEmpty()) {
                            Text(
                                "импорты: ${status.ok.joinToString(", ")}",
                                color = TextDim,
                                fontSize = 11.sp,
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                    }
                }
            }
            Spacer(Modifier.height(16.dp))

            Row(modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { startScript() },
                    enabled = filePath != null && !running,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Accent,
                        contentColor = Color(0xFF0E1013),
                        disabledContainerColor = CardGlass,
                        disabledContentColor = TextDim,
                    ),
                    shape = RoundedCornerShape(18.dp),
                    modifier = Modifier.weight(1f),
                ) {
                    Text(
                        if (running) "выполняется…" else if (startedOnce) "Запустить ещё раз" else "Запустить",
                        fontSize = 15.sp,
                        modifier = Modifier.padding(vertical = 6.dp),
                    )
                }
                if (running) {
                    Spacer(Modifier.width(10.dp))
                    Button(
                        onClick = {
                            TerminalIO.cancel()
                            running = false
                            output += "\n[остановлено]\n"
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0x33F4B400),
                            contentColor = WarnOrange,
                        ),
                        shape = RoundedCornerShape(18.dp),
                    ) {
                        Text(
                            "Стоп",
                            fontSize = 15.sp,
                            modifier = Modifier.padding(vertical = 6.dp),
                        )
                    }
                }
            }
        }

        if (startedOnce) {
            val dl = progress
            if (dl != null) {
                Spacer(Modifier.height(14.dp))
                GlassCard(modifier = Modifier.fillMaxWidth(), radius = 18.dp) {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                "скачиваю ${dl.first}",
                                color = TextMain,
                                fontSize = 14.sp,
                            )
                            Spacer(Modifier.weight(1f))
                            Text(
                                "${dl.second}%",
                                color = Accent,
                                fontSize = 15.sp,
                                fontFamily = FontFamily.Monospace,
                            )
                        }
                        Spacer(Modifier.height(10.dp))
                        val pct by animateFloatAsState(
                            targetValue = dl.second / 100f,
                            animationSpec = tween(200),
                            label = "dl",
                        )
                        LinearProgressIndicator(
                            progress = { pct },
                            color = Accent,
                            trackColor = Color(0x22FFFFFF),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
            Spacer(Modifier.height(18.dp))
            TerminalView(output = output, input = input, onInput = { input = it }, onSend = {
                val line = input
                output += "\n> $line\n"
                TerminalIO.submit(line)
                input = ""
            })
        }
    }
}

@Composable
fun TerminalView(output: String, input: String, onInput: (String) -> Unit, onSend: () -> Unit) {
    val clipboard = LocalClipboardManager.current
    var copied by remember { mutableStateOf(false) }
    var termScale by remember { mutableFloatStateOf(1f) }
    LaunchedEffect(copied) {
        if (copied) {
            delay(1400)
            copied = false
        }
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(TerminalBg, RoundedCornerShape(20.dp))
            .padding(10.dp)
            .pointerInput(Unit) {
                detectTransformGestures { _, _, zoom, _ ->
                    termScale = (termScale * zoom).coerceIn(0.5f, 3f)
                }
            }
            .pointerInput(Unit) {
                detectTapGestures(onDoubleTap = { termScale = 1f })
            }
            .graphicsLayer {
                scaleX = termScale
                scaleY = termScale
                transformOrigin = TransformOrigin(0f, 0f)
            },
    ) {
        val display = remember(output) { parseAnsi(output) }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "mini-term",
                color = TextDim,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
            )
            Spacer(Modifier.weight(1f))
            Text(
                "×" + "%.1f".format(termScale),
                color = TextDim,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
            )
            Spacer(Modifier.width(10.dp))
            Text(
                if (copied) "✓ скопировано" else "⧉ копировать",
                color = if (copied) OkGreen else Accent,
                fontSize = 11.sp,
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null,
                    ) {
                        clipboard.setText(AnnotatedString(display.text))
                        copied = true
                    },
            )
        }
        Spacer(Modifier.height(6.dp))
        Text(
            display,
            color = TerminalText,
            fontFamily = FontFamily.Monospace,
            fontSize = 10.sp,
            lineHeight = 13.sp,
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .heightIn(min = 140.dp, max = 320.dp),
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = input,
            onValueChange = onInput,
            singleLine = true,
            placeholder = { Text("ввод…", color = TextDim, fontSize = 12.sp) },
            textStyle = TextStyle(
                color = TerminalText,
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
            ),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
            keyboardActions = KeyboardActions(onSend = { onSend() }),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Accent,
                unfocusedBorderColor = Color(0x33FFFFFF),
                focusedContainerColor = Color(0x0DFFFFFF),
                unfocusedContainerColor = Color(0x0DFFFFFF),
                cursorColor = Accent,
            ),
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
