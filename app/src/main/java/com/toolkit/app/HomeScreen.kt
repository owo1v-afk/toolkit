package com.toolkit.app

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.toolkit.app.ui.Accent
import com.toolkit.app.ui.GlassCard
import com.toolkit.app.ui.TextDim
import com.toolkit.app.ui.TextMain

@Composable
fun HomeScreen(onOpenPython: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 22.dp, vertical = 28.dp),
    ) {
        Spacer(Modifier.height(18.dp))
        Text(
            "ToolKit",
            color = TextMain,
            fontSize = 30.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(
            "набор инструментов в одном приложении",
            color = TextDim,
            fontSize = 14.sp,
            modifier = Modifier.padding(top = 4.dp),
        )
        Spacer(Modifier.height(30.dp))

        GlassCard(
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onOpenPython),
        ) {
            Column(Modifier.padding(22.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(44.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            ">_",
                            color = Accent,
                            fontFamily = FontFamily.Monospace,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    Column(Modifier.padding(start = 10.dp)) {
                        Text(
                            "Запуск Python софтов",
                            color = TextMain,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            "мини-терминал · пакеты ставятся автоматически",
                            color = TextDim,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(top = 2.dp),
                        )
                    }
                }
                Spacer(Modifier.height(14.dp))
                Text(
                    "Загрузите ваш .py файл — и он запустится сразу, без лишних команд. " +
                        "Внутри можно писать: полноценный мини-терминал.",
                    color = TextDim,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                )
                Spacer(Modifier.height(16.dp))
                Text(
                    "Открыть →",
                    color = Accent,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }
    }
}
