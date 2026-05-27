"""Assign FGDC lookup-table color keys to GeMS MapUnitPolys symbols."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import arcpy  # type: ignore
except ImportError:  # pragma: no cover
    arcpy = None


FGDC_PALETTES: Dict[str, Sequence[str]] = {
    "quaternary": ("61", "71", "81", "91", "62", "72", "82", "92", "70", "80", "90"),
    "tertiary": ("75", "76", "85", "86", "95", "96", "97", "98", "87", "88"),
    "volcanic": ("33", "34", "35", "43", "44", "45", "54", "55", "56", "145", "155"),
    "serpentinite": ("406", "407", "408", "409", "506", "507", "508", "509"),
    "cretaceous": ("250", "260", "270", "350", "360", "370", "450", "460", "470"),
    "franciscan": ("502", "503", "504", "602", "603", "604", "702", "703", "704"),
    "other": ("122", "123", "124", "223", "224", "323", "324", "423"),
}

VOLCANIC_HINTS = (
    "volcan",
    "basalt",
    "andesite",
    "rhyolite",
    "dacite",
    "tuff",
    "breccia",
    "ignimbrite",
    "agglomerate",
)

FRANCISCAN_HINTS = (
    "kjf",
    "kf",
    "fcs",
    "fr",
)

SERPENTINITE_HINTS = (
    "serp",
    "sp",
)


@dataclass(frozen=True)
class SymbolDecision:
    map_unit: str
    family: str
    symbol: str
    source: str


def normalize_mapunit(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", value.strip())


def stable_pick(options: Sequence[str], key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(options)
    return options[index]


def load_overrides(csv_path: Optional[str]) -> Dict[str, str]:
    if not csv_path:
        return {}

    overrides: Dict[str, str] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            map_unit = normalize_mapunit(row.get("MapUnit"))
            symbol = (row.get("Symbol") or "").strip()
            if map_unit and symbol:
                overrides[map_unit.lower()] = symbol
    return overrides


def looks_like_serpentinite(unit: str) -> bool:
    lowered = unit.lower()
    if lowered in {"sp", "spm", "sps"}:
        return True
    return any(token in lowered for token in SERPENTINITE_HINTS)


def looks_like_franciscan(unit: str) -> bool:
    lowered = unit.lower()
    if lowered.startswith(("kjf", "jf")):
        return True
    return any(lowered.startswith(token) for token in FRANCISCAN_HINTS)


def looks_like_volcanic(unit: str) -> bool:
    lowered = unit.lower()
    if re.match(r"^[qtk][a-z]*v[a-z]*$", lowered):
        return True
    if lowered.endswith(("v", "vb", "vt", "rv")):
        return True
    return any(token in lowered for token in VOLCANIC_HINTS)


def classify_map_unit(map_unit: str) -> str:
    unit = normalize_mapunit(map_unit)
    lowered = unit.lower()

    if not lowered:
        return "other"
    if looks_like_serpentinite(unit):
        return "serpentinite"
    if looks_like_franciscan(unit):
        return "franciscan"
    if looks_like_volcanic(unit):
        return "volcanic"
    if lowered.startswith("q"):
        return "quaternary"
    if lowered.startswith("t") and not lowered.startswith("tr"):
        return "tertiary"
    if lowered.startswith("k"):
        return "cretaceous"
    return "other"


def choose_symbol(map_unit: str, overrides: Optional[Dict[str, str]] = None) -> SymbolDecision:
    normalized = normalize_mapunit(map_unit)
    lowered = normalized.lower()

    if overrides and lowered in overrides:
        return SymbolDecision(normalized, "override", overrides[lowered], "override")

    family = classify_map_unit(normalized)
    symbol = stable_pick(FGDC_PALETTES[family], lowered or "other")
    return SymbolDecision(normalized, family, symbol, "palette")


def iter_decisions(
    map_units: Iterable[Optional[str]],
    overrides: Optional[Dict[str, str]] = None,
) -> List[SymbolDecision]:
    return [choose_symbol(value or "", overrides) for value in map_units]


def update_feature_class(
    feature_class: str,
    mapunit_field: str = "MapUnit",
    symbol_field: str = "Symbol",
    override_csv: Optional[str] = None,
) -> Tuple[int, Dict[str, int]]:
    if arcpy is None:  # pragma: no cover
        raise RuntimeError("arcpy is required to update a feature class.")

    overrides = load_overrides(override_csv)
    counts: Dict[str, int] = {}
    updated = 0

    with arcpy.da.UpdateCursor(feature_class, [mapunit_field, symbol_field]) as cursor:
        for row in cursor:
            decision = choose_symbol(row[0], overrides)
            row[1] = decision.symbol
            cursor.updateRow(row)
            updated += 1
            counts[decision.family] = counts.get(decision.family, 0) + 1

    return updated, counts


def format_summary(counts: Dict[str, int]) -> str:
    if not counts:
        return "No rows updated."
    parts = [f"{family}={count}" for family, count in sorted(counts.items())]
    return ", ".join(parts)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_class", help="Path to the MapUnitPolys feature class")
    parser.add_argument("--mapunit-field", default="MapUnit")
    parser.add_argument("--symbol-field", default="Symbol")
    parser.add_argument("--override-csv")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview classification decisions from a text file with one MapUnit per line.",
    )
    return parser


def preview_from_file(path: str, override_csv: Optional[str]) -> int:
    overrides = load_overrides(override_csv)
    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            unit = raw_line.strip()
            if not unit:
                continue
            if "," in unit:
                unit = unit.split(",", 1)[0].strip()
            if unit.lower() == "mapunit":
                continue
            decision = choose_symbol(unit, overrides)
            print(f"{decision.map_unit},{decision.family},{decision.symbol},{decision.source}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.preview:
        return preview_from_file(args.feature_class, args.override_csv)

    if arcpy is None:
        parser.error("arcpy is not available. Use this script inside an ArcGIS Python environment.")

    updated, counts = update_feature_class(
        feature_class=args.feature_class,
        mapunit_field=args.mapunit_field,
        symbol_field=args.symbol_field,
        override_csv=args.override_csv,
    )

    message = f"Updated {updated} rows. {format_summary(counts)}"
    if arcpy is not None:
        arcpy.AddMessage(message)
    else:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
