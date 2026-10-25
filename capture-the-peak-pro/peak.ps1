# Capture the PEAK - Windows helper. Usage: .\peak.ps1 <command>
param([Parameter(Position=0)][string]$cmd = "help")
$IMAGE = "jaimnbidu/capture-the-peak:latest"

switch ($cmd) {
  "build"  { docker build --no-cache -t $IMAGE . }
  "board"  {
    docker run --rm -d --name peak-board -p 8000:8000 -p 7681:7681 -p 9000:9000 `
      -e PEAK_MODE=board -e PEAK_ADMIN_PASS='change_me_peak_admin' $IMAGE
    Write-Host "board up -> http://localhost:8000   (admin: /admin)"
  }
  "linear" {
    docker run --rm -d --name peak-linear -p 8100:8000 -p 7781:7681 -p 9100:9000 `
      -e PEAK_MODE=linear -e PEAK_LAB_PORT=9100 -e PEAK_ADMIN_PASS='change_me_peak_admin' $IMAGE
    Write-Host "linear up -> http://localhost:8100   (admin: /admin)"
  }
  "logs"   { docker logs -f peak-board }
  "stop"   { docker stop peak-board peak-linear 2>$null }
  "push"   { docker login; docker push $IMAGE }
  "clean"  { docker stop peak-board peak-linear 2>$null; docker image rm $IMAGE 2>$null }
  default  {
    Write-Host "Capture the PEAK"
    Write-Host "  .\peak.ps1 build    build + self-test the image"
    Write-Host "  .\peak.ps1 board    run the category board  (:8000)"
    Write-Host "  .\peak.ps1 linear   run the linear ascent   (:8100)"
    Write-Host "  .\peak.ps1 logs     tail portal logs"
    Write-Host "  .\peak.ps1 stop     stop both"
    Write-Host "  .\peak.ps1 push     push to Docker Hub"
    Write-Host "  .\peak.ps1 clean    stop + remove image"
  }
}
