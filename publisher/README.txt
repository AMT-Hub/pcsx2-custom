HOSTING AND PUBLISHING APPROVED BUILDS

No live repository is configured. Recommended initial host: a dedicated PUBLIC GitHub repository and Releases. Private authenticated repositories are not supported by this client yet; do not embed access tokens in URLs or config files.
The publisher script signs feeds with the existing PRIVATE-release-key.pem from the separately saved private publisher kit. This key never belongs in the portable PCSX2 folder, public repository, ZIP update or release assets. No private key is included in this source kit.
Only distribute the runtime-only signed update and its corresponding source/licence material. Do not upload the Personal portable ZIP: it contains personal BIOS files and settings. Do not upload games, memory cards or saves.

ONE-TIME SETUP
1. Choose/create a public repository under your own GitHub account. Keep normal source/licence documentation in it. GitHub Releases hosts update assets; no web server or token stored on client machines is required.
2. The stable feed URL will have this form (substitute OWNER and REPO):
   https://github.com/OWNER/REPO/releases/latest/download/approved-feed.json
3. Keep the key in private publisher storage. Feed signing requires Python and the cryptography package; clients do not require Python.

EACH APPROVED RELEASE
1. Complete the existing source port/build/gameplay approval process. Produce the signed custom update ZIP with the original publisher tooling. Do not automatically sign a newly compiled nightly without acceptance tests.
2. Choose a unique GitHub release tag and an immutable package asset name. Determine its permanent URL:
   https://github.com/OWNER/REPO/releases/download/TAG/PACKAGE.zip
3. Generate the feed using a strictly increasing integer sequence (start at 1 for the first live feed; increase even when only refreshing expiry):
   python make_feed.py --package PACKAGE.zip --url https://github.com/OWNER/REPO/releases/download/TAG/PACKAGE.zip --key PRIVATE-release-key.pem --sequence 1 --days 30 --output approved-feed.json
   The script verifies the package manifest signature with that key, checks ZIP integrity, and signs the feed containing the exact package identity, size and SHA-256.
4. Create a DRAFT release. Attach PACKAGE.zip, approved-feed.json, the exact corresponding custom source/build kit and required licence notices. Ensure source availability is appropriate for the software being distributed; a private ChatGPT download link alone is not a public source distribution.
5. Review the attached files. Publish the release and mark it Latest. Do not mark the feed release as a GitHub prerelease if relying on releases/latest. The software can still be labelled a test build in its title and notes.
6. Test the stable feed URL through the custom updater, then check update/rollback. Do not overwrite an already published package asset with different bytes; use a new tag/ID for changed builds.
7. Before expiry, publish a refreshed signed feed with a higher sequence. It may point to the same unchanged permanent package URL. A fresh metadata-only release can carry the feed and become Latest; the referenced package stays on the original release.

The signed feed removes trust in a bare unsigned latest.json, but the release-signing key remains the approval authority. If that key is compromised, a separately distributed updater trust-key change is required. There is no automatic key rotation or revocation mechanism in this prototype.
GitHub release discovery is not hard-coded: another HTTPS host can serve the same signed envelope and packages. The client requires public unauthenticated downloads with valid HTTPS certificates.

GitHub documentation:
https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases

NOT IMPLEMENTED
Hosted repository setup/publishing, GitHub authentication, unattended source builds, automated feature approval, Windows-startup checks, updater self-updating or silent runtime installation. Those are separate work from signed-feed delivery.
