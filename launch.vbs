Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run chr(34) & "%APPDATA%\pypoetry\venv\Scripts\poetry.exe" & Chr(34) & " run python app.py", 0
Set WshShell = Nothing