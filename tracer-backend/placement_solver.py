"""Z3-backed placement solver for MCU breakout boards.

Reads a CompiledConstraints object (from placement_constraints.compile_constraints),
asserts the labeled constraints, and solves.

SAT  → extracts the Z3 model and returns component positions in mm + grid units.
UNSAT → attempts a group-level UNSAT core by relaxing constraint families one at a
        time to identify which family makes the problem infeasible.
Timeout → reported as "timeout" status (treated like infeasible by the pipeline).

All solver state is local to solve(); there is no global mutable solver object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import z3

from placement_constraints import CompiledConstraints, PlacementVars


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class SolverResult:
    status: str                             # "placed" | "infeasible" | "timeout"
    positions: Optional[dict[str, dict]]    # role → placement dict (mm + deg)
    unsat_reason: Optional[str]
    unsat_groups: list[str] = field(default_factory=list)
    objective_value: Optional[float] = None


# ── Model extraction ──────────────────────────────────────────────────────────

def _extract_positions(
    model: z3.ModelRef,
    variables: dict[str, PlacementVars],
    grid_mm: float,
    req_map: dict[str, list[str]],
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for role, v in variables.items():
        x_u   = model.eval(v.x,   model_completion=True).as_long()
        y_u   = model.eval(v.y,   model_completion=True).as_long()
        rot_u = model.eval(v.rot, model_completion=True).as_long()
        rot_u = max(0, min(3, rot_u))  # clamp to valid range
        if rot_u in (0, 2):
            ew_u, eh_u = v.w_units, v.h_units
        else:
            ew_u, eh_u = v.h_units, v.w_units
        result[role] = {
            "functional_role": role,
            "part_id": v.part_id,
            "x_mm": round(x_u * grid_mm, 3),
            "y_mm": round(y_u * grid_mm, 3),
            "rotation_deg": rot_u * 90,
            "width_mm":  round(ew_u * grid_mm, 3),
            "height_mm": round(eh_u * grid_mm, 3),
            "satisfies_requirement_ids": v.satisfies_requirement_ids,
        }
    return result


# ── UNSAT core analysis ───────────────────────────────────────────────────────

_CONSTRAINT_FAMILIES = ("rotation", "boundary", "nooverlap", "edge", "proximity", "opt_adx", "opt_ady")


def _group_of(label: str) -> str:
    for fam in _CONSTRAINT_FAMILIES:
        if label.startswith(fam + ":") or label == fam:
            return fam
    return "unknown"


def _groups_in_core(core: list) -> list[str]:
    return sorted({_group_of(str(c)) for c in core})


def _get_unsat_reason(
    tracked: list[tuple[z3.BoolRef, str]],
    timeout_ms: int,
) -> tuple[str, list[str]]:
    """Return (human-readable reason, list of group names) by probing constraint families.

    Strategy: try solving with successively more constraint families until we find
    the one that tips the problem into UNSAT. This is O(#families × solve_time) but
    gives a clear, actionable diagnosis without requiring Z3 unsat_core mode.
    """
    grouped: dict[str, list[tuple[z3.BoolRef, str]]] = {}
    for fmla, label in tracked:
        g = _group_of(label)
        grouped.setdefault(g, []).append((fmla, label))

    ordered_families = [f for f in _CONSTRAINT_FAMILIES if f in grouped]
    cumulative: list[tuple[z3.BoolRef, str]] = []
    culprit: list[str] = []

    for fam in ordered_families:
        cumulative.extend(grouped[fam])
        s = z3.Solver()
        s.set("timeout", timeout_ms // len(ordered_families))
        for fmla, label in cumulative:
            s.assert_and_track(fmla, z3.Bool(label))
        result = s.check()
        if result == z3.unsat:
            culprit.append(fam)
            # For proximity, try to get per-constraint details
            if fam == "proximity":
                core_labels = [str(c) for c in s.unsat_core()]
                prox_labels = [l for l in core_labels if l.startswith("proximity:")]
                if prox_labels:
                    detail = "; ".join(prox_labels[:5])
                    return (
                        f"Proximity constraints are unsatisfiable — check board size or "
                        f"reduce distance requirements. Affected: {detail}",
                        culprit,
                    )
            return (
                f"Constraint family '{fam}' makes the placement infeasible. "
                f"This typically means {'board is too small for all components' if fam == 'nooverlap' else 'the ' + fam + ' constraints conflict with each other or with the board size'}.",
                culprit,
            )

    return ("Constraints are jointly unsatisfiable (no single family identified).", [])


# ── Public solver ─────────────────────────────────────────────────────────────

def solve(
    compiled: CompiledConstraints,
    optimize: bool = False,
    timeout_ms: int = 30_000,
) -> SolverResult:
    """Solve the compiled placement constraints.

    Parameters
    ----------
    compiled   : output of placement_constraints.compile_constraints()
    optimize   : if True, minimise summed Manhattan distance between connected
                 component centres (uses Z3 Optimize instead of plain Solver)
    timeout_ms : solver wall-clock timeout in milliseconds

    Returns
    -------
    SolverResult with status "placed", "infeasible", or "timeout"
    """
    req_map: dict[str, list[str]] = {}  # placeholder for future traced req IDs

    if optimize and compiled.optimize_terms:
        solver: z3.Solver | z3.Optimize = z3.Optimize()
        obj_sum = z3.Sum(compiled.optimize_terms)
        cast_optimize = True
    else:
        solver = z3.Solver()
        cast_optimize = False

    solver.set("timeout", timeout_ms)

    # Assert all tracked constraints; use assert_and_track for potential core extraction.
    for fmla, label in compiled.tracked:
        solver.assert_and_track(fmla, z3.Bool(label))

    if cast_optimize:
        solver.minimize(obj_sum)  # type: ignore[union-attr]

    result = solver.check()

    # ── SAT ──────────────────────────────────────────────────────────────────
    if result == z3.sat:
        model = solver.model()
        obj_val: Optional[float] = None
        if cast_optimize:
            try:
                obj_val = float(solver.lower(obj_sum).as_fraction())  # type: ignore[union-attr]
            except Exception:
                pass
        positions = _extract_positions(
            model, compiled.variables, compiled.grid_mm, req_map
        )
        return SolverResult(
            status="placed",
            positions=positions,
            unsat_reason=None,
            objective_value=obj_val,
        )

    # ── Timeout ───────────────────────────────────────────────────────────────
    if result == z3.unknown:
        return SolverResult(
            status="timeout",
            positions=None,
            unsat_reason=(
                f"Z3 solver timed out after {timeout_ms} ms. "
                "Try increasing the board size, relaxing proximity constraints, "
                "or reducing the number of components."
            ),
        )

    # ── UNSAT ─────────────────────────────────────────────────────────────────
    reason, groups = _get_unsat_reason(compiled.tracked, timeout_ms)
    return SolverResult(
        status="infeasible",
        positions=None,
        unsat_reason=reason,
        unsat_groups=groups,
    )
