# TerminalIO доступен из Python-кода через рефлексию Chaquopy —
# его нельзя переименовывать или выбрасывать при обфускации.
-keep class com.toolkit.app.TerminalIO { *; }