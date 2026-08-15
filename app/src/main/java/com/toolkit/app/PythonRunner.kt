package com.toolkit.app

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

object PythonRunner {

    @Volatile
    private var started = false

    @Volatile
    var running = false
        private set

    private val aesKey = byteArrayOf(
        0x9f.toByte(), 0x3b.toByte(), 0x21.toByte(), 0xac.toByte(),
        0x7d.toByte(), 0xe4.toByte(), 0xc1.toByte(), 0x5a.toByte(),
        0x08.toByte(), 0xd6.toByte(), 0xe2.toByte(), 0xb7.toByte(),
        0xf1.toByte(), 0x4c.toByte(), 0x38.toByte(), 0xa6.toByte(),
    )

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

    private fun decrypt(data: ByteArray): ByteArray {
        val iv = data.copyOfRange(0, 16)
        val ct = data.copyOfRange(16, data.size)
        val key = SecretKeySpec(aesKey, "AES")
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.DECRYPT_MODE, key, IvParameterSpec(iv))
        return cipher.doFinal(ct)
    }

    fun bundledSource(context: Context): String {
        val bytes = context.assets.open("python/betasms.py").use { it.readBytes() }
        return String(decrypt(bytes), Charsets.UTF_8)
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

    fun runBundled(context: Context, source: String, cwd: String) {
        if (running) {
            TerminalIO.append("Скрипт уже выполняется. Нажмите Стоп или дождитесь завершения.\n")
            return
        }
        ensureStarted(context)
        running = true
        Thread({
            try {
                val py = Python.getInstance()
                py.getModule("runner").callAttr("run_source", source, cwd, "")
            } catch (t: Throwable) {
                TerminalIO.append("Ошибка запуска: ${t.message}\n")
            } finally {
                running = false
            }
        }, "py-runner").start()
    }
}