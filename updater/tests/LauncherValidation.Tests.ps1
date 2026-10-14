param([Parameter(Mandatory=$true)][string]$AcceptedLauncher)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$source=Split-Path $PSScriptRoot -Parent
foreach($name in @('Engine.ps1','Feed.ps1','Updater.ps1')) {
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $source $name),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw ($errors | Out-String)}
}
. (Join-Path $source 'Engine.ps1')
. (Join-Path $source 'Feed.ps1')
$acceptedBytes=[IO.File]::ReadAllBytes($AcceptedLauncher)
if((File-Hash $AcceptedLauncher) -cne '4fab61885b8aa0fa413255b5d1927d6a785ef52e99e68203dc52d08828f147f9'){throw 'Wrong accepted launcher test input.'}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('pcsx2 launcher validation '+[guid]::NewGuid().ToString('N'))
$install=Join-Path $temp ('Portable '+[char]0x00e9)
$packages=Join-Path $temp 'packages'
$rsa=New-Object Security.Cryptography.RSACryptoServiceProvider(2048)
$rsa.PersistKeyInCsp=$false
$script:Passed=0
function Check([bool]$Condition,[string]$Name) {
    if(!$Condition){throw "FAILED: $Name"};$script:Passed++;Write-Host "PASS: $Name"
}
function Expect-Blocked([scriptblock]$Action,[string]$Pattern,[string]$Name) {
    $message=''
    try { & $Action | Out-Null } catch { $message=$_.Exception.Message }
    Check ($message -like $Pattern) "$Name ($message)"
}
function Restore-Launcher { [IO.File]::WriteAllBytes((Join-Path $install 'Custom-PCSX2.exe'),$acceptedBytes) }
function Snapshot-Portable {
    $rows=@(Get-ChildItem -LiteralPath $install -Recurse -File | Where-Object { $_.Name -ne 'runtime.lock' } | Sort-Object FullName | ForEach-Object {
        $_.FullName.Substring($install.Length)+':'+(File-Hash $_.FullName)
    })
    return ($rows -join "`n")
}
function Make-Package([string]$Id,[string]$Version) {
    $stage=Join-Path $packages $Id
    $runtime=Join-Path $stage 'runtime'
    [void][IO.Directory]::CreateDirectory((Join-Path $runtime 'custom-pcsx2'))
    [void][IO.Directory]::CreateDirectory((Join-Path $runtime 'resources'))
    $files=[ordered]@{}
    foreach($name in @('PCSX2-ShaderPrototype.exe','portable.txt','custom-pcsx2/auto-bios.enabled','custom-pcsx2/bios-catalogue.tsv','custom-pcsx2/bios-rules.tsv','resources/patches.zip')) {
        $content="fixture $Id $name";if($name -eq 'portable.txt'){$content='../../..'}
        $path=Join-Path $runtime $name
        [IO.File]::WriteAllText($path,$content)
        $files[$name]=@{size=(Get-Item -LiteralPath $path).Length;sha256=(File-Hash $path)}
    }
    $m=@{schema=1;product='CustomPCSX2';channel='approved';data_schema=1;id=$Id;label="Fixture custom PCSX2 $Version";features=@('auto-bios','shaderglass','sorting-title');requires=@{};files=$files}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($m | ConvertTo-Json -Depth 12 -Compress))
    [IO.File]::WriteAllBytes((Join-Path $stage 'manifest.json'),$bytes)
    [IO.File]::WriteAllBytes((Join-Path $stage 'manifest.sig'),$rsa.SignData($bytes,[Security.Cryptography.CryptoConfig]::MapNameToOID('SHA256')))
    $zip=Join-Path $packages ($Id+'.zip')
    [IO.Compression.ZipFile]::CreateFromDirectory($stage,$zip)
    return $zip
}
try {
    Initialize-Updater $install
    [void][IO.Directory]::CreateDirectory($packages)
    [IO.File]::WriteAllText((Join-Path $script:Control 'public-key.xml'),$rsa.ToXmlString($false))
    foreach($folder in @('inis','gamesettings','inputprofiles','bios','memcards','sstates')) {
        [void][IO.Directory]::CreateDirectory((Join-Path $install $folder))
        [IO.File]::WriteAllText((Join-Path $install ($folder+'/keep.txt')),'unchanged fixture')
    }
    [IO.File]::WriteAllText((Join-Path $install 'pcsx2-qt.exe'),'untouched official executable fixture')
    Restore-Launcher
    Check ((Get-LauncherStatus).Compatible) 'Accepted launcher allowed without executing it'
    $handle=Open-CompatibleLauncher
    try {
        Expect-Blocked { [IO.File]::WriteAllText((Join-Path $install 'Custom-PCSX2.exe'),'changed') } '*used by another process*' 'Verified launcher cannot be overwritten while held'
        Expect-Blocked { [IO.File]::Delete((Join-Path $install 'Custom-PCSX2.exe')) } '*used by another process*' 'Verified launcher cannot be deleted while held'
    } finally { $handle.Dispose() }
    Restore-Launcher
    $a=Make-Package 'nightly-2_9_126-fixture-a' '2.9.126'
    $b=Make-Package 'nightly-2_9_127-fixture-b' '2.9.127'
    $script:NetworkCalls=0;$script:ChangeLauncherDuringDownload=$false
    # Network fixture only. Real signature, package, hash, state and rollback code.
    function Receive-Https([string]$Url,[string]$Destination,[long]$Limit) {
        $script:NetworkCalls++
        if($Url -eq 'https://fixtures.invalid/feed.json'){[IO.File]::Copy($script:FixtureFeed,$Destination)}
        elseif($Url -eq 'https://fixtures.invalid/package.zip'){
            [IO.File]::Copy($b,$Destination)
            if($script:ChangeLauncherDuringDownload){[IO.File]::WriteAllText((Join-Path $install 'Custom-PCSX2.exe'),'replaced during download')}
        }else{throw 'Unexpected network call in tests.'}
    }
    foreach($kind in @('missing','unrecognised')) {
        if($kind -eq 'missing'){[IO.File]::Delete((Join-Path $install 'Custom-PCSX2.exe'))}
        else{[IO.File]::WriteAllText((Join-Path $install 'Custom-PCSX2.exe'),'MZ unrecognised launcher')}
        Check (!(Get-LauncherStatus).Compatible) "$kind launcher is reported as blocked"
        $before=Snapshot-Portable
        Expect-Blocked { Install-Package $a } 'Launcher validation blocked*' "$kind launcher blocks local install"
        Expect-Blocked { Rollback-Runtime } 'Launcher validation blocked*' "$kind launcher blocks rollback"
        Expect-Blocked { Install-FromFeed 'https://fixtures.invalid/feed.json' 'id' 'hash' } 'Launcher validation blocked*' "$kind launcher blocks online install"
        Check ($script:NetworkCalls -eq 0) "$kind launcher blocked before network access"
        Check ((Snapshot-Portable) -ceq $before) "$kind rejection preserves selection, payloads and portable data"
    }
    Restore-Launcher
    Install-Package $a | Out-Host
    Check ((Read-Selection).Current -ceq 'nightly-2_9_126-fixture-a') 'Accepted launcher installs signed runtime A'
    Install-Package $b | Out-Host
    Check ((Read-Selection).Current -ceq 'nightly-2_9_127-fixture-b') 'Accepted launcher installs signed runtime B'
    Check ((Get-RuntimeDisplayName (Read-Selection).Current) -ceq 'PCSX2 2.9.127 (nightly-2_9_127-fixture-b)') 'Selected custom version displayed clearly'
    Check ((Get-RuntimeDisplayName 'legacy') -ceq 'PCSX2 2.9.126 (original custom runtime)') 'Legacy label is readable'
    Check ((Get-RuntimeDisplayName 'nightly-2_9_999-missing') -like '*metadata unavailable*') 'Missing metadata is not presented as a verified version'
    Rollback-Runtime | Out-Host
    Check ((Read-Selection).Current -ceq 'nightly-2_9_126-fixture-a') 'Rollback selects A'
    $feed=@{schema=1;product='CustomPCSX2';channel='approved';sequence=1;expiresUtc=[DateTimeOffset]::UtcNow.AddDays(1).ToString('o');release=@{id='nightly-2_9_127-fixture-b';label='Fixture 2.9.127';bytes=(Get-Item $b).Length;sha256=(File-Hash $b);url='https://fixtures.invalid/package.zip'}}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($feed | ConvertTo-Json -Depth 8 -Compress))
    $envelope=@{payload=[Convert]::ToBase64String($bytes);signature=[Convert]::ToBase64String($rsa.SignData($bytes,[Security.Cryptography.CryptoConfig]::MapNameToOID('SHA256')))}
    $script:FixtureFeed=Join-Path $packages 'feed.json'
    [IO.File]::WriteAllText($script:FixtureFeed,($envelope | ConvertTo-Json -Compress))
    [IO.File]::Delete((Join-Path $install 'Custom-PCSX2.exe'))
    $null=Check-Feed 'https://fixtures.invalid/feed.json'
    Check ($script:NetworkCalls -eq 1) 'Read-only feed check remains available with missing launcher'
    $before=Snapshot-Portable
    Expect-Blocked { Rollback-Runtime } 'Launcher validation blocked*' 'Missing launcher blocks rollback when a real previous runtime exists'
    Check ((Snapshot-Portable) -ceq $before) 'Blocked rollback leaves installed runtimes and portable data intact'
    Restore-Launcher
    $script:ChangeLauncherDuringDownload=$true
    Expect-Blocked { Install-FromFeed 'https://fixtures.invalid/feed.json' $feed.release.id $feed.release.sha256 } 'Launcher validation blocked*' 'Launcher changed during download is rejected by install engine'
    Check ((Read-Selection).Current -ceq 'nightly-2_9_126-fixture-a') 'Rejected download does not change selection'
    Check (@(Get-ChildItem -LiteralPath $script:Control -Filter 'download-*.zip').Count -eq 0) 'Rejected download is cleaned up'
    $script:ChangeLauncherDuringDownload=$false;Restore-Launcher
    Install-FromFeed 'https://fixtures.invalid/feed.json' $feed.release.id $feed.release.sha256 | Out-Host
    Check ((Read-Selection).Current -ceq 'nightly-2_9_127-fixture-b') 'Online install still works after launcher restoration'
    Rollback-Runtime | Out-Host
    Check ((Read-Selection).Current -ceq 'nightly-2_9_126-fixture-a') 'Rollback still works after online install'
    Check ([IO.File]::ReadAllText((Join-Path $install 'pcsx2-qt.exe')) -ceq 'untouched official executable fixture') 'Official EXE is untouched'
    foreach($folder in @('inis','gamesettings','inputprofiles','bios','memcards','sstates')) {
        Check ([IO.File]::ReadAllText((Join-Path $install ($folder+'/keep.txt'))) -ceq 'unchanged fixture') "$folder contents retained"
    }
    Write-Host "SUCCESS: $script:Passed launcher validation checks passed on PowerShell $($PSVersionTable.PSVersion)."
} finally {
    $rsa.Dispose()
    if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}
}
