package com.toolkit.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Ink = Color(0xFF0E1013)
val InkSoft = Color(0xFF14171B)
val CardGlass = Color(0xFF1B1F24)
val BorderGlass = Color(0x26FFFFFF)
val TextMain = Color(0xFFE8EAED)
val TextDim = Color(0xFF9AA0A6)
val Accent = Color(0xFF8AB4F8)
val AccentSoft = Color(0xFF6FA8DC)
val TerminalBg = Color(0xFF0A0C0F)
val TerminalText = Color(0xFFD6E3EC)
val OkGreen = Color(0xFF81C995)
val WarnOrange = Color(0xFFF4B400)

private val Scheme = darkColorScheme(
    primary = Accent,
    onPrimary = Color(0xFF0E1013),
    secondary = AccentSoft,
    background = Ink,
    onBackground = TextMain,
    surface = InkSoft,
    onSurface = TextMain,
    surfaceVariant = CardGlass,
    onSurfaceVariant = TextDim,
    outline = BorderGlass,
)

@Composable
fun ToolKitTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = Scheme,
        content = content,
    )
}
