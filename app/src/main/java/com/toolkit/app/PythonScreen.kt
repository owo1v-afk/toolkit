package com.toolkit.app

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.ImeAction
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
                output = outBuffer.toString()
            }
        }
        TerminalIO.onFinished = {
            running = false
            output = synchronized(outBuffer) { outBuffer.toString() }
        }
        PythonRunner.run(ctx, path) {}
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
                                "не найдено в сборке: ${status.missing.joinToString(", ")}",
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
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    if (running) "выполняется…" else if (startedOnce) "Запустить ещё раз" else "Запустить",
                    fontSize = 15.sp,
                    modifier = Modifier.padding(vertical = 6.dp),
                )
            }
        }

        if (startedOnce) {
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
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(TerminalBg, RoundedCornerShape(22.dp))
            .padding(14.dp),
    ) {
        Text(
            "mini-term",
            color = TextDim,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            output.ifBlank { "_" },
            color = TerminalText,
            fontFamily = FontFamily.Monospace,
            fontSize = 12.sp,
            lineHeight = 16.sp,
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .heightIn(min = 180.dp, max = 380.dp),
        )
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(
            value = input,
            onValueChange = onInput,
            singleLine = true,
            placeholder = { Text("ввод для скрипта…", color = TextDim, fontSize = 13.sp) },
            textStyle = TextStyle(
                color = TerminalText,
                fontFamily = FontFamily.Monospace,
                fontSize = 13.sp,
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
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
