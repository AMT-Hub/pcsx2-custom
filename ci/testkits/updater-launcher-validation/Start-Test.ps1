Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
try {
    $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    if((Split-Path $root -Leaf) -ine 'PCSX2-Nightly-Test') {
        throw 'Run this test only in a separate COPY of your custom nightly installation named PCSX2-Nightly-Test. Your working installation should stay unchanged.'
    }
    foreach($name in @('portable.txt','PCSX2-Update.exe','custom-pcsx2/updater/Engine.ps1','custom-pcsx2/updater/Updater.ps1','custom-pcsx2/updater/public-key.xml')) {
        if(!(Test-Path -LiteralPath (Join-Path $root $name) -PathType Leaf)) {
            throw "Missing existing installation file: $name. Extract the test ZIP into a complete copy of the accepted custom nightly installation."
        }
    }
    & (Join-Path $PSScriptRoot 'Updater.ps1')
} catch {
    [void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'PCSX2 Launcher Validation Test','OK','Error')
    exit 1
}
