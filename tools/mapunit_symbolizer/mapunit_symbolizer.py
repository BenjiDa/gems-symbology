"""Assign FGDC lookup-table color keys to GeMS MapUnitPolys symbols."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

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


def get_string_attr(obj: Any, attr_name: str) -> str:
    value = getattr(obj, attr_name, "")
    if value is None:
        return ""
    return str(value).strip()


def extract_code(candidate: str, code_pattern: Optional[str] = None) -> str:
    text = (candidate or "").strip()
    if not text:
        return ""
    if not code_pattern:
        return text
    match = re.search(code_pattern, text)
    if not match:
        return ""
    if match.groups():
        return (match.group(1) or "").strip()
    return match.group(0).strip()


def flatten_item_value(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (str, int, float)):
        return [str(value).strip()]
    if isinstance(value, dict):
        if "fieldValues" in value:
            results: List[str] = []
            for item in value.get("fieldValues", []):
                results.extend(flatten_item_value(item))
            return results
        if "values" in value:
            results = []
            for item in value.get("values", []):
                results.extend(flatten_item_value(item))
            return results
        if "value" in value:
            return flatten_item_value(value.get("value"))
        return []

    if hasattr(value, "fieldValues"):
        results = []
        for item in getattr(value, "fieldValues", []):
            results.extend(flatten_item_value(item))
        return results
    if hasattr(value, "values"):
        results = []
        for item in getattr(value, "values", []):
            results.extend(flatten_item_value(item))
        return results
    if hasattr(value, "value"):
        return flatten_item_value(getattr(value, "value"))
    return []


def item_mapunit_values(item: Any, field_index: int = 0) -> List[str]:
    values = getattr(item, "values", []) or []
    map_units: List[str] = []

    for raw_value in values:
        flattened = flatten_item_value(raw_value)
        if not flattened:
            continue
        if field_index < len(flattened):
            candidate = normalize_mapunit(flattened[field_index])
        else:
            candidate = normalize_mapunit(flattened[0])
        if candidate:
            map_units.append(candidate)

    return map_units


def item_symbol_name(item: Any) -> str:
    symbol = getattr(item, "symbol", None)
    if symbol is None:
        return ""
    return get_string_attr(symbol, "name")


def resolve_item_symbol_code(
    item: Any,
    code_source: str = "AUTO",
    code_pattern: Optional[str] = None,
) -> str:
    normalized_source = (code_source or "AUTO").upper()
    candidates: List[str]

    if normalized_source == "LABEL":
        candidates = [get_string_attr(item, "label")]
    elif normalized_source == "DESCRIPTION":
        candidates = [get_string_attr(item, "description")]
    elif normalized_source == "SYMBOL_NAME":
        candidates = [item_symbol_name(item)]
    else:
        candidates = [
            get_string_attr(item, "label"),
            get_string_attr(item, "description"),
            item_symbol_name(item),
        ]

    for candidate in candidates:
        code = extract_code(candidate, code_pattern)
        if code:
            return code
    return ""


def build_symbol_lookup_from_renderer(
    fields: Sequence[str],
    groups: Sequence[Any],
    value_field: str = "MapUnit",
    code_source: str = "AUTO",
    code_pattern: Optional[str] = None,
) -> Dict[str, str]:
    if not fields:
        raise RuntimeError("The template layer does not define any unique value fields.")

    lowered_fields = [field.lower() for field in fields]
    try:
        field_index = lowered_fields.index(value_field.lower())
    except ValueError as exc:
        raise RuntimeError(
            f"The template layer is not symbolized on the requested value field: {value_field}"
        ) from exc

    lookup: Dict[str, str] = {}

    for group in groups:
        for item in getattr(group, "items", []) or []:
            code = resolve_item_symbol_code(item, code_source=code_source, code_pattern=code_pattern)
            if not code:
                item_label = get_string_attr(item, "label") or "<blank>"
                source_name = {
                    "LABEL": "class label",
                    "DESCRIPTION": "class description",
                    "SYMBOL_NAME": "symbol name",
                    "AUTO": "class label, class description, or symbol name",
                }.get((code_source or "AUTO").upper(), "class metadata")
                pattern_text = code_pattern or "<none>"
                raise RuntimeError(
                    "Could not determine an FGDC code from a symbology class. "
                    f"Class label: {item_label}. "
                    f"The tool looked in the {source_name} using pattern '{pattern_text}'. "
                    "Make sure the FGDC code is stored there in the .lyrx class."
                )

            for map_unit in item_mapunit_values(item, field_index):
                key = map_unit.lower()
                if key in lookup and lookup[key] != code:
                    raise RuntimeError(
                        f"Conflicting FGDC codes found for MapUnit '{map_unit}': "
                        f"{lookup[key]} and {code}"
                    )
                lookup[key] = code

    if not lookup:
        raise RuntimeError("No MapUnit-to-Symbol mappings were found in the template layer.")

    return lookup


def load_layerfile_renderer(
    layer_file_path: str,
    layer_name: Optional[str] = None,
) -> Tuple[Sequence[str], Sequence[Any], str]:
    if arcpy is None:  # pragma: no cover
        raise RuntimeError("arcpy is required to read ArcGIS layer files.")

    layer_file = arcpy.mp.LayerFile(layer_file_path)
    layers = layer_file.listLayers()
    if not layers:
        raise RuntimeError(f"No layers were found in layer file: {layer_file_path}")

    selected_layer = None
    if layer_name:
        for layer in layers:
            if layer.name == layer_name or layer.longName == layer_name:
                selected_layer = layer
                break
        if selected_layer is None:
            raise RuntimeError(f"Layer '{layer_name}' was not found in {layer_file_path}")
    else:
        for layer in layers:
            if getattr(layer, "isFeatureLayer", False):
                selected_layer = layer
                break
        if selected_layer is None:
            selected_layer = layers[0]

    symbology = selected_layer.symbology
    renderer = getattr(symbology, "renderer", None)
    if renderer is None or getattr(renderer, "type", "") != "UniqueValueRenderer":
        raise RuntimeError(
            "The template .lyrx must use a Unique Value renderer so MapUnit values can be matched."
        )

    return renderer.fields, renderer.groups, selected_layer.name


def validate_feature_class(
    feature_class: str,
    mapunit_field: str,
    symbol_field: str,
) -> str:
    if arcpy is None:  # pragma: no cover
        raise RuntimeError("arcpy is required to validate a feature class.")

    if not arcpy.Exists(feature_class):
        raise RuntimeError(f"Input feature class does not exist: {feature_class}")

    desc = arcpy.Describe(feature_class)
    catalog_path = getattr(desc, "catalogPath", feature_class)

    field_names = {field.name.lower() for field in arcpy.ListFields(feature_class)}
    missing_fields = [
        field_name
        for field_name in (mapunit_field, symbol_field)
        if field_name.lower() not in field_names
    ]
    if missing_fields:
        raise RuntimeError(
            "Missing required field(s): " + ", ".join(missing_fields)
        )

    if not arcpy.TestSchemaLock(catalog_path):
        raise RuntimeError(
            "Cannot acquire a lock on the input feature class. "
            "Close any open attribute tables, stop editing the layer elsewhere, "
            "remove joins/relates, and make sure the dataset is not open in another ArcGIS session."
        )

    return catalog_path


def update_feature_class(
    feature_class: str,
    mapunit_field: str = "MapUnit",
    symbol_field: str = "Symbol",
    override_csv: Optional[str] = None,
) -> Tuple[int, Dict[str, int]]:
    if arcpy is None:  # pragma: no cover
        raise RuntimeError("arcpy is required to update a feature class.")

    feature_class = validate_feature_class(feature_class, mapunit_field, symbol_field)
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


def update_feature_class_from_lookup(
    feature_class: str,
    symbol_lookup: Dict[str, str],
    mapunit_field: str = "MapUnit",
    symbol_field: str = "Symbol",
    only_update_matches: bool = True,
) -> Tuple[int, int]:
    if arcpy is None:  # pragma: no cover
        raise RuntimeError("arcpy is required to update a feature class.")

    feature_class = validate_feature_class(feature_class, mapunit_field, symbol_field)
    updated = 0
    unmatched = 0

    with arcpy.da.UpdateCursor(feature_class, [mapunit_field, symbol_field]) as cursor:
        for row in cursor:
            map_unit = normalize_mapunit(row[0])
            symbol = symbol_lookup.get(map_unit.lower())
            if symbol:
                row[1] = symbol
                cursor.updateRow(row)
                updated += 1
            elif not only_update_matches:
                row[1] = None
                cursor.updateRow(row)
                unmatched += 1
            else:
                unmatched += 1

    return updated, unmatched


def update_feature_class_from_layerfile(
    feature_class: str,
    layer_file_path: str,
    mapunit_field: str = "MapUnit",
    symbol_field: str = "Symbol",
    template_value_field: str = "MapUnit",
    layer_name: Optional[str] = None,
    code_source: str = "AUTO",
    code_pattern: Optional[str] = None,
) -> Tuple[int, int, str]:
    fields, groups, resolved_layer_name = load_layerfile_renderer(layer_file_path, layer_name)
    lookup = build_symbol_lookup_from_renderer(
        fields=fields,
        groups=groups,
        value_field=template_value_field,
        code_source=code_source,
        code_pattern=code_pattern,
    )
    updated, unmatched = update_feature_class_from_lookup(
        feature_class=feature_class,
        symbol_lookup=lookup,
        mapunit_field=mapunit_field,
        symbol_field=symbol_field,
    )
    return updated, unmatched, resolved_layer_name


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
