# GridSentinel engineering rules

Read MASTER_SPEC.md, docs/source-analysis.md and docs/api-contract.md before modifying code. Supplied source PDFs and XLSX are immutable source of truth. Preserve them and their hashes. Read extracted source text in data/source; scanned MPR pages and panel drawing renders are in tmp/pdfs.

- On-premise only. No Sites registration, cloud hosting, cloud database, remote fonts or external runtime dependency. Next.js + FastAPI + PostgreSQL + Mosquitto + Docker Compose.
- This is a hackathon condition-monitoring prototype, never a protection relay. Never issue device writes, trip commands or reset certified protection equipment.
- All demo observations are synthetic. Workbook L1 samples are organizer-supplied synthetic; other channels generated synthetic; hardware mappings source-derived. Label provenance in API, UI and docs.
- Register addresses must have source page, width, scale, signedness, and addressing convention. Do not guess unspecified word order: make configurable and document unverified default.
- UTC aware telemetry; durable deduplication, out-of-order rejection, missing/stale/invalid quality explicit; no silent zero substitution.
- Deterministic explainable risk, no accuracy promises. Engineering demo thresholds are assumptions, not protection setpoints or universal limits.
- No embedded secrets. Bootstrap local credentials securely and ignore generated secrets. Authentication, viewer/operator/admin roles, audit log, validated identity and request limits.
- Test meaningful boundaries and end-to-end operation. Record measurements, commands, dates and failures honestly. Do not call anything verified without actual checks.
- Coordinate shared interfaces before implementation and preserve backward compatibility.
- Keep work at repository root (no redundant nested repository). Scripts must work from documented Windows/Linux commands.

V2 extends baseline commit `4a0f4c1cae879604a384e91862749fef754abecc`. Preserve V1 verification evidence and original sources. Never purge history to make the demo clean: use explicit run identities and views.
