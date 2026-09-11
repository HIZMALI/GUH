"""Source/pin contract tests. Actual C++ runtime tests run via firmware/tools/run_host_tests.py."""
import csv
import importlib.util
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
PCB = ROOT / "hardware/pcb"
FIRMWARE = ROOT / "edge/firmware"


def csv_rows(name):
    with (PCB / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_generated_firmware_maps_match_reviewed_python_metadata():
    path = FIRMWARE / "tools/generate_register_maps.py"
    spec = importlib.util.spec_from_file_location("firmware_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (FIRMWARE / "include/gridsentinel/register_maps.hpp").read_text(encoding="utf-8") == module.render()


def test_firmware_poll_ranges_never_include_tvoc_write_addresses():
    source = (FIRMWARE / "include/gridsentinel/register_maps.hpp").read_text(encoding="utf-8")
    ranges = re.findall(r"ReadRange (kTvoc\w+)\{(\d+), (\d+)\}", source)
    assert len(ranges) == 6
    for _, address, count in ranges:
        assert not set(range(int(address), int(address) + int(count))) & {213, 1000, 1100}
    assert "if (version.valid && version.major >= 3)" in (FIRMWARE / "src/core.cpp").read_text(encoding="utf-8")


def test_required_hardware_deliverables_and_parseable_svgs():
    required = {"README.md", "architecture.md", "schematic.svg", "pcb-placement.svg", "connectors.csv", "netlist.csv", "component-selection.md", "power-budget.csv", "design-rules.md", "safety-boundaries.md"}
    assert required <= {file.name for file in PCB.iterdir()}
    for name in ("schematic.svg", "pcb-placement.svg"):
        root = ET.parse(PCB / name).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        assert root.attrib["viewBox"]
    assert not list(PCB.glob("*.kicad_*"))  # EDA neutral; KiCad was not available.


def test_every_connector_pin_has_exact_matching_net_node():
    connectors, nets = csv_rows("connectors.csv"), csv_rows("netlist.csv")
    assert {row["connector"] for row in connectors} == {f"J{i}" for i in range(1, 8)}
    index = {(row["ref"], row["pin"]): row for row in nets}
    assert len(index) == len(nets)
    assert len({(row["connector"], row["pin"]) for row in connectors}) == len(connectors)
    for row in connectors:
        node = index[row["connector"], row["pin"]]
        assert node["net"] == row["net"] and node["domain"] == row["domain"]
        assert row["notes"] and row["status"] == "reference_concept"
    assert index["J1", "1"]["net"] == "VIN24"
    assert index["J7", "1"]["role"] == "input_only"
    assert not any("trip" in row["net"].lower() or "breaker" in row["net"].lower() for row in nets)


def test_field_common_and_isolated_power_domains_stay_independent():
    nodes = csv_rows("netlist.csv")
    index = {(row["ref"], row["pin"]): row for row in nodes}
    for port, chip, connector in (("MPR", "U3", "J2"), ("TVOC", "U4", "J3")):
        assert index[connector, "3"]["net"] == f"GND_{port}"
        for pin in ("9", "15"):
            assert index[chip, pin]["net"] == f"GND_{port}"
        assert index[chip, "16"]["net"] == f"V5_{port}"
        assert index[chip, "1"]["net"] == "V3V3"
        assert index[f"DC_{port}", "IN-"]["net"] == "GND_LOGIC"
        assert index[f"DC_{port}", "OUT-"]["net"] == f"GND_{port}"
        assert all(row["domain"] == port for row in nodes if row["net"] == f"GND_{port}")
    assert {row["net"] for row in nodes if row["net"].startswith("GND_")} == {"GND_LOGIC", "GND_MPR", "GND_TVOC"}


def test_candidate_pin_assignment_and_electrical_polarity():
    index = {(row["ref"], row["pin"]): row for row in csv_rows("netlist.csv")}
    # Source checked U1 pad mapping, not guessed GPIO number as module pad.
    expected = {"10":"MPR_TX", "11":"MPR_RX", "8":"MPR_DE_RE", "4":"TVOC_TX", "5":"TVOC_RX", "6":"TVOC_DE_RE", "18":"ETH_CS_N", "19":"SPI_MOSI", "20":"SPI_SCK", "21":"SPI_MISO", "38":"PD_FEATURE_RX"}
    for pin, net in expected.items(): assert index["U1", pin]["net"] == net
    # TI A is positive/non-inverting; ABB B is positive. Do not match terminal letters blindly.
    assert index["U4", "12"]["net"] == index["J3", "1"]["net"] == "TVOC_D1"
    assert index["U4", "13"]["net"] == index["J3", "2"]["net"] == "TVOC_D0"
    assert index["H_ETH1", "3"]["net"] == "SPI_MOSI"
    assert index["H_ETH2", "6"]["net"] == "SPI_MISO"
    for pad in ("15", "16", "26", "28", "29", "30"):
        assert index["U1", pad]["net"].startswith("NC_")


def test_power_budget_arithmetic_preserves_assumption_provenance():
    total = 0
    for row in csv_rows("power-budget.csv"):
        load = float(row["voltage_v"]) * float(row["current_ma_each"]) / 1000 * int(row["quantity"])
        assert math.isclose(load, float(row["load_w"]), abs_tol=0.000001)
        upstream = load / float(row["rail_conversion_efficiency_assumed"])
        assert math.isclose(upstream, float(row["from_5v_w"]), abs_tol=0.000001)
        assert row["basis"] and row["status"] == "unmeasured_engineering_budget"
        total += upstream
    assert math.isclose(total / .85 / 24 * 1.25, .3143695, abs_tol=.000001)


def test_h1_remains_in_right_auxiliary_zone_in_hardware_artifact():
    root = ET.parse(ROOT / "hardware/concept/panel-placement.svg").getroot()
    point = root.find(".//*[@id='th-a-h1']")
    assert point is not None and point.attrib["data-zone"] == "right-auxiliary"
    circle = point.find("{http://www.w3.org/2000/svg}circle")
    assert float(circle.attrib["cx"]) >= 702 and float(circle.attrib["cy"]) < 704
    docs = (ROOT / "docs/hardware/panel-placement.md").read_text(encoding="utf-8")
    assert "TH-A / H1" in docs and "alt kablo bölgesinde değildir" in docs


def test_environment_plan_covers_required_conditions_without_certification_claim():
    text = (ROOT / "docs/hardware/environmental-emc-plan.md").read_text(encoding="utf-8")
    for condition in ("Düşük sıcaklık", "Yüksek sıcaklık", "Nem / yoğuşma", "Yoğun EM / manyetik alan", "Transient / surge", "Titreşim", "Metal kabin RF", "IP / toz", "Kablo güzergâhı", "Güç kaybı"):
        assert f"| {condition}" in text
    assert "§2.2.9(iii)" in text and "§10.12" in text
    assert "uygulanmış saha/sertifikasyon sonucu değildir" in text
