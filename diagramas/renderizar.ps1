# Convierte los diagramas SVG a PNG con Edge headless.
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$dir = $PSScriptRoot
foreach ($p in @(@("flujo", "1000,1060"), @("arquitectura", "1000,820"))) {
  $svg = "file:///" + (($dir -replace '\\', '/') + "/" + $p[0] + ".svg")
  $png = Join-Path $dir ($p[0] + ".png")
  $proc = Start-Process -FilePath $edge -ArgumentList @("--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=$($p[1])", "--screenshot=`"$png`"", "`"$svg`"") -PassThru -WindowStyle Hidden
  if (-not $proc.WaitForExit(60000)) { try { $proc.Kill() } catch {} }
  "{0} -> {1}" -f $png, (Test-Path $png)
}
