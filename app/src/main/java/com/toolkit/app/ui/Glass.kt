package com.toolkit.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    radius: Dp = 26.dp,
    tint: Color = Color(0x0CFFFFFF),
    content: @Composable BoxScope.() -> Unit,
) {
    val shape = RoundedCornerShape(radius)
    Box(
        modifier = modifier
            .clip(shape)
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0x14FFFFFF),
                        tint,
                        Color(0x05FFFFFF),
                    )
                )
            ),
    ) {
        content()
    }
}

val GlassRadius = RoundedCornerShape(20.dp)

@Composable
fun flatButtonElevation(): androidx.compose.material3.ButtonElevation =
    androidx.compose.material3.ButtonDefaults.buttonElevation(
        defaultElevation = 0.dp,
        pressedElevation = 0.dp,
        focusedElevation = 0.dp,
        hoveredElevation = 0.dp,
        disabledElevation = 0.dp,
    )
