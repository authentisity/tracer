"""Placement constraint compiler for MCU breakout boards.

Converts board outline, component list, netlist, and formal requirements into a
set of Z3 assertions that, when satisfied, yield a legal component placement.

Constraint families (each assertion is labeled for UNSAT core attribution):
  boundary    — every component's bbox stays within the board outline
  nooverlap   — no two component bboxes intersect
  edge        — edge-mounted parts (USB connectors, headers) touch a board edge
  rotation    — rotation variable is in {0, 1, 2, 3}
  proximity   — topologically-derived and requirement-driven distance limits

All positions are in integer *grid units* (default 0.5 mm/unit).
Rotation encoding: 0=0°, 1=90°, 2=180°, 3=270°.
Effective dimensions: at rot∈{1,3} width and height swap.
Centers are represented as 2×(grid units) to avoid integer division.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import z3

import catalog as _catalog


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class PlacementVars:
    role: str
    part_id: str
    category: str
    x: z3.ArithRef          # top-left x, grid units
    y: z3.ArithRef          # top-left y, grid units
    rot: z3.ArithRef        # ∈ {0, 1, 2, 3}
    w_units: int            # bbox width at rot=0, grid units (always ≥1)
    h_units: int            # bbox height at rot=0, grid units (always ≥1)
    satisfies_requirement_ids: list[str] = field(default_factory=list)


@dataclass
class CompiledConstraints:
    variables: dict[str, PlacementVars]    # functional_role → vars
    tracked: list[tuple[z3.BoolRef, str]]  # (formula, label) for unsat_core
    grid_mm: float
    board_w_units: int
    board_h_units: int
    optimize_terms: list[z3.ArithRef]      # pairwise Manhattan terms for Optimize


# ── Unit conversion ───────────────────────────────────────────────────────────

def _ceil(mm: float, grid_mm: float) -> int:
    """Round mm up to the next grid unit (minimum 1)."""
    return max(1, math.ceil(mm / grid_mm))


def _round(mm: float, grid_mm: float) -> int:
    return round(mm / grid_mm)


# ── Effective-dimension helpers (rotation-aware) ──────────────────────────────

def _eff_w(v: PlacementVars) -> z3.ArithRef:
    return z3.If(z3.Or(v.rot == 0, v.rot == 2), v.w_units, v.h_units)


def _eff_h(v: PlacementVars) -> z3.ArithRef:
    return z3.If(z3.Or(v.rot == 0, v.rot == 2), v.h_units, v.w_units)


def _center2x(v: PlacementVars) -> z3.ArithRef:
    """2 × center_x in grid units (avoids integer division)."""
    return 2 * v.x + _eff_w(v)


def _center2y(v: PlacementVars) -> z3.ArithRef:
    return 2 * v.y + _eff_h(v)


# ── Formal-requirement parsers ────────────────────────────────────────────────

def _board_outline_from_reqs(reqs: list[dict], default: tuple[float, float]) -> tuple[float, float]:
    """Extract board dimensions from formal requirements if present."""
    w, h = default
    for r in reqs:
        param = (r.get("parameter") or "").lower()
        stmt  = (r.get("statement") or "").lower()
        unit  = (r.get("unit") or "").lower()
        if unit not in ("mm", ""):
            continue
        try:
            v = float(r.get("value") or 0)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        if "board_width" in param or ("width" in param and "board" in stmt):
            w = v
        if "board_height" in param or "board_length" in param or (
                ("height" in param or "length" in param) and "board" in stmt):
            h = v
    return w, h


def _proximity_limits_from_reqs(reqs: list[dict]) -> dict[str, float]:
    """Return max-distance (mm) per proximity class from formal requirements."""
    limits: dict[str, float] = {
        "decoupling": 5.0,
        "pullup":     10.0,
        "crystal":    5.0,
    }
    for r in reqs:
        unit = (r.get("unit") or "").lower()
        op   = r.get("operator") or ""
        if unit != "mm" or op not in ("<=", "<"):
            continue
        try:
            d = float(r.get("value") or 9999)
        except (TypeError, ValueError):
            continue
        stmt  = ((r.get("statement") or "") + " " + (r.get("parameter") or "")).lower()
        if any(kw in stmt for kw in ("decoupl", "bypass cap", "bypass capacitor")):
            limits["decoupling"] = min(limits["decoupling"], d)
        if any(kw in stmt for kw in ("pull", "i2c", "sda", "scl")):
            limits["pullup"] = min(limits["pullup"], d)
        if any(kw in stmt for kw in ("crystal", "xtal", "osc")):
            limits["crystal"] = min(limits["crystal"], d)
    return limits


# ── Netlist topology helpers ──────────────────────────────────────────────────

_IC_CATS = {"mcu", "ldo", "sensor"}


def _role_category(role: str, components: list[dict]) -> str:
    for c in components:
        if c.get("functional_role") == role:
            return c.get("category", "")
    return ""


def _pin_name(role: str, pin_num: str, role_to_part: dict[str, str],
               catalog_pins: dict[str, dict]) -> str:
    part_id = role_to_part.get(role, "")
    return catalog_pins.get(part_id, {}).get(pin_num, {}).get("name", "").upper()


def _collect_proximity_pairs(
    netlist: dict,
    components: list[dict],
    catalog_pins: dict[str, dict],
) -> dict[str, list[tuple[str, str, str]]]:
    """Return lists of (role_a, role_b, net_name) per proximity class.

    decoupling: IC power_in on same power net as capacitor
    pullup:     MCU I2C SDA/SCL pin on same signal net as resistor
    crystal:    MCU OSC_IN/OUT pin on same signal net as crystal
    """
    role_to_part: dict[str, str] = {c["functional_role"]: c["part_id"] for c in components}
    role_to_cat: dict[str, str]  = {c["functional_role"]: c.get("category", "") for c in components}

    pairs: dict[str, list[tuple[str, str, str]]] = {
        "decoupling": [], "pullup": [], "crystal": [],
    }

    for net in netlist.get("nets", []):
        net_name  = net.get("name", "")
        net_class = net.get("net_class", "")
        pins      = net.get("pins", [])
        roles_on_net = [p.get("component_role", "") for p in pins]

        # Decoupling: IC *consuming* a power_in pin + capacitor on same power net.
        # Deliberately excludes LDOs (power_out pin) — they are suppliers, not consumers.
        if net_class == "power":
            ic_roles: list[str] = []
            for p in pins:
                r    = p.get("component_role", "")
                pnum = p.get("pin_number", "")
                if role_to_cat.get(r) not in _IC_CATS:
                    continue
                part_id  = role_to_part.get(r, "")
                pin_type = catalog_pins.get(part_id, {}).get(pnum, {}).get("type", "")
                if pin_type == "power_in" and r not in ic_roles:
                    ic_roles.append(r)
            cap_roles = [p.get("component_role", "") for p in pins
                         if role_to_cat.get(p.get("component_role", "")) == "capacitor"]
            for ic in ic_roles:
                for cap in cap_roles:
                    pairs["decoupling"].append((ic, cap, net_name))

        # Pull-ups and crystal: inspect pin names
        mcu_roles = [r for r in roles_on_net if role_to_cat.get(r) == "mcu"]
        res_roles = [r for r in roles_on_net if role_to_cat.get(r) == "resistor"]
        xtal_roles = [r for r in roles_on_net if role_to_cat.get(r) == "crystal"]

        for pin in pins:
            r = pin.get("component_role", "")
            p = pin.get("pin_number", "")
            name = _pin_name(r, p, role_to_part, catalog_pins)
            if role_to_cat.get(r) == "mcu":
                if any(kw in name for kw in ("SDA", "SCL", "I2C")):
                    for res in res_roles:
                        if (r, res, net_name) not in pairs["pullup"]:
                            pairs["pullup"].append((r, res, net_name))
                if any(kw in name for kw in ("OSC", "XIN", "XOUT", "CLKIN")):
                    for xtal in xtal_roles:
                        if (r, xtal, net_name) not in pairs["crystal"]:
                            pairs["crystal"].append((r, xtal, net_name))

    return pairs


# ── Edge-placement rules ───────────────────────────────────────────────────────
# Determines which board edge (if any) a component should touch.

_EDGE_BY_CATEGORY: dict[str, str] = {
    "connector": "bottom",   # USB connectors on bottom edge
}


def _edge_for_role(role: str, category: str, header_idx: dict) -> Optional[str]:
    """Return "left", "right", "top", "bottom", or None."""
    if category in _EDGE_BY_CATEGORY:
        return _EDGE_BY_CATEGORY[category]
    if category == "header":
        # Alternate headers between left and right edges
        idx = header_idx.setdefault("count", 0)
        header_idx["count"] += 1
        return "left" if idx % 2 == 0 else "right"
    return None


# ── Constraint builders ───────────────────────────────────────────────────────

def _assert(tracked: list, formula: z3.BoolRef, label: str) -> None:
    tracked.append((formula, label))


def _add_rotation_domain(v: PlacementVars, tracked: list) -> None:
    _assert(tracked, z3.And(v.rot >= 0, v.rot <= 3),
            f"rotation:{v.role}")


def _add_boundary(v: PlacementVars, W: int, H: int, tracked: list) -> None:
    ew = _eff_w(v)
    eh = _eff_h(v)
    _assert(tracked, z3.And(v.x >= 0, v.x + ew <= W,
                             v.y >= 0, v.y + eh <= H),
            f"boundary:{v.role}")


def _add_nooverlap(vi: PlacementVars, vj: PlacementVars, tracked: list) -> None:
    ewi, ehi = _eff_w(vi), _eff_h(vi)
    ewj, ehj = _eff_w(vj), _eff_h(vj)
    _assert(tracked,
            z3.Or(
                vi.x + ewi <= vj.x,
                vj.x + ewj <= vi.x,
                vi.y + ehi <= vj.y,
                vj.y + ehj <= vi.y,
            ),
            f"nooverlap:{vi.role}:{vj.role}")


def _add_edge(v: PlacementVars, edge: str, W: int, H: int, tracked: list) -> None:
    ew = _eff_w(v)
    eh = _eff_h(v)
    constraint = {
        "left":   v.x == 0,
        "right":  v.x + ew == W,
        "top":    v.y == 0,
        "bottom": v.y + eh == H,
    }.get(edge)
    if constraint is not None:
        _assert(tracked, constraint, f"edge:{v.role}:{edge}")


def _add_proximity(
    vi: PlacementVars,
    vj: PlacementVars,
    D_units: int,
    req_id: str,
    tracked: list,
) -> None:
    """Manhattan distance between centres ≤ D_units.

    Use 2× coordinates to avoid integer division:
      |cx_i − cx_j| + |cy_i − cy_j| ≤ D_units
    with 2cx = 2x + eff_w, this becomes:
      |2cx_i − 2cx_j| + |2cy_i − 2cy_j| ≤ 2*D_units
    Linearised as 4 half-plane constraints.
    """
    dx = _center2x(vi) - _center2x(vj)
    dy = _center2y(vi) - _center2y(vj)
    D2 = 2 * D_units
    label = f"proximity:{vi.role}:{vj.role}:{req_id}"
    _assert(tracked, z3.And(
        dx + dy <= D2,
        dx - dy <= D2,
        -dx + dy <= D2,
        -dx - dy <= D2,
    ), label)


# ── Main compiler ─────────────────────────────────────────────────────────────

def compile_constraints(
    board_outline: Optional[dict],
    components: list[dict],
    netlist: dict,
    formal_requirements: dict,
    catalog_pins: dict[str, dict],
    grid_mm: float = 0.5,
    default_board_mm: tuple[float, float] = (60.0, 60.0),
) -> CompiledConstraints:
    """Compile all placement constraints into Z3 assertions.

    Parameters
    ----------
    board_outline       : explicit {width_mm, height_mm} or None (derived from reqs)
    components          : list of selected-component dicts from stage 4
    netlist             : stage 5 output dict
    formal_requirements : stage 3 output dict
    catalog_pins        : {part_id → {pin_num → {name, type}}} from catalog.get_pins
    grid_mm             : placement grid resolution in mm
    default_board_mm    : fallback board size when not in requirements

    Returns
    -------
    CompiledConstraints ready for placement_solver.solve()
    """
    reqs = formal_requirements.get("requirements", [])

    # ── Board outline ─────────────────────────────────────────────────────────
    if board_outline:
        w_mm = float(board_outline.get("width_mm", default_board_mm[0]))
        h_mm = float(board_outline.get("height_mm", default_board_mm[1]))
    else:
        w_mm, h_mm = _board_outline_from_reqs(reqs, default_board_mm)

    W = _ceil(w_mm, grid_mm)
    H = _ceil(h_mm, grid_mm)

    # ── Geometry lookup + missing check ───────────────────────────────────────
    missing_geometry: list[str] = []
    geom: dict[str, dict] = {}
    for comp in components:
        pid = comp.get("part_id", "")
        g = _catalog.get_geometry(pid)
        if g is None:
            missing_geometry.append(f"{comp.get('functional_role')} ({pid})")
        else:
            geom[pid] = g

    if missing_geometry:
        raise ValueError(
            "Cannot compile placement constraints — missing footprint geometry for: "
            + ", ".join(missing_geometry)
        )

    # ── Create Z3 variables ───────────────────────────────────────────────────
    variables: dict[str, PlacementVars] = {}
    for comp in components:
        role = comp["functional_role"]
        pid  = comp["part_id"]
        bw, bh = geom[pid]["bbox_mm"]
        v = PlacementVars(
            role=role,
            part_id=pid,
            category=comp.get("category", ""),
            x=z3.Int(f"x_{role}"),
            y=z3.Int(f"y_{role}"),
            rot=z3.Int(f"rot_{role}"),
            w_units=_ceil(bw, grid_mm),
            h_units=_ceil(bh, grid_mm),
            satisfies_requirement_ids=comp.get("satisfies_requirement_ids", []),
        )
        variables[role] = v

    # ── Build constraints ─────────────────────────────────────────────────────
    tracked: list[tuple[z3.BoolRef, str]] = []
    roles = list(variables.keys())

    for v in variables.values():
        _add_rotation_domain(v, tracked)
        _add_boundary(v, W, H, tracked)

    for i, ri in enumerate(roles):
        for j in range(i + 1, len(roles)):
            _add_nooverlap(variables[ri], variables[roles[j]], tracked)

    header_idx: dict = {}
    for v in variables.values():
        edge = _edge_for_role(v.role, v.category, header_idx)
        if edge:
            _add_edge(v, edge, W, H, tracked)

    # ── Proximity constraints ─────────────────────────────────────────────────
    prox_limits = _proximity_limits_from_reqs(reqs)
    prox_pairs  = _collect_proximity_pairs(netlist, components, catalog_pins)

    for cls, pairs in prox_pairs.items():
        D_mm    = prox_limits.get(cls, 8.0)
        D_units = _ceil(D_mm, grid_mm)
        for role_a, role_b, net_name in pairs:
            if role_a not in variables or role_b not in variables:
                continue
            req_ids = [
                r.get("id", "")
                for r in reqs
                if any(
                    kw in ((r.get("statement") or "") + " " + (r.get("parameter") or "")).lower()
                    for kw in ("distance", "proximity", "near", "close")
                )
            ]
            req_id = req_ids[0] if req_ids else f"auto_{cls}"
            _add_proximity(variables[role_a], variables[role_b],
                           D_units, req_id, tracked)

    # ── Objective terms (summed Manhattan pairwise for connected components) ──
    optimize_terms: list[z3.ArithRef] = []
    for net in netlist.get("nets", []):
        pins = net.get("pins", [])
        roles_on_net = [p.get("component_role", "") for p in pins
                        if p.get("component_role", "") in variables]
        for i, ra in enumerate(roles_on_net):
            for rb in roles_on_net[i + 1:]:
                va, vb = variables[ra], variables[rb]
                dx = _center2x(va) - _center2x(vb)
                dy = _center2y(va) - _center2y(vb)
                # Z3 Optimize can minimize a sum of ArithRef expressions;
                # use auxiliary vars to linearize absolute value.
                adx = z3.Int(f"adx_{ra}_{rb}")
                ady = z3.Int(f"ady_{ra}_{rb}")
                # Encode |dx| ≤ adx and |dy| ≤ ady
                tracked.append((z3.And(adx >= dx, adx >= -dx), f"opt_adx:{ra}:{rb}"))
                tracked.append((z3.And(ady >= dy, ady >= -dy), f"opt_ady:{ra}:{rb}"))
                optimize_terms.append(adx + ady)

    return CompiledConstraints(
        variables=variables,
        tracked=tracked,
        grid_mm=grid_mm,
        board_w_units=W,
        board_h_units=H,
        optimize_terms=optimize_terms,
    )
