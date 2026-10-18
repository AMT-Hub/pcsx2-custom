# PCSX2 nightly discovery reports

**These are review requests, not approved updates.**

Reviewed baseline: **v2.9.127** (`e35cb2c87590bc3d127b3bb4dd222b01e598c9a4`).

Discovery is scheduled hourly at **:53 UTC**. GitHub may delay or drop scheduled events; the next hour provides another opportunity. See the [workflow](https://github.com/AMT-Hub/pcsx2-custom/actions/workflows/nightly-discovery.yml) for runs, failures and manual checks.

## Check history

- **Last successful check:** [2026-10-18T16:12:12.365940+00:00](https://github.com/AMT-Hub/pcsx2-custom/actions/runs/39143905650/attempts/1) — event `schedule`.
- **Last successful scheduled check:** [2026-10-18T16:12:12.365940+00:00](https://github.com/AMT-Hub/pcsx2-custom/actions/runs/39143905650/attempts/1) — event `schedule`.

Push/manual checks do not verify the scheduled trigger. If the scheduled timestamp is missing or more than three hours old, investigate scheduling in Actions. These are fixed timestamps, not a live health badge. [Machine-readable last check](last-check.json).

## Reports against the current baseline

- [v2.9.129 / 091ab68708a5](reports/v2.9.129/f1eb8f61b139df7db14915ebc454a1df90293a5c0ac4087f7a00a412f6f5deaf.md) — 2026-10-16T19:06:41.641308+00:00
- [v2.9.128 / fdd6aca352cc](reports/v2.9.128/8a51383ea4aa3d0aab7d7fff89ee1d49539e1090e12115fd23364f85839f017f.md) — 2026-10-16T19:06:41.641308+00:00

Older assessments remain under `reports/`; their baseline and source identity are recorded in each report. Unchanged candidates are not reported twice. Retagged releases, changed assets or changed review inputs produce a new candidate record. Each run assesses at most 10 unseen candidates, newest first; any backlog is stated in its summary. Successful-check timestamps update independently of candidate reports.

Reports do not modify the custom emulator, launcher, updater, reviewed pins, releases or signed feed.
