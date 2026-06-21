"""Electrical Rules Check (ERC) for MCU breakout netlists.

All rules are deterministic and specific to the MCU breakout board class.
Returns a list of structured violation dicts; an empty list means the netlist passes.

Rule IDs
--------
power_pins_on_power_net     Every power_in pin of an IC must be in a "power" net.
ground_pins_on_ground_net   Every ground pin must be in a "ground" net.
no_output_conflict          No two power_out/output pins share the same net.
i2c_pullup_present          SDA/SCL nets must contain a passive resistor pin.
decoupling_cap_on_ic_power  Each IC's VDD net must include a capacitor pin.
no_pin_duplicated           A pin reference may appear in at most one net.
all_pins_accounted          Every catalog pin is either in a net or unconnected list.
net_class_consistency       Net class must agree with the pin types it carries.
"""
from __future__ import annotations
from typing import Any


# ── Types ─────────────────────────────────────────────────────────────────────

# A violation is a plain dict so it serialises directly to JSON.
def _v(rule: str, description: str, offending_pins: list[dict]) -> dict:
    return {"rule": rule, "description": description, "offending_pins": offending_pins}


def _pin_ref(component_role: str, part_id: str, pin_number: str,
             pin_name: str, net_name: str | None = None) -> dict:
    d: dict = {
        "component_role": component_role,
        "part_id": part_id,
        "pin_number": pin_number,
        "pin_name": pin_name,
    }
    if net_name is not None:
        d["net_name"] = net_name
    return d


# ── Active IC categories (power and ground pins must be covered) ───────────────
_IC_CATEGORIES = {"mcu", "ldo", "sensor", "diode"}


def _name_has(pin_name: str, *keywords: str) -> bool:
    n = pin_name.upper()
    return any(kw in n for kw in keywords)


# ── Public entry point ────────────────────────────────────────────────────────

def run_erc(
    nets: list[dict],
    unconnected: list[dict],
    components: list[dict],          # [{functional_role, part_id, category, ...}]
    catalog_pins: dict[str, dict],   # part_id → {pin_number → {name, type}}
) -> list[dict]:
    """Run all ERC rules and return a (possibly empty) list of violation dicts."""

    # Build lookup helpers
    role_to_comp: dict[str, dict] = {c["functional_role"]: c for c in components}
    nets_by_name: dict[str, dict] = {n["name"]: n for n in nets}

    # Map (component_role, pin_number) → net_name for every in-net pin
    in_net: dict[tuple[str, str], str] = {}
    for net in nets:
        for pin in net.get("pins", []):
            key = (pin.get("component_role", ""), pin.get("pin_number", ""))
            in_net[key] = net["name"]

    # Map (component_role, pin_number) → True for explicitly unconnected pins
    in_uc: set[tuple[str, str]] = set()
    for uc in unconnected:
        pr = uc.get("pin_ref") or uc
        key = (pr.get("component_role", ""), pr.get("pin_number", ""))
        in_uc.add(key)

    violations: list[dict] = []

    violations += _check_power_pins_on_power_net(nets, in_net, role_to_comp, catalog_pins)
    violations += _check_ground_pins_on_ground_net(nets, in_net, role_to_comp, catalog_pins)
    violations += _check_no_output_conflict(nets, role_to_comp, catalog_pins)
    violations += _check_i2c_pullup(nets, role_to_comp, catalog_pins)
    violations += _check_decoupling_cap(nets, in_net, components, catalog_pins)
    violations += _check_no_pin_duplicated(nets)
    violations += _check_all_pins_accounted(in_net, in_uc, components, catalog_pins)
    violations += _check_net_class_consistency(nets, role_to_comp, catalog_pins)

    return violations


# ── Rule implementations ──────────────────────────────────────────────────────

def _get_pin_info(role: str, pin_num: str, role_to_comp: dict, catalog_pins: dict) -> dict:
    comp = role_to_comp.get(role, {})
    part_id = comp.get("part_id", "?")
    pins = catalog_pins.get(part_id, {})
    info = pins.get(pin_num, {})
    return {
        "component_role": role,
        "part_id": part_id,
        "pin_number": pin_num,
        "pin_name": info.get("name", pin_num),
        "pin_type": info.get("type", "unknown"),
    }


def _check_power_pins_on_power_net(
    nets: list[dict],
    in_net: dict[tuple, str],
    role_to_comp: dict,
    catalog_pins: dict,
) -> list[dict]:
    violations: list[dict] = []
    net_class_by_name = {n["name"]: n.get("net_class", "") for n in nets}

    for role, comp in role_to_comp.items():
        if comp.get("category") not in _IC_CATEGORIES:
            continue
        part_id = comp["part_id"]
        for pin_num, info in catalog_pins.get(part_id, {}).items():
            if info.get("type") != "power_in":
                continue
            key = (role, pin_num)
            net_name = in_net.get(key)
            if net_name is None:
                violations.append(_v(
                    "power_pins_on_power_net",
                    f"power_in pin {info.get('name')} on {role} ({part_id}) "
                    f"is not connected to any net.",
                    [_pin_ref(role, part_id, pin_num, info.get("name", ""), None)],
                ))
            elif net_class_by_name.get(net_name) not in ("power", "ground"):
                # VBUS from USB connector is power_in but lands on a power net called VBUS
                # Allow any net_class that is 'power'; 'ground' is wrong here.
                if net_class_by_name.get(net_name) == "ground":
                    violations.append(_v(
                        "power_pins_on_power_net",
                        f"power_in pin {info.get('name')} on {role} is on net "
                        f"'{net_name}' (net_class=ground) — should be a power net.",
                        [_pin_ref(role, part_id, pin_num, info.get("name", ""), net_name)],
                    ))
    return violations


def _check_ground_pins_on_ground_net(
    nets: list[dict],
    in_net: dict[tuple, str],
    role_to_comp: dict,
    catalog_pins: dict,
) -> list[dict]:
    violations: list[dict] = []
    net_class_by_name = {n["name"]: n.get("net_class", "") for n in nets}

    for role, comp in role_to_comp.items():
        part_id = comp["part_id"]
        for pin_num, info in catalog_pins.get(part_id, {}).items():
            if info.get("type") != "ground":
                continue
            key = (role, pin_num)
            net_name = in_net.get(key)
            if net_name is None:
                violations.append(_v(
                    "ground_pins_on_ground_net",
                    f"ground pin {info.get('name')} on {role} ({part_id}) "
                    "is not connected to any net.",
                    [_pin_ref(role, part_id, pin_num, info.get("name", ""), None)],
                ))
            elif net_class_by_name.get(net_name) != "ground":
                violations.append(_v(
                    "ground_pins_on_ground_net",
                    f"ground pin {info.get('name')} on {role} is on net "
                    f"'{net_name}' (net_class={net_class_by_name.get(net_name)!r}) "
                    "— expected net_class 'ground'.",
                    [_pin_ref(role, part_id, pin_num, info.get("name", ""), net_name)],
                ))
    return violations


def _check_no_output_conflict(
    nets: list[dict],
    role_to_comp: dict,
    catalog_pins: dict,
) -> list[dict]:
    violations: list[dict] = []
    for net in nets:
        driving_pins: list[dict] = []
        for pin in net.get("pins", []):
            role = pin.get("component_role", "")
            comp = role_to_comp.get(role, {})
            part_id = comp.get("part_id", "")
            pin_num = pin.get("pin_number", "")
            info = catalog_pins.get(part_id, {}).get(pin_num, {})
            if info.get("type") in ("power_out", "output"):
                driving_pins.append(
                    _pin_ref(role, part_id, pin_num, info.get("name", ""), net["name"])
                )
        if len(driving_pins) > 1:
            violations.append(_v(
                "no_output_conflict",
                f"Net '{net['name']}' has {len(driving_pins)} driving pins "
                "(power_out/output) — short circuit risk.",
                driving_pins,
            ))
    return violations


def _check_i2c_pullup(
    nets: list[dict],
    role_to_comp: dict,
    catalog_pins: dict,
) -> list[dict]:
    violations: list[dict] = []
    for net in nets:
        i2c_pins: list[dict] = []
        has_pullup = False
        for pin in net.get("pins", []):
            role = pin.get("component_role", "")
            comp = role_to_comp.get(role, {})
            part_id = comp.get("part_id", "")
            pin_num = pin.get("pin_number", "")
            info = catalog_pins.get(part_id, {}).get(pin_num, {})
            pin_name = info.get("name", pin_num)
            if _name_has(pin_name, "SDA", "SCL", "I2C_S"):
                i2c_pins.append(
                    _pin_ref(role, part_id, pin_num, pin_name, net["name"])
                )
            # Pullup: passive pin from a resistor component
            if (info.get("type") == "passive"
                    and comp.get("category") == "resistor"):
                has_pullup = True
        if i2c_pins and not has_pullup:
            violations.append(_v(
                "i2c_pullup_present",
                f"Net '{net['name']}' carries I²C SDA/SCL but has no pull-up resistor pin.",
                i2c_pins,
            ))
    return violations


def _check_decoupling_cap(
    nets: list[dict],
    in_net: dict[tuple, str],
    components: list[dict],
    catalog_pins: dict,
) -> list[dict]:
    """For each IC with a VDD/VDDA pin, its power net must contain at least one capacitor pin."""
    violations: list[dict] = []

    # Build: net_name → set of (category, part_id) of components with pins on that net
    net_categories: dict[str, set[str]] = {}
    for net in nets:
        cats: set[str] = set()
        for pin in net.get("pins", []):
            role = pin.get("component_role", "")
            comp = next((c for c in components if c["functional_role"] == role), {})
            cats.add(comp.get("category", ""))
        net_categories[net["name"]] = cats

    # For each IC, find its VDD net and check for a capacitor on that net
    for comp in components:
        if comp.get("category") not in _IC_CATEGORIES:
            continue
        role = comp["functional_role"]
        part_id = comp["part_id"]
        for pin_num, info in catalog_pins.get(part_id, {}).items():
            if info.get("type") != "power_in":
                continue
            pin_name = info.get("name", "")
            if not _name_has(pin_name, "VDD", "VCC", "VDDA", "VDDIO", "VLOGIC", "VBUS"):
                continue
            vdd_net = in_net.get((role, pin_num))
            if vdd_net is None:
                continue
            cats_on_net = net_categories.get(vdd_net, set())
            if "capacitor" not in cats_on_net:
                violations.append(_v(
                    "decoupling_cap_on_ic_power",
                    f"IC '{role}' ({part_id}) power pin {pin_name!r} is on net "
                    f"'{vdd_net}' but no decoupling capacitor pin is on that net.",
                    [_pin_ref(role, part_id, pin_num, pin_name, vdd_net)],
                ))
    return violations


def _check_no_pin_duplicated(nets: list[dict]) -> list[dict]:
    seen: dict[tuple[str, str], str] = {}  # (role, pin) → first net_name
    violations: list[dict] = []
    for net in nets:
        for pin in net.get("pins", []):
            key = (pin.get("component_role", ""), pin.get("pin_number", ""))
            if key in seen:
                violations.append(_v(
                    "no_pin_duplicated",
                    f"Pin ({key[0]}, pin {key[1]}) appears in nets "
                    f"'{seen[key]}' AND '{net['name']}'.",
                    [{"component_role": key[0], "pin_number": key[1],
                      "first_net": seen[key], "second_net": net["name"]}],
                ))
            else:
                seen[key] = net["name"]
    return violations


def _check_all_pins_accounted(
    in_net: dict[tuple, str],
    in_uc: set[tuple],
    components: list[dict],
    catalog_pins: dict,
) -> list[dict]:
    """Every pin in the catalog must be in a net or the unconnected list."""
    violations: list[dict] = []
    for comp in components:
        role = comp["functional_role"]
        part_id = comp["part_id"]
        for pin_num, info in catalog_pins.get(part_id, {}).items():
            if info.get("type") == "nc":
                continue  # NC pins need not be listed
            key = (role, pin_num)
            if key not in in_net and key not in in_uc:
                violations.append(_v(
                    "all_pins_accounted",
                    f"Pin {info.get('name')!r} (pin {pin_num}) of '{role}' ({part_id}) "
                    "is neither in a net nor in the unconnected list.",
                    [_pin_ref(role, part_id, pin_num, info.get("name", ""), None)],
                ))
    return violations


def _check_net_class_consistency(
    nets: list[dict],
    role_to_comp: dict,
    catalog_pins: dict,
) -> list[dict]:
    violations: list[dict] = []
    for net in nets:
        declared_class = net.get("net_class", "")
        has_ground_pin = False
        has_power_out = False
        for pin in net.get("pins", []):
            role = pin.get("component_role", "")
            comp = role_to_comp.get(role, {})
            part_id = comp.get("part_id", "")
            pin_num = pin.get("pin_number", "")
            info = catalog_pins.get(part_id, {}).get(pin_num, {})
            ptype = info.get("type", "")
            if ptype == "ground":
                has_ground_pin = True
            if ptype == "power_out":
                has_power_out = True

        if has_ground_pin and declared_class != "ground":
            violations.append(_v(
                "net_class_consistency",
                f"Net '{net['name']}' has a ground pin but net_class={declared_class!r} "
                "(expected 'ground').",
                [],
            ))
        if has_power_out and declared_class not in ("power",):
            violations.append(_v(
                "net_class_consistency",
                f"Net '{net['name']}' has a power_out pin but net_class={declared_class!r} "
                "(expected 'power').",
                [],
            ))
    return violations
