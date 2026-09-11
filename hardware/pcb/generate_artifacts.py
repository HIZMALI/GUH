"""EDA-neutral, reviewable carrier connections. No production netlist/footprint claim."""
import csv
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ESP = "ESP32-S3-WROOM-1/1U datasheet v1.8 pp11-12"
ETH = "WIZnet WIZ850io official pin assignment"
ISO = "TI ISO1410 Rev I p4"
PLAN = "GridSentinel engineering reference assumption; component footprint TBD"
rows = []
connectors = []


def pin(ref, number, name, net, domain="LOGIC", source=PLAN, role="passive", status="reference_concept"):
    rows.append(dict(ref=ref, pin=str(number), pin_name=name, net=net, domain=domain, role=role, source=source, status=status))


def connector(ref, number, name, net, domain, role, notes):
    pin(ref, number, name, net, domain, PLAN, role)
    connectors.append(dict(connector=ref, pin=str(number), pin_name=name, net=net, domain=domain, direction=role, notes=notes, status="reference_concept"))


def two(ref, a, b, domain="LOGIC", names=("1", "2")):
    pin(ref, names[0], names[0], a, domain); pin(ref, names[1], names[1], b, domain)


def write_csv(name, data):
    with (HERE / name).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)


connector("J1", 1, "+24V_AUX", "VIN24", "LOGIC", "power_input", "Existing approved low-voltage auxiliary supply only; no mains/bar bus connection")
connector("J1", 2, "0V_AUX", "GND_LOGIC", "LOGIC", "power_return", "Not MPR/TVOC isolated commons")
connector("J1", 3, "CHASSIS", "CHASSIS", "CHASSIS", "shield", "Chassis bonding design/PE procedure requires installation review")
for ref, port in (("J2", "MPR"), ("J3", "TVOC")):
    connector(ref, 1, "D1 / B(+) device convention", f"{port}_D1", port, "data_bidirectional", "Read requests/responses only; TI ISO1410 A(+), pin12")
    connector(ref, 2, "D0 / A(-) device convention", f"{port}_D0", port, "data_bidirectional", "TI ISO1410 B(-), pin13; verify terminal marking at commissioning")
    connector(ref, 3, "COM", f"GND_{port}", port, "signal_common", "Independent isolated common; never join the other port/logic ground")
    connector(ref, 4, "SHIELD", "CHASSIS", "CHASSIS", "shield", "Screen termination coordinated at enclosure; not signal common")
for number, label, net in ((1, "PAIR1+", "ETH_CABLE_P1P"), (2, "PAIR1-", "ETH_CABLE_P1N"), (3, "PAIR2+", "ETH_CABLE_P2P"), (6, "PAIR2-", "ETH_CABLE_P2N")):
    connector("J4", number, label, net, "ETH_CABLE", "data_bidirectional", "RJ45 integral to WIZ850io; isolation transformer internal to module; no direct MCU net")
for number in (4, 5, 7, 8):
    connector("J4", number, "UNUSED / no PoE", f"NC_J4_{number}", "ETH_CABLE", "unconnected", "10/100 module; spare-pair treatment is module internal; carrier adds no PoE")
connector("J4", "S", "SHELL", "CHASSIS", "CHASSIS", "shield", "Module shield to chassis treatment requires EMC review; no unreviewed logic-ground bridge")
connector("J5", "RF", "ANTENNA", "RF_ANT", "RF", "rf_bidirectional", "Existing RF connector on ESP32-S3-WROOM-1U; not a fabricated carrier RF footprint")
connector("J5", "S", "RF_RETURN", "GND_LOGIC", "LOGIC", "signal_common", "Module antenna connector shield; chosen antenna/cable approval and routing TBD")
for number, label, net, role in ((1, "USB_D+", "USB_DP", "data_bidirectional"), (2, "USB_D-", "USB_DM", "data_bidirectional"), (3, "GND", "GND_LOGIC", "signal_common"), (4, "3V3_SENSE", "V3V3", "sense_only"), (5, "MCU_EN_ONLY", "MCU_EN", "local_service"), (6, "MCU_BOOT_ONLY", "MCU_BOOT", "local_service")):
    connector("J6", number, label, net, "LOGIC", role, "Local MCU service only; no field reset line; J6.4 must not back-power carrier")
for number, label, net, role in ((1, "PD_FEATURE_RX", "PD_FEATURE_RX", "input_only"), (2, "LOGIC_GND", "GND_LOGIC", "signal_common"), (3, "3V3_REFERENCE", "V3V3", "sense_only")):
    connector("J7", number, label, net, "LOGIC", role, "Optional 3.3V UART receive-only derived features; external qualified acquisition; no HFCT raw input; same safe low-voltage domain only")

# Candidate module pads; unused GPIOs explicitly stay unrouted. J5 RF is integral to U1.
used = {
    1:("GND", "GND_LOGIC"), 2:("3V3", "V3V3"), 3:("EN", "MCU_EN"),
    4:("GPIO4", "TVOC_TX"), 5:("GPIO5", "TVOC_RX"), 6:("GPIO6", "TVOC_DE_RE"), 7:("GPIO7", "WDI"),
    8:("GPIO15", "MPR_DE_RE"), 10:("GPIO17", "MPR_TX"), 11:("GPIO18", "MPR_RX"),
    13:("GPIO19_USB_D-", "USB_DM"), 14:("GPIO20_USB_D+", "USB_DP"),
    17:("GPIO9", "ETH_INT_N"), 18:("GPIO10", "ETH_CS_N"), 19:("GPIO11", "SPI_MOSI"),
    20:("GPIO12", "SPI_SCK"), 21:("GPIO13", "SPI_MISO"), 22:("GPIO14", "ETH_RST_N"),
    23:("GPIO21", "NVM_CS_N"), 27:("GPIO0_BOOT", "MCU_BOOT"), 38:("GPIO2", "PD_FEATURE_RX"),
    40:("GND", "GND_LOGIC"), 41:("EPAD", "GND_LOGIC"),
}
for number in range(1, 42):
    name, net = used.get(number, ("UNROUTED", f"NC_U1_{number}"))
    pin("U1", number, name, net, "LOGIC", ESP, "module_pin", "reference_candidate_pin_checked")
pin("U1", "RF", "integral_RF_port", "RF_ANT", "RF", ESP, "rf_bidirectional", "reference_candidate_pin_checked")
for sub, definitions in (("H_ETH1", [(1,"GND","GND_LOGIC"),(2,"GND","GND_LOGIC"),(3,"MOSI","SPI_MOSI"),(4,"SCLK","SPI_SCK"),(5,"SCNn","ETH_CS_N"),(6,"INTn","ETH_INT_N")]), ("H_ETH2", [(1,"GND","GND_LOGIC"),(2,"3V3D","V3V3"),(3,"3V3D","V3V3"),(4,"NC","NC_H_ETH2_4"),(5,"RSTn","ETH_RST_N"),(6,"MISO","SPI_MISO")])):
    for number, label, net in definitions:
        pin(sub, number, label, net, "LOGIC", ETH, "module_header", "reference_candidate_pin_checked")
for ref, port in (("U3", "MPR"), ("U4", "TVOC")):
    for number, label, net in [(1,"VCC1","V3V3"),(2,"GND1","GND_LOGIC"),(3,"R",f"{port}_RX"),(4,"RE_N",f"{port}_DE_RE"),(5,"DE",f"{port}_DE_RE"),(6,"D",f"{port}_TX"),(7,"NC",f"NC_{ref}_7"),(8,"GND1","GND_LOGIC")]:
        pin(ref, number, label, net, "LOGIC", ISO, "isolator_logic", "reference_candidate_pin_checked")
    for number, label, net in [(9,"GND2",f"GND_{port}"),(10,"NC",f"NC_{ref}_10"),(11,"NC",f"NC_{ref}_11"),(12,"A_NONINVERTING",f"{port}_D1"),(13,"B_INVERTING",f"{port}_D0"),(14,"NC",f"NC_{ref}_14"),(15,"GND2",f"GND_{port}"),(16,"VCC2",f"V5_{port}")]:
        pin(ref, number, label, net, port, ISO, "isolator_bus", "reference_candidate_pin_checked")
    two(f"R_{port}_DE", f"{port}_DE_RE", "GND_LOGIC")
    two(f"JP_{port}_TERM", f"{port}_D1", f"{port}_TERM", port)
    two(f"R_{port}_120", f"{port}_TERM", f"{port}_D0", port)
    two(f"R_{port}_BIAS_P_DNP", f"V5_{port}", f"{port}_D1", port)
    two(f"R_{port}_BIAS_N_DNP", f"{port}_D0", f"GND_{port}", port)
    two(f"C_{port}_VCC1", "V3V3", "GND_LOGIC")
    two(f"C_{port}_VCC2", f"V5_{port}", f"GND_{port}", port)
    for number, net in (("LINE1",f"{port}_D1"),("LINE0",f"{port}_D0"),("RETURN",f"GND_{port}")):
        pin(f"ESD_{port}_TBD", number, number, net, port)
    for number, net, domain in (("IN+","V5_MAIN","LOGIC"),("IN-","GND_LOGIC","LOGIC"),("OUT+",f"V5_{port}",port),("OUT-",f"GND_{port}",port)):
        pin(f"DC_{port}", number, number, net, domain)

two("F1", "VIN24", "VIN_FUSED")
two("D1_REVERSE", "VIN_FUSED", "VIN_PROT", names=("A", "K"))
two("TVS1_TBD", "VIN_PROT", "GND_LOGIC", names=("K", "A"))
two("L1_FILTER", "VIN_PROT", "VIN_FILTERED")
two("C1_INPUT", "VIN_FILTERED", "GND_LOGIC")
for ref, input_net, output_net in (("DC1_BUCK_TBD", "VIN_FILTERED", "V5_MAIN"), ("DC2_3V3_TBD", "V5_MAIN", "V3V3")):
    for name, net in (("VIN", input_net), ("VOUT", output_net), ("GND", "GND_LOGIC")):
        pin(ref, name, name, net)
two("C2_5V", "V5_MAIN", "GND_LOGIC"); two("C3_3V3", "V3V3", "GND_LOGIC")
two("R_EN_10K", "V3V3", "MCU_EN"); two("R_BOOT_10K", "V3V3", "MCU_BOOT")
two("R_ETH_CS_10K", "V3V3", "ETH_CS_N"); two("R_NVM_CS_10K", "V3V3", "NVM_CS_N")
two("R_ETH_RST_10K", "V3V3", "ETH_RST_N")
for name, net in (("VDD","V3V3"),("GND","GND_LOGIC"),("WDI","WDI"),("RESET_N","MCU_EN")):
    pin("SUPERVISOR_TBD", name, name, net)
for name, net in (("VDD","V3V3"),("GND","GND_LOGIC"),("CS_N","NVM_CS_N"),("SCK","SPI_SCK"),("MOSI","SPI_MOSI"),("MISO","SPI_MISO")):
    pin("NVM_TBD", name, name, net)
write_csv("connectors.csv", connectors); write_csv("netlist.csv", rows)

budget = []
for item, voltage, ma, qty, efficiency, basis in [
    ("ESP32-S3 module allocation",3.3,500,1,.85,"500mA minimum supply capability guideline; budget allocation not measured consumption"),
    ("WIZ850io Ethernet allocation",3.3,200,1,.85,"Official normal typical 141mA; 200mA engineering reserve is not guaranteed maximum"),
    ("ISO1410 logic side",3.3,6,2,.85,"Conservative 6mA allocation per logic side; verify selected mode and temperature"),
    ("ISO1410 field side",5,160,2,.75,"Conservative source driver-load maximum case allocation; isolated converter 75% assumed"),
    ("NVM watchdog indicators reserve",3.3,60,1,.85,"Unselected components; engineering allocation"),
]:
    watts = voltage * ma / 1000 * qty
    budget.append(dict(item=item,voltage_v=voltage,current_ma_each=ma,quantity=qty,load_w=round(watts,6),rail_conversion_efficiency_assumed=efficiency,from_5v_w=round(watts/efficiency,6),basis=basis,status="unmeasured_engineering_budget"))
write_csv("power-budget.csv",budget)


def svg_start(title, subtitle, height=1040):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="{height}" viewBox="0 0 1600 {height}"><title>{escape(title)}</title><defs><marker id="a" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#28c2b7"/></marker></defs><style>text{{font-family:Arial,sans-serif;fill:#eaf1f7}} .t{{font-size:30px;font-weight:bold}} .h{{font-size:21px;font-weight:bold}} .p{{font-size:17px}} .s{{font-size:14px;fill:#b7c9d7}} .wire{{fill:none;stroke:#28c2b7;stroke-width:3;marker-end:url(#a)}} .box{{fill:#132a3b;stroke:#48697f;stroke-width:2}} .domain{{fill:#153a3d;stroke:#28c2b7;stroke-width:2}}</style><rect width="1600" height="{height}" fill="#091823"/><text x="48" y="52" class="t">{escape(title)}</text><text x="48" y="85" class="p">{escape(subtitle)}</text>']


def box(svg, x, y, w, h, title, lines, cls="box"):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/><text x="{x+20}" y="{y+32}" class="h">{escape(title)}</text>')
    for i, line in enumerate(lines): svg.append(f'<text x="{x+20}" y="{y+62+i*25}" class="p">{escape(line)}</text>')


def wire(svg, path, label, x, y):
    svg.append(f'<path d="{path}" class="wire"/><text x="{x}" y="{y}" class="s">{escape(label)}</text>')


svg = svg_start("GridSentinel Edge Interface Carrier v0.1", "EDA-neutral reference schematic | pin/net names match CSV | no field control outputs")
box(svg,45,120,440,190,"J1 → protected auxiliary power",["1: +24V_AUX   2: 0V   3: chassis","F1 → D1 reverse → TVS1 / L1 / C1","DC1 buck 24V → V5_MAIN","DC2 switching 5V → V3V3"])
box(svg,535,120,470,190,"U1 ESP32-S3-WROOM-1U candidate",["p2: 3V3 | p1 / p40 / p41: GND_LOGIC","p3 EN ← local supervisor + pull-up","p7 GPIO7 → watchdog WDI","Uncommissioned reference MCU source"])
box(svg,1055,120,500,190,"U2 WIZ850io module / J4 Ethernet",["H_ETH1: 1,2 GND | 3 MOSI | 4 SCLK","H_ETH1: 5 CSn | 6 INTn","H_ETH2: 1 GND | 2,3 3V3 | 4 NC","H_ETH2: 5 RSTn | 6 MISO"])
wire(svg,"M485 190 H535","V3V3",486,177)
wire(svg,"M1005 220 H1055","SPI",1007,207)
box(svg,45,365,440,250,"MPR isolated domain / J2",["DC_MPR: V5_MAIN → isolated V5_MPR","U3 ISO1410 p16 VCC2; p9,15 GND2","J2.1 D1(+) ← U3.12 A (TI naming)","J2.2 D0(-) ← U3.13 B (TI naming)","J2.3 COM = GND_MPR; .4 chassis","120Ω end-only jumper; bias DNP"],"domain")
box(svg,535,365,470,250,"MCU UART routing / LOGIC domain",["MPR TX p10/G17 → U3.6 D","MPR RX p11/G18 ← U3.3 R","MPR DE/RE p8/G15 → U3.4 + .5","TVOC TX p4/G4 → U4.6 D","TVOC RX p5/G5 ← U4.3 R","TVOC DE/RE p6/G6 → U4.4 + .5"])
box(svg,1055,365,500,250,"TVOC isolated domain / J3",["DC_TVOC: V5_MAIN → isolated V5_TVOC","U4 ISO1410 p16 VCC2; p9,15 GND2","J3.1 ABB +(B) ← U4.12 A (TI)","J3.2 ABB -(A) ← U4.13 B (TI)","J3.3 COM = GND_TVOC; .4 chassis","120Ω end-only jumper; bias DNP"],"domain")
wire(svg,"M535 470 H485","isolation",484,457); wire(svg,"M1005 470 H1055","isolation",1007,457)
box(svg,45,670,440,215,"Local storage + watchdog",["SPI NVM ≥64KiB allocation; part TBD","NVM CS p23/G21; shared SPI bus","Atomic dual-bank journal port required","Supervisor RESETn → MCU_EN only","No external reset connection"])
box(svg,535,670,470,215,"J5 antenna + J6 local service",["J5 is U1 integral external RF port","TH-A / H1: right auxiliary air space","J6.1 USB D+ p14; .2 D- p13","J6.3 GND; .4 3V3 sense (no feed)","J6.5 MCU EN; .6 MCU BOOT p27"])
box(svg,1055,670,500,215,"J7 optional PD feature input",[".1 UART RX-only → U1 p38 / GPIO2",".2 GND_LOGIC; .3 3V3 sense","Separate qualified acquisition required","No raw HFCT / MHz / pC measurement","PD via existing LAN also possible"])
svg.append('<text x="48" y="934" class="h">Two field commons remain separate. Ethernet magnetics are inside WIZ850io. No mains, relay, trip or protection-reset circuit.</text>')
svg.append('<text x="48" y="970" class="p">Symbolic power / storage components need selection and detailed design. No ERC/DRC, insulation, EMC or thermal certification.</text></svg>')
(HERE/"schematic.svg").write_text("\n".join(svg),encoding="utf-8")

svg = svg_start("Carrier v0.1 | PCB placement study", "Planning envelope 160 × 100 mm assumed | placement only, unrouted | no manufacturing files",1100)
svg.append('<rect x="110" y="135" width="1380" height="775" rx="22" fill="#0c302e" stroke="#63b9a9" stroke-width="3"/>')
box(svg,145,175,330,170,"J1 / input protection",["F1 • D1 • TVS1 • filter","DC1 24→5V | DC2 5→3V3","Thermal / surge validation pending"])
box(svg,550,175,400,170,"U1 + local service",["ESP32-S3-WROOM-1U","J5 external antenna cable exit ↑","J6 local debug | strap pins reserved"])
box(svg,1050,175,400,170,"J4 / WIZ850io",["RJ45 at enclosure edge","Magnetics integral to module","Module footprint / keepout unverified"])
box(svg,550,410,400,150,"LOGIC island",["NVM | watchdog | shared SPI","J7 PD feature input, RX only","No ground copper across barriers"])
box(svg,145,630,395,220,"MPR field island",["J2 at edge; protected twisted pair","DC_MPR isolated power → U3","GND_MPR only on field side","Termination / bias coordination"],"domain")
box(svg,1050,630,400,220,"TVOC field island",["J3 at edge; protected twisted pair","DC_TVOC isolated power → U4","GND_TVOC only on field side","COM never shared with MPR"],"domain")
svg.append('<path d="M110 590 H590 V910 M1000 910 V590 H1490" stroke="#f1bd64" stroke-width="5" stroke-dasharray="12 9" fill="none"/>')
svg.append('<text x="610" y="665" class="h">Isolation barriers</text><text x="610" y="700" class="p">Symbolic width only.</text><text x="610" y="730" class="p">Creepage / clearance</text><text x="610" y="760" class="p">must be calculated.</text>')
svg.append('<text x="48" y="965" class="h">Location in panel: safe right auxiliary volume, separated from busbars and lower cable / HFCT work area.</text>')
svg.append('<text x="48" y="1000" class="p">TH-A / H1 samples representative air away from carrier heat. Antenna placement requires closed-door RF trials.</text>')
svg.append('<text x="48" y="1035" class="p">KiCad unavailable: no fabricated .kicad_sch / .kicad_pcb, no ERC/DRC or production-readiness claim.</text></svg>')
(HERE/"pcb-placement.svg").write_text("\n".join(svg),encoding="utf-8")
print(f"Generated {len(connectors)} connector pins, {len(rows)} net nodes, {len(budget)} power allocations and 2 SVGs")
