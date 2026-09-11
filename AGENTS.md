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
- User authorizes parallel agent work. Keep file ownership disjoint and communicate contract changes before implementation. Do not modify another agent's files until handoff.
- Keep work at repository root (no redundant nested repository). Scripts must work from documented Windows/Linux commands.

Ownership: backend agent apps/api, services/anomaly_engine, services/simulator, services/telemetry, services/notification, tests/unit and tests/integration for backend. Integration agent services/modbus, services/scada_bridge, edge, hardware, related docs/tests. Frontend agent apps/web and frontend E2E. Root owns deployment, scripts, shared docs, data preparation, integration verification and final fixes.

V2 ownership override: root owns SCADA bank mapping/server/tests and only the SCADA endpoint/settings blocks inside apps/api. Integration agent owns PCB/card, reference firmware and environmental/EMC deliverables. Coordinate narrow shared-file patches. Baseline commit is 4a0f4c1cae879604a384e91862749fef754abecc; preserve all v1 verification evidence and original sources. V2 is additive hardening, not a rewrite. Never purge history to make the demo clean: use explicit run identities and views.
