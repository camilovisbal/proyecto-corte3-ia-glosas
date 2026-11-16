# Captura paginas de precios y fuentes con Edge headless (evidencia con fecha de consulta).
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$dir = $PSScriptRoot
$paginas = @(
  @("01-precio-openrouter-qwen3.8-27b.png", "https://openrouter.ai/qwen/qwen3.8-27b"),
  @("02-precio-openrouter-qwen3-14b.png", "https://openrouter.ai/qwen/qwen3-14b"),
  @("03-precio-g6e-xlarge-us-east-1.png", "https://compute.doit.com/spot/us-east-1/g6e.xlarge"),
  @("04-precio-l40s-gpudojo.png", "https://gpudojo.com/l40s"),
  @("05-trm-2026-11-11.png", "https://www.dolar-colombia.com/2026-11-11"),
  @("06-aws-local-zones-latam.png", "https://aws.amazon.com/blogs/publicsector/aws-announces-local-zones-latin-america"),
  @("07-api-clinica-docs.png", "https://labs.proyectoasur.org/api/clinica/docs")
)
foreach ($p in $paginas) {
  $out = Join-Path $dir $p[0]
  $proc = Start-Process -FilePath $edge -ArgumentList @("--headless=new","--disable-gpu","--hide-scrollbars","--window-size=1280,1400","--virtual-time-budget=15000","--screenshot=`"$out`"",$p[1]) -PassThru -WindowStyle Hidden
  if (-not $proc.WaitForExit(90000)) { $proc.Kill() }
  "{0} -> {1}" -f $p[0], (Test-Path $out)
}
