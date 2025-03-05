Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & CreateObject("WScript.Shell").CurrentDirectory & "\start_bot.bat" & chr(34), 0
Set WshShell = Nothing 