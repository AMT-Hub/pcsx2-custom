# Rules catalogue review — 0.2.0-test1

The catalogue is generated from general rules plus versioned identity/release
metadata. It is not a list limited to the installed collection.

- `COLLECTION-COVERAGE.md` (private download only): human-readable audit of all supplied collection entries.
- `COLLECTION-COVERAGE.json` (private download only): expected regional serials, generated values and method.
- `RULES-COVERAGE.json`: whole-database method counts and unresolved candidates.
- `catalogue.json`: the 52 explicit user-preference exceptions and their identities.
- `rules.json`: reusable policies, regional aliases and release metadata.
- `METADATA-PROVENANCE.json`: pinned inputs, checksums and rejected metadata joins.

Counts refer to disc identities, not distinct games. Normal-title coverage is not
chronology coverage. Demo identities excluded by the broader filter are not
silently restored by screenshot exceptions. No installed ROM was read or tested.
Manual overrides and clear-to-opt-out behaviour remain authoritative at runtime.
