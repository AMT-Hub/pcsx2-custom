param([ValidateSet('Prepare','Restore')][string]$Action='Prepare')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$kit=$PSScriptRoot
$root=Split-Path (Split-Path $kit -Parent) -Parent
$lock=$null
try {
    if ((Split-Path $root -Leaf) -cne 'PCSX2-Nightly-Test') { throw 'Use a separate COPY of your installation named exactly PCSX2-Nightly-Test. Do not run this in your working installation.' }
    foreach($name in @('Custom-PCSX2.exe','PCSX2-Update.exe','portable.txt','custom-pcsx2/updater/Engine.ps1')) {
        if(!(Test-Path -LiteralPath (Join-Path $root $name) -PathType Leaf)){throw "Missing existing installation file: $name. Copy the full working custom nightly installation first."}
    }
    . (Join-Path $root 'custom-pcsx2/updater/Engine.ps1')
    Initialize-Updater $root
    Assert-PlainPath $kit
    $lock=Acquire-UpdateLock
    Assert-NotRunning
    $legacy=Join-Path $root 'custom-pcsx2/shader-prototype'
    $backup=Join-Path $kit 'original-runtime'
    $stage=Join-Path $kit 'staged-runtime'
    $state=Join-Path $kit 'test-state.json'
    $active=Join-Path $root 'custom-pcsx2/updater/active.txt'
    $metadata=Get-Content -LiteralPath (Join-Path $kit 'TEST-INFO.json') -Raw | ConvertFrom-Json
    if($Action -eq 'Restore') {
        if(!(Test-Path -LiteralPath $state)){throw 'No prepared test is recorded in this copy.'}
        $saved=Get-Content -LiteralPath $state -Raw | ConvertFrom-Json
        if(Test-Path -LiteralPath $backup) {
            Assert-PlainPath $backup
            if(Test-Path -LiteralPath $legacy) {
                Assert-PlainPath $legacy
                $retained=Join-Path $kit ('tested-runtime-'+[guid]::NewGuid().ToString('N'))
                [IO.Directory]::Move($legacy,$retained)
            }
            [IO.Directory]::Move($backup,$legacy)
        } elseif($saved.prepared) {throw 'Original runtime backup is missing; nothing was changed.'}
        if($saved.hadSelection) {
            [IO.File]::WriteAllBytes($active,[Convert]::FromBase64String($saved.selectionBase64))
        } elseif(Test-Path -LiteralPath $active) {
            Remove-Item -LiteralPath $active
        }
        Move-Item -LiteralPath $state -Destination (Join-Path $kit ('restored-'+[guid]::NewGuid().ToString('N')+'.json'))
        Write-Host 'RESTORED: original runtime and selection. Settings/saves in this test copy are retained.'
    } else {
        if((Test-Path -LiteralPath $state) -or (Test-Path -LiteralPath $backup)){throw 'A test/backup already exists. Run Restore-Nightly-Test.cmd before preparing again.'}
        if(!(Test-Path -LiteralPath $legacy -PathType Container)){throw 'Original shader-prototype runtime is missing.'}
        Assert-PlainPath $legacy
        foreach($item in @($metadata.requires.PSObject.Properties)) {
            Assert-RelativeName $item.Name
            if(!$item.Name.StartsWith('ShaderGlass/')){throw 'Unexpected test dependency.'}
            $file=Join-Path $root $item.Name
            Assert-PlainPath $file
            if(!(Test-Path -LiteralPath $file) -or (File-Hash $file) -cne $item.Value){throw "Shader component does not match the accepted baseline: $($item.Name)"}
        }
        $archive=Join-Path $kit 'runtime.zip'
        if((File-Hash $archive) -cne $metadata.runtimeZipSha256){throw 'Runtime ZIP hash does not match the downloaded GitHub build.'}
        $hashFile=Join-Path $kit 'runtime-hashes.json'
        if((File-Hash $hashFile) -cne $metadata.hashListSha256){throw 'Runtime hash list was changed.'}
        $hashes=Get-Content -LiteralPath $hashFile -Raw | ConvertFrom-Json
        $expected=@($hashes.PSObject.Properties.Name)
        if(Test-Path -LiteralPath $stage){throw 'A staging folder already exists. Preserve or remove only nightly-test-2.9.127/staged-runtime, then retry.'}
        $zip=[IO.Compression.ZipFile]::OpenRead($archive)
        try {
            $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
            [long]$total=0
            foreach($entry in $zip.Entries) {
                Assert-RelativeName $entry.FullName
                if(!$seen.Add($entry.FullName) -or $expected -cnotcontains $entry.FullName){throw 'Unexpected or duplicate runtime entry.'}
                $total+=$entry.Length
                if($total -gt 1073741824){throw 'Runtime is larger than expected.'}
            }
            if($seen.Count -ne $expected.Count){throw 'Runtime has missing files.'}
            [void][IO.Directory]::CreateDirectory($stage)
            foreach($entry in $zip.Entries) {
                $out=Join-Path $stage $entry.FullName
                [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($out))
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$out,$false)
            }
        } finally {$zip.Dispose()}
        foreach($item in @($hashes.PSObject.Properties)) {
            if((File-Hash (Join-Path $stage $item.Name)) -cne $item.Value){throw "Extracted runtime hash mismatch: $($item.Name)"}
        }
        if([IO.File]::ReadAllText((Join-Path $stage 'portable.txt')).Trim() -cne '../../..'){throw 'Unexpected candidate portable data path.'}
        # The disposable legacy test folder is two levels below its portable root.
        [IO.File]::WriteAllText((Join-Path $stage 'portable.txt'),"../..`r`n",[Text.Encoding]::ASCII)
        $had=Test-Path -LiteralPath $active
        $bytes=''
        if($had){$bytes=[Convert]::ToBase64String([IO.File]::ReadAllBytes($active))}
        $saved=@{prepared=$false;hadSelection=$had;selectionBase64=$bytes;run=$metadata.run}
        $saved | ConvertTo-Json | Set-Content -LiteralPath $state -Encoding UTF8
        [IO.Directory]::Move($legacy,$backup)
        [IO.Directory]::Move($stage,$legacy)
        Write-Selection 'legacy' ''
        $saved.prepared=$true
        $saved | ConvertTo-Json | Set-Content -LiteralPath $state -Encoding UTF8
        Write-Host 'READY: launch Custom-PCSX2.exe from this PCSX2-Nightly-Test copy.'
        Write-Host 'This is an unsigned gameplay test. Use Restore-Nightly-Test.cmd before using the updater in this copy.'
    }
} catch {
    Write-Host ('TEST SETUP STOPPED: '+$_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {if($lock){$lock.Dispose()}}
