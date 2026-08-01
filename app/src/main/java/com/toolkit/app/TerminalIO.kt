package com.toolkit.app

import android.os.Handler
import android.os.Looper
import java.util.concurrent.LinkedBlockingQueue
import java.util.regex.Pattern

object TerminalIO {

    private val main = Handler(Looper.getMainLooper())
    private val inputQueue = LinkedBlockingQueue<String>()
    private val ansi = Pattern.compile("\u001B\\[[0-9;?]*[a-zA-Z]|\u001B\\([0-9A-Za-z]|\u001B[=>]")

    @Volatile
    var onAppend: ((String) -> Unit)? = null

    @Volatile
    var onFinished: (() -> Unit)? = null

    @JvmStatic
    fun append(s: String) {
        val clean = ansi.matcher(s).replaceAll("").replace("\r", "")
        main.post { onAppend?.invoke(clean) }
    }

    @JvmStatic
    fun readInput(): String {
        return try {
            inputQueue.take()
        } catch (e: InterruptedException) {
            ""
        }
    }

    @JvmStatic
    fun submit(text: String) {
        inputQueue.offer(text)
    }

    @JvmStatic
    fun finished() {
        main.post { onFinished?.invoke() }
    }
}
