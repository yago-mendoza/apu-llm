"""What machine this is: recorded next to every benchmark so results from different laptops compare."""

import json
import os
import platform
import subprocess

_PS = r"""
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpu = Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
$mem = Get-CimInstance Win32_PhysicalMemory
$os  = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
  vendor = $cs.Manufacturer; model = $cs.Model
  cpu = $cpu.Name.Trim(); cores = $cpu.NumberOfCores; threads = $cpu.NumberOfLogicalProcessors
  gpus = @($gpu | ForEach-Object { "$($_.Name) (driver $($_.DriverVersion))" })
  ram_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
  ram_free_gb = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
  ram_modules = @($mem).Count
  ram_mts = ($mem | Select-Object -First 1).ConfiguredClockSpeed
  os = "$($os.Caption) $($os.Version)"
} | ConvertTo-Json -Compress
"""


def info() -> dict:
    if platform.system() == "Windows":
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", _PS],
                                 capture_output=True, text=True, timeout=30, check=True).stdout
            return json.loads(out)
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass
    return {"cpu": platform.processor() or platform.machine(), "threads": os.cpu_count(),
            "os": f"{platform.system()} {platform.release()}"}


def free_ram_gb() -> float | None:
    if platform.system() == "Windows":
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / 2**30
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 2**20
    except OSError:
        pass
    return None
