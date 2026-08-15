package com.toolkit.app

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File

object PythonRunner {

    @Volatile
    private var started = false

    @Volatile
    var running = false
        private set

    private fun ensureStarted(context: Context) {
        if (!started) {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(context))
            }
            started = true
        }
    }

    fun start(context: Context) {
        ensureStarted(context)
        bundledScript(context)
    }

    fun bundledScript(context: Context): String {
        val dir = File(context.filesDir, "scripts").apply { mkdirs() }
        val dest = File(dir, "betasms.py")
        if (!dest.exists()) {
            runCatching {
                context.assets.open("python/betasms.py").use { src ->
                    dest.outputStream().use { src.copyTo(it) }
                }
            }
        }
        return dest.absolutePath
    }

    fun run(context: Context, scriptPath: String) {
        runWithArgs(context, scriptPath, emptyList())
    }

    fun runWithArgs(context: Context, scriptPath: String, args: List<String>) {
        if (running) {
            TerminalIO.append("Скрипт уже выполняется. Нажмите Стоп или дождитесь завершения.\n")
            return
        }
        ensureStarted(context)
        running = true
        Thread({
            try {
                val py = Python.getInstance()
                py.getModule("runner").callAttr("run", scriptPath, args.joinToString("\u0000"))
            } catch (t: Throwable) {
                TerminalIO.append("Ошибка запуска: ${t.message}\n")
            } finally {
                running = false
            }
        }, "py-runner").start()
    }
}
