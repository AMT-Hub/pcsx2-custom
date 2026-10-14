Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
try {
 . (Join-Path $PSScriptRoot 'Engine.ps1')
 . (Join-Path $PSScriptRoot 'Feed.ps1')
 Initialize-Updater ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')))
 $baseline=Join-Path $script:Root 'custom-pcsx2/shader-prototype/PCSX2-ShaderPrototype.exe'
 if (!(Test-Path -LiteralPath $baseline) -or (File-Hash $baseline) -ne '8dd5588d650a75be428ef25571d2fe0b94a58202c766729f2b4d4b8a35ea420d'){throw 'This test requires your accepted custom nightly 2.9.126 installation and controlled updater.'}
 $script:Job=$null;$script:Available=$null
 $form=New-Object Windows.Forms.Form;$form.Text='PCSX2 Controlled Updater 0.2.0 - feed test'
 $form.ClientSize=New-Object Drawing.Size(720,490);$form.StartPosition='CenterScreen';$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false
 $form.Font=New-Object Drawing.Font('Segoe UI',10)
 $form.Icon=[Drawing.Icon]::ExtractAssociatedIcon((Join-Path $script:Root 'PCSX2-Update.exe'))
 $heading=New-Object Windows.Forms.Label;$heading.SetBounds(20,16,680,25);$heading.Text='Approved custom builds only. Official PCSX2 updates remain disabled.';$form.Controls.Add($heading)
 $status=New-Object Windows.Forms.Label;$status.SetBounds(20,50,680,45);$form.Controls.Add($status)
 $caption=New-Object Windows.Forms.Label;$caption.SetBounds(20,105,680,25);$caption.Text='Release feed URL (HTTPS)';$form.Controls.Add($caption)
 $url=New-Object Windows.Forms.TextBox;$url.SetBounds(20,134,680,28);$form.Controls.Add($url)
 $auto=New-Object Windows.Forms.CheckBox;$auto.SetBounds(20,172,680,28);$auto.Text='Check automatically when this updater opens (never install automatically)';$form.Controls.Add($auto)
 function Make-Button($text,$x,$y,$w){$b=New-Object Windows.Forms.Button;$b.SetBounds($x,$y,$w,38);$b.Text=$text;$form.Controls.Add($b);return $b}
 $check=Make-Button 'Check for updates' 20 212 320
 $download=Make-Button 'Download and install' 360 212 340
 $local=Make-Button 'Install local ZIP...' 20 264 320
 $rollback=Make-Button 'Roll back' 360 264 340
 $result=New-Object Windows.Forms.TextBox;$result.SetBounds(20,320,680,150);$result.Multiline=$true;$result.ReadOnly=$true;$result.ScrollBars='Vertical';$form.Controls.Add($result)
 $result.Text='Enter your published release feed URL. Checking and downloading happen here; each new custom build still requires publisher approval.'
 $config=Join-Path $script:Control 'feed-settings.json';Assert-PlainPath $config
 if(Test-Path -LiteralPath $config){$c=[IO.File]::ReadAllText($config)|ConvertFrom-Json;$url.Text=$c.url;$auto.Checked=[bool]$c.checkOnOpen}
 function Refresh-State {
  $s=Read-Selection;$status.Text="Current: $($s.Current)`r`nPrevious: $($s.Previous)"
  $busy=$null -ne $script:Job
  $url.Enabled=!$busy;$auto.Enabled=!$busy;$check.Enabled=!$busy;$local.Enabled=!$busy
  $rollback.Enabled=(!$busy -and [bool]$s.Previous)
  $download.Enabled=(!$busy -and $null -ne $script:Available -and $script:Available.release.id -cne $s.Current)
 }
 function Save-FeedSettings {
  $null=Assert-Https $url.Text.Trim()
  [IO.File]::WriteAllText($config,(@{url=$url.Text.Trim();checkOnOpen=$auto.Checked}|ConvertTo-Json))
 }
 function Start-Operation([string]$Operation,[string]$Argument,[string]$Id='',[string]$Hash='') {
  if($script:Job){return}
  $script:Operation=$Operation;$result.Text='Working: '+$Operation+'. Please wait...'
  $ps=[PowerShell]::Create()
  [void]$ps.AddScript({param($root,$op,$arg,$id,$hash)
   $ErrorActionPreference='Stop'
   . (Join-Path $root 'custom-pcsx2/updater/Engine.ps1')
   Initialize-Updater $root
   . (Join-Path $root 'custom-pcsx2/updater/Feed.ps1')
   switch($op){
    'Check' {Check-Feed $arg}
    'Download and install' {Install-FromFeed $arg $id $hash}
    'Install local ZIP' {Install-Package $arg}
    'Roll back' {Rollback-Runtime}
   }
  }).AddArgument($script:Root).AddArgument($Operation).AddArgument($Argument).AddArgument($Id).AddArgument($Hash)
  $script:Worker=$ps;$script:Job=$ps.BeginInvoke();Refresh-State
 }
 $timer=New-Object Windows.Forms.Timer;$timer.Interval=200
 $timer.Add_Tick({
  if($script:Job -and $script:Job.IsCompleted){
   try {
    $out=$script:Worker.EndInvoke($script:Job)
    if($script:Worker.HadErrors){throw ($script:Worker.Streams.Error | Out-String)}
    if($script:Operation -eq 'Check'){
     $script:Available=$out[0];$r=$script:Available.release
     if($r.id -ceq (Read-Selection).Current){$result.Text='You already have the latest approved release: '+$r.label}
     else{$result.Text="Approved release: $($r.label)`r`nDownload: $([math]::Round($r.bytes/1MB,1)) MB`r`nSelect Download and install to proceed. Close PCSX2 first."}
    }else{$result.Text=($out | Out-String)}
   }catch{$result.Text=$_.Exception.Message;$script:Available=$null}
   finally{$script:Worker.Dispose();$script:Job=$null;Refresh-State}
  }
 })
 $check.Add_Click({try{Save-FeedSettings;$script:Available=$null;Start-Operation 'Check' $url.Text.Trim()}catch{$result.Text=$_.Exception.Message}})
 $download.Add_Click({if($script:Available){Start-Operation 'Download and install' $url.Text.Trim() $script:Available.release.id $script:Available.release.sha256}})
 $local.Add_Click({$d=New-Object Windows.Forms.OpenFileDialog;$d.Filter='Custom update ZIP (*.zip)|*.zip';try{if($d.ShowDialog($form) -eq 'OK'){Start-Operation 'Install local ZIP' $d.FileName}}finally{$d.Dispose()}})
 $rollback.Add_Click({Start-Operation 'Roll back' ''})
 $url.Add_TextChanged({$script:Available=$null;Refresh-State})
 $auto.Add_CheckedChanged({if($url.Text.Trim()){try{Save-FeedSettings}catch{$result.Text=$_.Exception.Message}}})
 $form.Add_FormClosing({param($sender,$e) if($script:Job){$e.Cancel=$true;$result.Text='An operation is in progress. Wait for it to finish before closing.'}})
 $form.Add_Shown({if($auto.Checked -and $url.Text.Trim()){$check.PerformClick()}})
 Refresh-State;$timer.Start();[void]$form.ShowDialog();$timer.Stop();$timer.Dispose()
}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'PCSX2 Updater','OK','Error')}
