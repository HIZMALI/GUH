# Integration slice validation record

Date: 2026-09-11. Execution host: local Windows/PowerShell, native Python 3.14 for the independent stdlib tests. Production target remains Python 3.12 container; Docker full-stack verification belongs to the main acceptance record.

Command from repository root:

```text
python -m unittest discover -s tests/modbus -v
```

24 tests PASS in 0.353 seconds after implementation fixes. Covered: supplied-source MPR literal addresses, negative signed values, scale, configurable word order, uint64 energy, missing/invalid values, MPR timeout; TVOC detector boundary/reserved bits, relay/state bits, manual timestamp example and timezone conversion, unused/partial sentinel, firmware version gate, diagnostic DTC byte order, inverted sensor bit polarity with active-error and installed-module context, offline result; real localhost FC03/04, alarm transition, HTTP bearer fleet poll through TCP, write rejection, invalid range/unit, fragmented/persistent requests, malformed MBAP, zero count, stale snapshot, socket timeout/offline, numeric panel mapping and247-unit boundary.

Fixtures contain deliberately synthetic values. Tests did not connect to a physical MPR, ABB COM module, energy cabinet or external SCADA. They prove software behavior for the tested vectors/frames; actual device compatibility, RTU electrical timing, commissioned word order/timezone, firmware details and safety functions remain unverified.

Hardware visual: `hardware/concept/panel-placement.svg` was rendered through the bundled Node `sharp` package and inspected at1300×1100. Output `hardware/concept/panel-placement.png` is a raster preview of the same vector concept. Text/zone layout and source dimensions were visually checked. This is not a mechanical interference check. An initial Playwright SVG screenshot attempt timed out; a PyMuPDF fallback was unavailable in the installed runtimes; the successful `sharp` render supplied visual QA. These development-only tools add no remote asset or runtime dependency to the application.

Source review: original MPR scan rotated for legibility (`tmp/pdfs/mpr-readable.png`), both MPR pages and source panel drawing inspected, ABB manual s.20–33 extracted text reviewed, HFCT30/50 source datasheets reviewed. Original source PDFs/XLSX were not modified. Earlier MPR summary address offsets were corrected against the scan; relevant map/source-analysis documents now use the actual source addresses.
