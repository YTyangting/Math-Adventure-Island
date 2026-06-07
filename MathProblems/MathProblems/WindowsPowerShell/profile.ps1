
#region conda initialize
# !! Contents within this block are managed by 'conda init' !!
If (Test-Path "C:\CodeEnvironment\ANACONDA\Scripts\conda.exe") {
    (& "C:\CodeEnvironment\ANACONDA\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | ?{$_} | Invoke-Expression
}
#endregion

