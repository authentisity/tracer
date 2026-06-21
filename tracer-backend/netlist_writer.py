"""KiCad legacy .net format writer (isolated/swappable).

Ref-designator assignment rules
--------------------------------
mcu          → U1, U2, ...
ldo          → U<next>
sensor       → U<next>
capacitor    → C1, C2, ...
resistor     → R1, R2, ...
led          → D1, D2, ...
crystal      → Y1, Y2, ...
usb          → J1, J2, ...
diode        → D<next>
ferrite      → FB1, FB2, ...
header       → J<next>
(fallback)   → X1, X2, ...
"""
from __future__ import annotations
import datetime
from typing import Any


# ── Ref designator allocation ─────────────────────────────────────────────────

_CATEGORY_PREFIX: dict[str, str] = {
    "mcu":       "U",
    "ldo":       "U",
    "sensor":    "U",
    "capacitor": "C",
    "resistor":  "R",
    "led":       "D",
    "crystal":   "Y",
    "usb":       "J",
    "diode":     "D",
    "ferrite":   "FB",
    "header":    "J",
}


def _assign_refs(components: list[dict]) -> dict[str, str]:
    """Return {functional_role → ref_designator}."""
    counters: dict[str, int] = {}
    refs: dict[str, str] = {}
    for comp in components:
        cat = (comp.get("category") or "").lower()
        prefix = _CATEGORY_PREFIX.get(cat, "X")
        counters[prefix] = counters.get(prefix, 0) + 1
        refs[comp["functional_role"]] = f"{prefix}{counters[prefix]}"
    return refs


# ── Public entry point ────────────────────────────────────────────────────────

def write_kicad_net(
    components: list[dict],
    nets: list[dict],
    unconnected: list[dict],
    project_name: str = "tracer_design",
) -> str:
    """Return a KiCad legacy .net file as a string.

    Parameters
    ----------
    components  : list of SelectedComponent dicts
    nets        : list of Net dicts (from Netlist IR)
    unconnected : list of unconnected pin dicts
    project_name: used in the header
    """
    refs = _assign_refs(components)
    role_to_comp: dict[str, dict] = {c["functional_role"]: c for c in components}

    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    ts = datetime.datetime.utcnow().strftime("%Y%m%d %H%M%S")
    lines += [
        "(export (version D)",
        f"  (design",
        f"    (source \"{project_name}.kicad_sch\")",
        f"    (date \"{ts}\")",
        f"    (tool \"Tracer AI 1.0\")",
        f"  )",
    ]

    # ── Components section ────────────────────────────────────────────────────
    lines.append("  (components")
    for comp in components:
        role = comp["functional_role"]
        ref = refs[role]
        mpn = comp.get("mpn", "?")
        symbol = comp.get("kicad_symbol", "")
        footprint = comp.get("kicad_footprint", "")
        lines += [
            f"    (comp (ref \"{ref}\")",
            f"      (value \"{mpn}\")",
            f"      (footprint \"{footprint}\")",
            f"      (libsource (lib \"{symbol.split(':')[0] if ':' in symbol else symbol}\")"
            f" (part \"{symbol.split(':')[1] if ':' in symbol else symbol}\"))",
            f"      (property (name \"functional_role\") (value \"{role}\"))",
            f"    )",
        ]
    lines.append("  )")

    # ── Nets section ──────────────────────────────────────────────────────────
    # Net 0 is always GND in KiCad convention
    net_list: list[dict] = []
    gnd_nets = [n for n in nets if n.get("net_class") == "ground"]
    other_nets = [n for n in nets if n.get("net_class") != "ground"]
    ordered = gnd_nets + other_nets

    lines.append("  (nets")
    net_code = 0
    for net in ordered:
        net_code += 1
        net_name = net["name"]
        lines.append(f"    (net (code \"{net_code}\") (name \"{net_name}\")")
        for pin in net.get("pins", []):
            role = pin.get("component_role", "")
            pin_num = pin.get("pin_number", "")
            ref = refs.get(role, "?")
            lines.append(f"      (node (ref \"{ref}\") (pin \"{pin_num}\"))")
        lines.append("    )")

    # Unconnected pins get their own single-pin "net" (NC_xxx) so they appear in the file
    for uc in unconnected:
        net_code += 1
        pr = uc.get("pin_ref") or uc
        role = pr.get("component_role", "")
        pin_num = pr.get("pin_number", "")
        ref = refs.get(role, "?")
        nc_name = f"NC_{ref}_{pin_num}"
        lines += [
            f"    (net (code \"{net_code}\") (name \"{nc_name}\")",
            f"      (node (ref \"{ref}\") (pin \"{pin_num}\"))",
            f"    )",
        ]

    lines.append("  )")
    lines.append(")")

    return "\n".join(lines)
