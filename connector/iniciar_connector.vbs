Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "C:\Users\TGL Solutions\Desktop\NEXUS\connector"
oShell.Run """C:\Users\TGL Solutions\Desktop\NEXUS\connector\.venv\Scripts\pythonw.exe"" main.py", 0, False
