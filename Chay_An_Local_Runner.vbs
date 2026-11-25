' Script khoi dong Local Runner Service ngam (khong hien cua so den console)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "pythonw local_runner_service.py", 0, False

