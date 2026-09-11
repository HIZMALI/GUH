"""Build/run the reference C++ core in an isolated compiler image; never modifies app images."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "edge/firmware/test/verification.json"
IMAGE = "gridsentinel-firmware-host-test:local"


def run(command):
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{command}: exit {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def main():
    started = time.monotonic()
    build = ["docker", "build", "-f", "edge/firmware/test/Dockerfile.host", "-t", IMAGE, "."]
    command = ["docker", "run", "--rm", "--network", "none", IMAGE]
    run(build)
    result = json.loads(run(command))
    compiler = run(["docker", "run", "--rm", "--network", "none", IMAGE, "g++", "--version"]).splitlines()[0]
    sources = {}
    for folder in ("include", "src", "test"):
        for path in sorted((ROOT / "edge/firmware" / folder).rglob("*")):
            if path.is_file() and (path.suffix in (".cpp", ".hpp") or path.name == "Dockerfile.host"):
                sources[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "host_core": result,
        "elapsed_seconds": round(time.monotonic() - started, 3), "compiler": compiler,
        "build_command": build, "run_command": command,
        "image_id": run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"]),
        "embedded_build": {"status": "NOT_RUN", "reason": "ESP-IDF/PlatformIO/Arduino toolchains not installed; no physical board attached"},
        "physical_drivers": "NOT_VALIDATED", "kicad_erc_drc": "NOT_RUN_KICAD_NOT_INSTALLED",
        "source_sha256": sources,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
