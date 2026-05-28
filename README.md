# GeMS Symbology Tools

This repository is for small, independent utilities that support GeMS-based mapping workflows.

## Tools

### MapUnit Symbolizer

Assigns FGDC color lookup keys to the `Symbol` field in `MapUnitPolys` based on `MapUnit`.

- Target environment: ArcGIS on Windows
- Input: GeMS `MapUnitPolys` feature class
- Primary fields: `MapUnit`, `Symbol`
- Output: updated `Symbol` values using FGDC generic lookup codes
- Preferred workflow: read `MapUnit` classes from a curated `.lyrx` and exact symbol values from a CSV

See [tools/mapunit_symbolizer/README.md](/Users/benmelosh/Code/Current/gems-symbology/tools/mapunit_symbolizer/README.md).
