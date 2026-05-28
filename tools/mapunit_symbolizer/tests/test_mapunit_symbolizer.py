import unittest

from tools.mapunit_symbolizer import mapunit_symbolizer


class FakeValue(object):
    def __init__(self, field_values):
        self.fieldValues = field_values


class FakeSymbol(object):
    def __init__(self, name=""):
        self.name = name


class FakeItem(object):
    def __init__(self, label="", description="", values=None, symbol_name=""):
        self.label = label
        self.description = description
        self.values = values or []
        self.symbol = FakeSymbol(symbol_name)


class FakeGroup(object):
    def __init__(self, items):
        self.items = items


class MapUnitSymbolizerTests(unittest.TestCase):
    def test_quaternary_unit_maps_to_quaternary_family(self):
        decision = mapunit_symbolizer.choose_symbol("Qal")
        self.assertEqual(decision.family, "quaternary")
        self.assertIn(decision.symbol, mapunit_symbolizer.FGDC_PALETTES["quaternary"])

    def test_tertiary_unit_avoids_triassic_collision(self):
        self.assertEqual(mapunit_symbolizer.classify_map_unit("Tgr"), "tertiary")
        self.assertEqual(mapunit_symbolizer.classify_map_unit("Tr"), "other")

    def test_serpentinite_takes_priority(self):
        decision = mapunit_symbolizer.choose_symbol("sp")
        self.assertEqual(decision.family, "serpentinite")

    def test_franciscan_takes_priority_over_cretaceous(self):
        decision = mapunit_symbolizer.choose_symbol("KJf")
        self.assertEqual(decision.family, "franciscan")

    def test_volcanic_units_are_detected_before_age_family(self):
        decision = mapunit_symbolizer.choose_symbol("Tv")
        self.assertEqual(decision.family, "volcanic")

    def test_override_wins(self):
        decision = mapunit_symbolizer.choose_symbol("Qal", overrides={"qal": "71"})
        self.assertEqual(decision.family, "override")
        self.assertEqual(decision.symbol, "71")

    def test_extract_code_uses_regex_group(self):
        code = mapunit_symbolizer.extract_code("Qal | 603", r"\|\s*([A-Z0-9]+)$")
        self.assertEqual(code, "603")

    def test_build_symbol_lookup_from_renderer_reads_label_codes(self):
        groups = [
            FakeGroup(
                [
                    FakeItem(label="71", values=[FakeValue(["Qal"])]),
                    FakeItem(label="603", values=[FakeValue(["KJf"])]),
                ]
            )
        ]
        lookup = mapunit_symbolizer.build_symbol_lookup_from_renderer(
            fields=["MapUnit"],
            groups=groups,
            value_field="MapUnit",
            code_source="LABEL",
        )
        self.assertEqual(lookup["qal"], "71")
        self.assertEqual(lookup["kjf"], "603")

    def test_build_symbol_lookup_from_renderer_can_use_symbol_name(self):
        groups = [FakeGroup([FakeItem(values=[FakeValue(["sp"])], symbol_name="408")])]
        lookup = mapunit_symbolizer.build_symbol_lookup_from_renderer(
            fields=["MapUnit"],
            groups=groups,
            value_field="MapUnit",
            code_source="SYMBOL_NAME",
        )
        self.assertEqual(lookup["sp"], "408")

    def test_extract_mapunits_from_renderer(self):
        groups = [
            FakeGroup(
                [
                    FakeItem(values=[FakeValue(["Qal"])]),
                    FakeItem(values=[FakeValue(["act"])]),
                ]
            )
        ]
        map_units = mapunit_symbolizer.extract_mapunits_from_renderer(
            fields=["MapUnit"],
            groups=groups,
            value_field="MapUnit",
        )
        self.assertEqual(map_units, ["act", "Qal"])

    def test_compare_template_to_lookup_reports_missing_csv_values(self):
        missing, extra = mapunit_symbolizer.compare_template_to_lookup(
            template_mapunits=["act", "Qal"],
            symbol_lookup={"qal": "71", "sp": "408"},
        )
        self.assertEqual(missing, ["act"])
        self.assertEqual(extra, ["sp"])


if __name__ == "__main__":
    unittest.main()
