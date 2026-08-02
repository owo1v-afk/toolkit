package com.toolkit.app

import android.os.Handler
import android.os.Looper
import java.util.concurrent.LinkedBlockingQueue

object TerminalIO {

    private val main = Handler(Looper.getMainLooper())
    private val inputQueue = LinkedBlockingQueue<String>()

    @Volatile
    var onAppend: ((String) -> Unit)? = null

    @Volatile
    var onFinished: (() -> Unit)? = null

    @Volatile
    var onProgress: ((String, Int) -> Unit)? = null

    @Volatile
    @JvmField
    var cancelled = false

    @JvmStatic
    fun reset() {
        cancelled = false
    }

    @JvmStatic
    fun cancel() {
        cancelled = true
        inputQueue.offer("")
    }

    @JvmStatic
    fun progress(pkg: String, percent: Int) {
        main.post { onProgress?.invoke(pkg, percent) }
    }

    @JvmStatic
    fun append(s: String) {
        main.post { onAppend?.invoke(s) }
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
