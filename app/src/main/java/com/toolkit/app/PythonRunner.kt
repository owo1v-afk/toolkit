package com.toolkit.app

import android.content.Context
import com.chaquo.python.AndroidPlatform
import com.chaquo.python.Python
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
    }

    fun run(context: Context, scriptPath: String, onResult: (String) -> Unit) {
        if (running) {
            onResult("Скрипт уже выполняется.")
            return
        }
        ensureStarted(context)
        running = true
        Thread({
            try {
                val py = Python.getInstance()
                val argv = java.util.ArrayList<String>()
                argv.add(File(scriptPath).name)
                py.getModule("runner").callAttr("run", scriptPath, argv)
            } catch (t: Throwable) {
                TerminalIO.append("Ошибка запуска: ${t.message}\n")
            } finally {
                running = false
            }
        }, "py-runner").start()
    }
}
