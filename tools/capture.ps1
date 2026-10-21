# Captures a single window (never the whole screen) to a PNG, for the guide's screenshots.
# PrintWindow asks the window to paint itself, so it works even when the window is behind others.
# Usage: .\tools\capture.ps1 -Title "Ollama" -Out docs\assets\screens\ollama-app.png
param(
    [Parameter(Mandatory)] [string] $Title,
    [Parameter(Mandatory)] [string] $Out,
    [string] $Process
)

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
}
'@
Add-Type -AssemblyName System.Drawing
[Win]::SetProcessDPIAware() | Out-Null

$procs = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$Title*" }
if ($Process) { $procs = $procs | Where-Object ProcessName -eq $Process }
$proc = $procs | Select-Object -First 1
if (-not $proc) { throw "No window whose title contains '$Title'" }

$h = $proc.MainWindowHandle
if ([Win]::IsIconic($h)) { [Win]::ShowWindow($h, 9) | Out-Null; Start-Sleep -Milliseconds 600 }

$r = New-Object Win+RECT
[Win]::GetWindowRect($h, [ref]$r) | Out-Null
$w = $r.R - $r.L; $hgt = $r.B - $r.T

$bmp = New-Object System.Drawing.Bitmap $w, $hgt
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[Win]::PrintWindow($h, $hdc, 2) | Out-Null   # PW_RENDERFULLCONTENT: needed for GPU-drawn (Electron/Chromium) windows
$g.ReleaseHdc($hdc)

$dir = Split-Path $Out
New-Item -ItemType Directory -Force $dir | Out-Null
$full = Join-Path (Resolve-Path -LiteralPath $dir).Path (Split-Path $Out -Leaf)
$bmp.Save($full)
"$($proc.ProcessName) '$($proc.MainWindowTitle)' ${w}x${hgt} -> $full"
