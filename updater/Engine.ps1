# Windows PowerShell 5.1-compatible updater engine. No UI or network operations.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Assert-PlainPath([string]$Path) {
    $p = [IO.Path]::GetFullPath($Path)
    while ($p) {
        if (Test-Path -LiteralPath $p) {
            if ((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked folders/files are not supported for updates: $p"
            }
        }
        $parent = [IO.Path]::GetDirectoryName($p)
        if ($parent -eq $p) { break }; $p = $parent
    }
}
function Initialize-Updater([string]$Root) {
    $script:Root = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar)
    Assert-PlainPath $script:Root
    $script:Control = Join-Path $script:Root 'custom-pcsx2/updater'
    $script:Runtimes = Join-Path $script:Root 'custom-pcsx2/runtimes'
    foreach ($p in @($script:Control,$script:Runtimes)) {
        Assert-PlainPath $p; [void][IO.Directory]::CreateDirectory($p)
    }
}
function File-Hash([string]$Path) {
    $s = [IO.File]::OpenRead($Path); $h = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($h.ComputeHash($s))).Replace('-','').ToLowerInvariant() }
    finally { $s.Dispose(); $h.Dispose() }
}
function Open-CompatibleLauncher {
    # Exact accepted bytes, not a filename/version-string heuristic. Do not execute
    # an unrecognised launcher to discover its capabilities. Add future builds only
    # after their runtime-selection behaviour has been reviewed and accepted.
    $expected='4fab61885b8aa0fa413255b5d1927d6a785ef52e99e68203dc52d08828f147f9'
    $path=Join-Path $script:Root 'Custom-PCSX2.exe'
    $stream=$null
    try {
        Assert-PlainPath $path
        if (![IO.File]::Exists($path)) { throw 'Custom-PCSX2.exe is missing.' }
        # Hold this read handle throughout a state-changing operation on Windows:
        # another process cannot replace/delete/write the verified EXE meanwhile.
        $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $sha=[Security.Cryptography.SHA256]::Create()
        try { $actual=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
        finally { $sha.Dispose() }
        if ($actual -cne $expected) { throw 'Custom-PCSX2.exe is not the accepted updater-compatible launcher. An older launcher can ignore the selected version.' }
        return $stream
    } catch {
        if ($stream) { $stream.Dispose() }
        throw ("Launcher validation blocked the operation. "+$_.Exception.Message+"`r`nInstallation: "+$script:Root+"`r`nClose PCSX2 and this updater. Restore the tested Custom-PCSX2.exe, or back up the existing EXE and extract PCSX2-Updater-Launcher-Repair-test1.zip from the approved GitHub release into this folder. Reopen the updater afterwards. Do not substitute pcsx2-qt.exe.")
    }
}
function Assert-CompatibleLauncher {
    $handle=Open-CompatibleLauncher
    $handle.Dispose()
}
function Get-LauncherStatus {
    try {
        Assert-CompatibleLauncher
        return [pscustomobject]@{ Compatible=$true; Message='Launcher: compatible (accepted Custom-PCSX2.exe).' }
    } catch {
        return [pscustomobject]@{ Compatible=$false; Message=$_.Exception.Message }
    }
}
function Get-RuntimeDisplayName([string]$Id) {
    if (!$Id) { return 'None' }
    if ($Id -ceq 'legacy') { return 'PCSX2 2.9.126 (original custom runtime)' }
    try {
        if (!(Valid-Id $Id)) { throw 'Invalid runtime identifier.' }
        $dir=Join-Path $script:Runtimes $Id; Assert-PlainPath $dir
        foreach ($file in @('.release-manifest.json','.release-signature.bin','PCSX2-ShaderPrototype.exe')) {
            $path=Join-Path $dir $file; Assert-PlainPath $path
            if (![IO.File]::Exists($path)) { throw 'Missing runtime file.' }
        }
        $m=Read-Release ([IO.File]::ReadAllBytes((Join-Path $dir '.release-manifest.json'))) ([IO.File]::ReadAllBytes((Join-Path $dir '.release-signature.bin')))
        if ($m.id -cne $Id) { throw 'Runtime identity mismatch.' }
        # This is a selection label, not a claim that the emulator is running.
        # Full payload verification remains in install and rollback.
        if ($Id -cmatch '^nightly-([0-9]+)_([0-9]+)_([0-9]+)(-|$)') {
            return "PCSX2 $($Matches[1]).$($Matches[2]).$($Matches[3]) ($Id)"
        }
        return [string]$m.label
    } catch { return "$Id (runtime metadata unavailable)" }
}
function Valid-Id([string]$Id) { return ($Id -cmatch '^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$') }
function Read-Selection {
    $p = Join-Path $script:Control 'active.txt'; Assert-PlainPath $p
    if (!(Test-Path -LiteralPath $p)) { return @{ Current='legacy'; Previous='' } }
    $lines = [IO.File]::ReadAllLines($p)
    if ($lines.Count -lt 1 -or $lines.Count -gt 2 -or !(Valid-Id $lines[0])) { throw 'Invalid runtime selection file.' }
    $previous = ''; if ($lines.Count -eq 2) { $previous = $lines[1] }
    if ($previous -and !(Valid-Id $previous)) { throw 'Invalid previous runtime identifier.' }
    return @{ Current=$lines[0]; Previous=$previous }
}
function Write-Selection([string]$Current,[string]$Previous) {
    if (!(Valid-Id $Current) -or ($Previous -and !(Valid-Id $Previous))) { throw 'Invalid runtime identifier.' }
    $p=Join-Path $script:Control 'active.txt'; Assert-PlainPath $p
    $tmp=Join-Path $script:Control ('selection-'+[guid]::NewGuid().ToString('N')+'.tmp')
    $bytes=[Text.Encoding]::ASCII.GetBytes($Current+"`n"+$Previous+"`n")
    $f=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $f.Write($bytes,0,$bytes.Length); $f.Flush($true) } finally { $f.Dispose() }
    try {
        if ([IO.File]::Exists($p)) { [IO.File]::Replace($tmp,$p,($tmp+'.old')) }
        else { [IO.File]::Move($tmp,$p) }
    } finally { if ([IO.File]::Exists($tmp)) { [IO.File]::Delete($tmp) }; if ([IO.File]::Exists($tmp+'.old')) { [IO.File]::Delete($tmp+'.old') } }
}
function Acquire-UpdateLock {
    $p=Join-Path $script:Root 'custom-pcsx2/runtime.lock'; Assert-PlainPath $p
    try { return [IO.File]::Open($p,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch { throw 'Close PCSX2 and any other updater window before continuing.' }
}
function Assert-NotRunning {
    # Catch direct launches which bypass the cooperating launcher lock.
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { return }
    foreach ($p in @(Get-Process -Name 'PCSX2-ShaderPrototype','pcsx2-qt' -ErrorAction SilentlyContinue)) {
        try { $path=$p.MainModule.FileName }
        catch { throw 'An emulator process is running and could not be checked. Close it first.' }
        if ($path -and $path.StartsWith($script:Root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
            throw 'Close all PCSX2 windows in this installation before updating or rolling back.'
        }
    }
}
function Read-Release([byte[]]$Bytes,[byte[]]$Signature) {
    if ($Bytes.Length -gt 1048576 -or $Signature.Length -gt 4096) { throw 'Release metadata is too large.' }
    $rsa=New-Object Security.Cryptography.RSACryptoServiceProvider
    try {
        $rsa.PersistKeyInCsp=$false
        $rsa.FromXmlString([IO.File]::ReadAllText((Join-Path $script:Control 'public-key.xml')))
        if (!$rsa.VerifyData($Bytes,[Security.Cryptography.CryptoConfig]::MapNameToOID('SHA256'),$Signature)) { throw 'Package signature is invalid. Nothing was installed.' }
    } finally { $rsa.Dispose() }
    $m=[Text.Encoding]::UTF8.GetString($Bytes) | ConvertFrom-Json
    if ($m.schema -ne 1 -or $m.product -cne 'CustomPCSX2' -or $m.channel -cne 'approved' -or $m.data_schema -ne 1) {
        throw 'This package is not approved for this updater/data format.'
    }
    if (!(Valid-Id $m.id) -or $m.id -eq 'legacy') { throw 'Invalid release identifier.' }
    if ($m.features -notcontains 'auto-bios' -or $m.features -notcontains 'shaderglass' -or $m.features -notcontains 'sorting-title') { throw 'Package lacks required custom features.' }
    $props=@($m.files.PSObject.Properties)
    if ($props.Count -lt 3 -or $props.Count -gt 4000) { throw 'Invalid runtime file list.' }
    [long]$total=0
    foreach ($f in $props) {
        Assert-RelativeName $f.Name
        if ($f.Name.StartsWith('.') -or $f.Name -match '(^|/)(bios|memcards|sstates|inis|gamesettings|inputprofiles)(/|$)') { throw 'Package contains user-data paths.' }
        if ($f.Value.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $f.Value.size -lt 0 -or $f.Value.size -gt 268435456) { throw 'Invalid file metadata.' }
        $total += [long]$f.Value.size
    }
    if ($total -gt 1073741824) { throw 'Runtime exceeds the supported size.' }
    foreach ($name in @('PCSX2-ShaderPrototype.exe','portable.txt','custom-pcsx2/auto-bios.enabled','custom-pcsx2/bios-catalogue.tsv','custom-pcsx2/bios-rules.tsv','resources/patches.zip')) {
        if ($m.files.PSObject.Properties.Name -cnotcontains $name) { throw "Package is incomplete: $name" }
    }
    return $m
}
function Assert-RelativeName([string]$Name) {
    if (!$Name -or $Name.Length -gt 220 -or $Name -match '[\\:<>"|?*\x00-\x1f]' -or $Name.StartsWith('/') -or $Name.EndsWith('/')) { throw "Unsafe package path: $Name" }
    foreach ($part in $Name.Split('/')) {
        if (!$part -or $part -eq '.' -or $part -eq '..' -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)') { throw "Unsafe package path: $Name" }
    }
}
function Assert-Requirements($Manifest) {
    foreach ($f in @($Manifest.requires.PSObject.Properties)) {
        Assert-RelativeName $f.Name
        if (!$f.Name.StartsWith('ShaderGlass/')) { throw 'Unexpected package requirement.' }
        $p=Join-Path $script:Root $f.Name; Assert-PlainPath $p
        if (!(Test-Path -LiteralPath $p) -or (File-Hash $p) -cne $f.Value) { throw "This package requires a different installed shader component: $($f.Name)" }
    }
}
function Assert-Runtime([string]$Directory,$Manifest) {
    Assert-PlainPath $Directory
    foreach ($f in @($Manifest.files.PSObject.Properties)) {
        $p=Join-Path $Directory $f.Name; Assert-PlainPath $p
        if (!(Test-Path -LiteralPath $p -PathType Leaf) -or (Get-Item -LiteralPath $p).Length -ne $f.Value.size -or (File-Hash $p) -cne $f.Value.sha256) {
            throw "Runtime verification failed: $($f.Name)"
        }
    }
    $expected=@($Manifest.files.PSObject.Properties.Name)+@('.release-manifest.json','.release-signature.bin')
    foreach ($f in @(Get-ChildItem -LiteralPath $Directory -File -Recurse -Force)) {
        $rel=$f.FullName.Substring($Directory.Length+1).Replace('\','/')
        if ($expected -cnotcontains $rel) { throw "Unexpected runtime file: $rel" }
    }
    if ([IO.File]::ReadAllText((Join-Path $Directory 'portable.txt')).Trim() -cne '../../..') { throw 'Runtime does not point to the portable data folder.' }
}
function Snapshot-Settings([string]$From,[string]$To) {
    $name=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N')
    $dest=Join-Path $script:Control ('backups/'+$name)
    Assert-PlainPath $dest; [void][IO.Directory]::CreateDirectory($dest)
    foreach ($folder in @('inis','gamesettings','inputprofiles')) {
        $src=Join-Path $script:Root $folder
        if (Test-Path -LiteralPath $src) {
            Assert-PlainPath $src
            foreach ($item in @(Get-ChildItem -LiteralPath $src -Recurse -Force)) { Assert-PlainPath $item.FullName }
            Copy-Item -LiteralPath $src -Destination $dest -Recurse
        }
    }
    [IO.File]::WriteAllText((Join-Path $dest 'transition.txt'),"$From -> $To`r`nSettings snapshot only; no memory cards or save states copied.")
    return $dest
}
function Read-Installed([string]$Id) {
    if (!(Valid-Id $Id) -or $Id -eq 'legacy') { throw 'Invalid installed release.' }
    $dir=Join-Path $script:Runtimes $Id; Assert-PlainPath $dir
    $m=Read-Release ([IO.File]::ReadAllBytes((Join-Path $dir '.release-manifest.json'))) ([IO.File]::ReadAllBytes((Join-Path $dir '.release-signature.bin')))
    if ($m.id -cne $Id) { throw 'Installed release identity mismatch.' }
    Assert-Requirements $m; Assert-Runtime $dir $m
    return $m
}
function Install-Package([string]$Package) {
    $lock=Acquire-UpdateLock; $archive=$null; $stream=$null; $stage=$null; $launcher=$null
    try {
        Assert-NotRunning; $launcher=Open-CompatibleLauncher; $state=Read-Selection
        $stream=[IO.File]::Open($Package,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ($stream.Length -gt 1073741824) { throw 'Package is too large.' }
        $archive=New-Object IO.Compression.ZipArchive($stream,[IO.Compression.ZipArchiveMode]::Read,$true)
        $entries=New-Object 'System.Collections.Generic.Dictionary[string,System.IO.Compression.ZipArchiveEntry]' ([StringComparer]::OrdinalIgnoreCase)
        foreach ($entry in $archive.Entries) {
            Assert-RelativeName $entry.FullName
            if ($entries.ContainsKey($entry.FullName)) { throw 'Duplicate package entries.' }
            $entries.Add($entry.FullName,$entry)
        }
        foreach ($n in @('manifest.json','manifest.sig')) { if (!$entries.ContainsKey($n)) { throw 'This is not a signed custom update package.' } }
        if ($entries['manifest.json'].Length -gt 1048576 -or $entries['manifest.sig'].Length -gt 4096) { throw 'Invalid metadata size.' }
        $ms=New-Object IO.MemoryStream; $s=$entries['manifest.json'].Open()
        try {$s.CopyTo($ms);$bytes=$ms.ToArray()}finally{$s.Dispose();$ms.Dispose()}
        $ms=New-Object IO.MemoryStream; $s=$entries['manifest.sig'].Open()
        try {$s.CopyTo($ms);$sig=$ms.ToArray()}finally{$s.Dispose();$ms.Dispose()}
        $m=Read-Release $bytes $sig; Assert-Requirements $m
        if ($state.Current -ceq $m.id) { throw 'This release is already selected.' }
        $props=@($m.files.PSObject.Properties)
        if ($entries.Count -ne $props.Count+2) { throw 'Package contains missing or extra files.' }
        foreach ($f in $props) {
            $n='runtime/'+$f.Name
            if (!$entries.ContainsKey($n) -or $entries[$n].FullName -cne $n -or $entries[$n].Length -ne $f.Value.size) { throw "Package entry mismatch: $n" }
        }
        $stage=Join-Path $script:Runtimes ('.staging-'+[guid]::NewGuid().ToString('N'))
        Assert-PlainPath $stage; [void][IO.Directory]::CreateDirectory($stage)
        foreach ($f in $props) {
            $out=Join-Path $stage $f.Name; [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($out))
            $src=$entries['runtime/'+$f.Name].Open()
            $dst=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try { $src.CopyTo($dst) } finally { $src.Dispose();$dst.Dispose() }
        }
        [IO.File]::WriteAllBytes((Join-Path $stage '.release-manifest.json'),$bytes)
        [IO.File]::WriteAllBytes((Join-Path $stage '.release-signature.bin'),$sig)
        Assert-Runtime $stage $m
        $target=Join-Path $script:Runtimes $m.id; Assert-PlainPath $target
        if (Test-Path -LiteralPath $target) {
            $existing=Read-Installed $m.id
            if ((File-Hash (Join-Path $target '.release-manifest.json')) -cne (File-Hash (Join-Path $stage '.release-manifest.json'))) { throw 'A different release already uses this identifier.' }
        } else { [IO.Directory]::Move($stage,$target); $stage=$null }
        $backup=Snapshot-Settings $state.Current $m.id
        Write-Selection $m.id $state.Current
        return "Selected $($m.label). Previous runtime retained. Settings backup: $backup"
    } finally {
        if ($archive) {$archive.Dispose()}; if ($stream) {$stream.Dispose()}
        if ($stage -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage -Recurse -Force }
        if ($launcher) { $launcher.Dispose() }
        $lock.Dispose()
    }
}
function Rollback-Runtime {
    $lock=Acquire-UpdateLock; $launcher=$null
    try {
        Assert-NotRunning; $launcher=Open-CompatibleLauncher; $state=Read-Selection; $prev=$state.Previous
        if (!$prev) { throw 'No previous runtime has been recorded.' }
        if ($prev -eq 'legacy') {
            $p=Join-Path $script:Root 'custom-pcsx2/shader-prototype/PCSX2-ShaderPrototype.exe'; Assert-PlainPath $p
            if ((File-Hash $p) -cne '8dd5588d650a75be428ef25571d2fe0b94a58202c766729f2b4d4b8a35ea420d') { throw 'Original nightly runtime differs from the accepted baseline.' }
        } else { $null=Read-Installed $prev }
        $backup=Snapshot-Settings $state.Current $prev
        Write-Selection $prev $state.Current
        return "Selected previous runtime ($prev). Your current settings and saves are unchanged. Backup: $backup"
    } finally { if ($launcher) { $launcher.Dispose() }; $lock.Dispose() }
}
