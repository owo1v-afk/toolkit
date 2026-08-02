package com.toolkit.app

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

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
    }

    fun run(context: Context, scriptPath: String) {
        if (running) {
            TerminalIO.append("Скрипт уже выполняется. Нажмите Стоп или дождитесь завершения.\n")
            return
        }
        ensureStarted(context)
        running = true
        Thread({
            try {
                val py = Python.getInstance()
                py.getModule("runner").callAttr("run", scriptPath, "")
            } catch (t: Throwable) {
                TerminalIO.append("Ошибка запуска: ${t.message}\n")
            } finally {
                running = false
            }
        }, "py-runner").start()
    }
}
