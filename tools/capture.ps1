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
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    // Every visible top-level window whose title contains `part`. Needed because one process can own
    // several windows (Windows Terminal), and Process.MainWindowHandle only names one of them.
    public static System.Collections.Generic.List<IntPtr> Find(string part) {
        var found = new System.Collections.Generic.List<IntPtr>();
        EnumWindows((h, l) => {
            if (!IsWindowVisible(h)) return true;
            var sb = new System.Text.StringBuilder(512);
            GetWindowText(h, sb, 512);
            if (sb.ToString().IndexOf(part, StringComparison.OrdinalIgnoreCase) >= 0) found.Add(h);
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@
Add-Type -AssemblyName System.Drawing
[Win]::SetProcessDPIAware() | Out-Null

if ($Process) {
    $proc = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$Title*" -and $_.ProcessName -eq $Process } | Select-Object -First 1
    if (-not $proc) { throw "No $Process window whose title contains '$Title'" }
    $h = $proc.MainWindowHandle
} else {
    $h = [Win]::Find($Title) | Select-Object -First 1
    if (-not $h) { throw "No window whose title contains '$Title'" }
    $proc = [pscustomobject]@{ ProcessName = 'window'; MainWindowTitle = $Title }
}
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
