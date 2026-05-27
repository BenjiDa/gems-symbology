import os
import sys


TOOL_DIR = os.path.dirname(__file__)
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

import mapunit_symbolizer


class Toolbox(object):
    def __init__(self):
        self.label = "GeMS Symbology Tools"
        self.alias = "gems_symbology"
        self.tools = [AssignMapUnitSymbols]


class AssignMapUnitSymbols(object):
    def __init__(self):
        self.label = "Assign MapUnit Symbols"
        self.description = (
            "Populate the Symbol field in MapUnitPolys using FGDC color lookup keys "
            "chosen from the MapUnit value."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        import arcpy

        input_fc = arcpy.Parameter(
            displayName="Input MapUnitPolys",
            name="input_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
        )

        mapunit_field = arcpy.Parameter(
            displayName="MapUnit Field",
            name="mapunit_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        mapunit_field.parameterDependencies = [input_fc.name]
        mapunit_field.value = "MapUnit"

        symbol_field = arcpy.Parameter(
            displayName="Symbol Field",
            name="symbol_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        symbol_field.parameterDependencies = [input_fc.name]
        symbol_field.value = "Symbol"

        override_csv = arcpy.Parameter(
            displayName="Override CSV",
            name="override_csv",
            datatype="DEFile",
            parameterType="Optional",
            direction="Input",
        )
        override_csv.filter.list = ["csv"]

        return [input_fc, mapunit_field, symbol_field, override_csv]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import arcpy

        input_fc = parameters[0].valueAsText
        mapunit_field = parameters[1].valueAsText or "MapUnit"
        symbol_field = parameters[2].valueAsText or "Symbol"
        override_csv = parameters[3].valueAsText or None

        updated, counts = mapunit_symbolizer.update_feature_class(
            feature_class=input_fc,
            mapunit_field=mapunit_field,
            symbol_field=symbol_field,
            override_csv=override_csv,
        )

        arcpy.AddMessage(f"Updated {updated} rows.")
        arcpy.AddMessage(mapunit_symbolizer.format_summary(counts))
