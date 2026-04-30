Get-Content .env | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
    $line = $_.Trim()
    if ($line -ne "") {
        $name, $value = $line.split('=', 2)
        if ($name -and $value) {
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
cd dbt
..\venv\Scripts\dbt.exe docs generate
