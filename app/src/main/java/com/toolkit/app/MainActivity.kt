package com.toolkit.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.activity.compose.BackHandler
import com.toolkit.app.ui.ToolKitTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PythonRunner.start(applicationContext)
        setContent {
            ToolKitTheme {
                var screen by remember { mutableStateOf("home") }
                BackHandler(enabled = screen != "home") {
                    screen = "home"
                }
                when (screen) {
                    "home" -> HomeScreen(onOpenPython = { screen = "python" })
                    "python" -> PythonScreen(onBack = { screen = "home" })
                }
            }
        }
    }
}
