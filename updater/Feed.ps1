# Dot-source Engine.ps1 and initialise it before this module. Windows PowerShell 5.1.
function Assert-Https([string]$Url) {
 $u=$null
 if (![Uri]::TryCreate($Url,[UriKind]::Absolute,[ref]$u) -or $u.Scheme -cne 'https' -or $u.UserInfo -or $u.Fragment) {throw 'An HTTPS URL without embedded credentials or a fragment is required.'}
 return $u
}
function Receive-Https([string]$Url,[string]$Destination,[long]$Limit) {
 $uri=Assert-Https $Url
 [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
 $response=$null;$networkStream=$null;$output=$null
 try {
  for($redirect=0;$redirect -le 8;$redirect++) {
   $request=[Net.HttpWebRequest]::Create($uri);$request.AllowAutoRedirect=$false
   $request.Timeout=30000;$request.ReadWriteTimeout=30000;$request.UserAgent='CustomPCSX2-Updater/0.2.0'
   $response=$request.GetResponse();$code=[int]$response.StatusCode
   if($code -in @(301,302,303,307,308)) {
    $next=New-Object Uri($uri,$response.Headers['Location']);$response.Dispose();$response=$null
    $uri=Assert-Https $next.AbsoluteUri;continue
   }
   if($code -ne 200){throw "Unexpected HTTP response: $code"};break
  }
  if(!$response){throw 'Too many download redirects.'}
  if($response.ContentLength -gt $Limit){throw 'Download exceeds the permitted size.'}
  $networkStream=$response.GetResponseStream()
  $output=[IO.File]::Open($Destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  $buffer=New-Object byte[] 65536;[long]$total=0;$clock=[Diagnostics.Stopwatch]::StartNew()
  while(($count=$networkStream.Read($buffer,0,$buffer.Length)) -gt 0) {
   $total+=$count
   if($total -gt $Limit){throw 'Download exceeds the permitted size.'}
   if($clock.Elapsed.TotalMinutes -gt 30){throw 'Download exceeded the 30-minute limit.'}
   $output.Write($buffer,0,$count)
  }
  $output.Flush($true)
 } finally {if($output){$output.Dispose()};if($networkStream){$networkStream.Dispose()};if($response){$response.Dispose()}}
}
function Read-Feed([byte[]]$Bytes) {
 if($Bytes.Length -gt 1048576){throw 'Feed is too large.'}
 $envelope=[Text.Encoding]::UTF8.GetString($Bytes) | ConvertFrom-Json
 $payload=[Convert]::FromBase64String($envelope.payload)
 $signature=[Convert]::FromBase64String($envelope.signature)
 $rsa=New-Object Security.Cryptography.RSACryptoServiceProvider
 try {
  $rsa.PersistKeyInCsp=$false;$rsa.FromXmlString([IO.File]::ReadAllText((Join-Path $script:Control 'public-key.xml')))
  if(!$rsa.VerifyData($payload,[Security.Cryptography.CryptoConfig]::MapNameToOID('SHA256'),$signature)){throw 'Feed signature is invalid.'}
 }finally{$rsa.Dispose()}
 $feed=[Text.Encoding]::UTF8.GetString($payload) | ConvertFrom-Json
 if($feed.schema -ne 1 -or $feed.product -cne 'CustomPCSX2' -or $feed.channel -cne 'approved'){throw 'Unsupported release feed.'}
 if($feed.sequence -isnot [long] -and $feed.sequence -isnot [int]){throw 'Invalid feed sequence.'}
 if($feed.sequence -lt 1 -or $feed.sequence -gt 2147483647){throw 'Invalid feed sequence.'}
 $expires=[DateTimeOffset]::Parse($feed.expiresUtc,[Globalization.CultureInfo]::InvariantCulture)
 if($expires -le [DateTimeOffset]::UtcNow -or $expires -gt [DateTimeOffset]::UtcNow.AddDays(91)){throw 'Feed has expired or has an invalid expiry. Ask the publisher to refresh it.'}
 $r=$feed.release
 if(!(Valid-Id $r.id) -or $r.id -eq 'legacy' -or !$r.label -or $r.label.Length -gt 200){throw 'Invalid release identity.'}
 if($r.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $r.bytes -lt 1 -or $r.bytes -gt 1073741824){throw 'Invalid release download metadata.'}
 $null=Assert-Https $r.url
 $water=Join-Path $script:Control 'feed-highest.txt';Assert-PlainPath $water
 if(Test-Path -LiteralPath $water){$highest=[long][IO.File]::ReadAllText($water);if($feed.sequence -lt $highest){throw 'This feed is older than one already verified. Refusing replay.'}}
 return $feed
}
function Check-Feed([string]$Url) {
 $temp=Join-Path $script:Control ('feed-'+[guid]::NewGuid().ToString('N')+'.tmp')
 try {
  Receive-Https $Url $temp 1048576
  $lock=Acquire-UpdateLock
  try {
   $feed=Read-Feed ([IO.File]::ReadAllBytes($temp))
   $water=Join-Path $script:Control 'feed-highest.txt'
   $tmp=Join-Path $script:Control ('water-'+[guid]::NewGuid().ToString('N')+'.tmp')
   try {
    [IO.File]::WriteAllText($tmp,[string]$feed.sequence)
    if([IO.File]::Exists($water)){[IO.File]::Replace($tmp,$water,($tmp+'.old'))}else{[IO.File]::Move($tmp,$water)}
   }finally{foreach($p in @($tmp,($tmp+'.old'))){if([IO.File]::Exists($p)){[IO.File]::Delete($p)}}}
   return $feed
  }finally{$lock.Dispose()}
 }finally{if([IO.File]::Exists($temp)){[IO.File]::Delete($temp)}}
}
function Install-FromFeed([string]$Url,[string]$ExpectedId,[string]$ExpectedHash) {
 # Block a bad launcher before any download; Install-Package checks it again
 # and holds its verified bytes open through the final runtime selection.
 Assert-CompatibleLauncher
 # Recheck the authenticated feed when the user chooses Install.
 $feed=Check-Feed $Url;$r=$feed.release
 if($r.id -cne $ExpectedId -or $r.sha256 -cne $ExpectedHash){throw 'The approved release changed. Check for updates again before installing.'}
 $temp=Join-Path $script:Control ('download-'+[guid]::NewGuid().ToString('N')+'.zip')
 try {
  Receive-Https $r.url $temp ([long]$r.bytes)
  if((Get-Item -LiteralPath $temp).Length -ne $r.bytes -or (File-Hash $temp) -cne $r.sha256){throw 'Downloaded package hash or size is incorrect.'}
  # Cross-check the package identity against the signed feed before installation.
  $z=[IO.Compression.ZipFile]::OpenRead($temp)
  try {
   $entry=$z.GetEntry('manifest.json');if(!$entry -or $entry.Length -gt 1048576){throw 'Package metadata is missing or oversized.'}
   $reader=New-Object IO.StreamReader($entry.Open())
   try{$m=$reader.ReadToEnd() | ConvertFrom-Json}finally{$reader.Dispose()}
   if($m.id -cne $r.id){throw 'Package identity does not match the feed.'}
  }finally{$z.Dispose()}
  # Existing engine re-verifies package signature, all payload hashes, dependencies and locks.
  return (Install-Package $temp)
 }finally{if([IO.File]::Exists($temp)){[IO.File]::Delete($temp)}}
}
