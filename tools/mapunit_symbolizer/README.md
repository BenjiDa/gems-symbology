# MapUnit Symbolizer

This tool updates the `Symbol` field in a GeMS `MapUnitPolys` feature class by inferring a color family from each polygon's `MapUnit` value and assigning an FGDC generic lookup-table key.

There are now two workflows:

- `Assign Symbols From Layer File`: preferred when you already have a curated `.lyrx`
- `Assign MapUnit Symbols`: fallback heuristic assignment based on MapUnit naming

The default palette follows common USGS/FGDC age-color conventions:

- `Q` units use yellow shades
- `T` units use orange shades
- volcanic units use pink or buff shades
- serpentinite uses purple shades
- `K` units use green shades
- Franciscan-related Cretaceous units use blue shades

The defaults are intentionally heuristic. Local abbreviations vary a lot, so the tool also supports an override CSV for map-specific control.

## Files

- `MapUnitSymbolizer.pyt`: ArcGIS Python toolbox you can add directly in ArcGIS Pro
- `mapunit_symbolizer.py`: core classification and update logic
- `overrides.example.csv`: example manual overrides for specific map units

## ArcGIS Pro Usage

1. Copy the `tools/mapunit_symbolizer` folder to your Windows machine.
2. In ArcGIS Pro, add `MapUnitSymbolizer.pyt` as a toolbox.
3. Run `Assign MapUnit Symbols`.
4. Set:
   - `Input MapUnitPolys`
   - `MapUnit Field` if different from `MapUnit`
   - `Symbol Field` if different from `Symbol`
   - `Override CSV` if you want exact unit-to-symbol assignments

## Layer File Workflow

Use `Assign Symbols From Layer File` when you have a `.lyrx` that already has the right unique-value symbology for your map units.

Expected template setup:

1. The template layer uses a `Unique Value` renderer.
2. One of the renderer fields is `MapUnit` or another field you specify as `Template Value Field`.
3. Each class stores the FGDC symbol code in one of these places:
   - class label
   - class description
   - symbol name

Recommended first attempt:

- `Template Value Field`: `MapUnit`
- `FGDC Code Source In Template`: `LABEL`
- `FGDC Code Pattern`: `([A-Z0-9]+)`

Example labels that work well:

- `71`
- `603`
- `Qal | 71` with a more specific pattern such as `\\|\\s*([A-Z0-9]+)$`
- `FGDC 603`

## Override CSV

CSV format:

```csv
MapUnit,Symbol
Qal,71
Qoa,61
KJf,603
sp,408
```

Overrides take priority over the built-in heuristics.

## Notes

- The `Symbol` field is populated with the FGDC generic lookup key, not an RGB value.
- The selected codes come from the FGDC digital geologic color chart and are grouped into practical palettes for each unit family.
- If you later want this to also build a layer file or apply a full ArcGIS symbology renderer, we can add that as the next step.
- The layer-file workflow is usually the better fit once you have an approved cartographic template.

## Lock Errors

If ArcGIS Pro reports `RuntimeError: Cannot acquire a lock`, the tool usually cannot get edit access to `MapUnitPolys`.

Common fixes:

1. Close the attribute table for `MapUnitPolys`.
2. Remove any joins or relates from the layer.
3. Stop any active edit session touching the same geodatabase.
4. Make sure the same geodatabase is not open in another ArcGIS Pro project or ArcMap session.
5. If the data is on a network share, copy it to a local file geodatabase and try again.
6. If you passed in a layer from the current map, try browsing directly to the feature class in the geodatabase instead.
