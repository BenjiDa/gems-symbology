import unittest

from tools.mapunit_symbolizer import mapunit_symbolizer


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


if __name__ == "__main__":
    unittest.main()
