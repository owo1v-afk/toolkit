package com.toolkit.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.runtime.*
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
                AnimatedContent(
                    targetState = screen,
                    transitionSpec = {
                        (fadeIn(animationSpec = tween(230)) +
                            slideInHorizontally(initialOffsetX = { it / 24 }))
                            .togetherWith(
                                fadeOut(animationSpec = tween(230)) +
                                    slideOutHorizontally(targetOffsetX = { -it / 24 })
                            )
                    },
                    label = "screen",
                ) { s ->
                    when (s) {
                        "home" -> HomeScreen(
                            onOpenPython = { screen = "python" },
                            onOpenStresser = { screen = "stresser" },
                        )
                        "python" -> PythonScreen(onBack = { screen = "home" })
                        "stresser" -> WifiStresserScreen(onBack = { screen = "home" })
                    }
                }
            }
        }
    }
}
