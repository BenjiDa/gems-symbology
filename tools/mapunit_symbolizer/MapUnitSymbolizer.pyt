import importlib
import os
import sys


TOOL_DIR = os.path.dirname(__file__)
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

import mapunit_symbolizer


def load_symbolizer_module():
    module = importlib.reload(mapunit_symbolizer)
    expected_attrs = (
        "update_feature_class",
        "update_feature_class_from_layerfile_and_csv",
        "format_summary",
    )
    missing = [attr for attr in expected_attrs if not hasattr(module, attr)]
    if missing:
        raise RuntimeError(
            "ArcGIS Pro appears to have loaded a stale copy of mapunit_symbolizer.py. "
            "Close the toolbox, remove and re-add MapUnitSymbolizer.pyt, or restart ArcGIS Pro. "
            "Missing attribute(s): " + ", ".join(missing)
        )
    return module


class Toolbox(object):
    def __init__(self):
        self.label = "GeMS Symbology Tools"
        self.alias = "gems_symbology"
        self.tools = [AssignSymbolsFromLayerFile, AssignMapUnitSymbols]


class AssignSymbolsFromLayerFile(object):
    def __init__(self):
        self.label = "Assign Symbols From Layer File And CSV"
        self.description = (
            "Populate the Symbol field in MapUnitPolys by validating MapUnit classes against "
            "a predefined .lyrx unique-value renderer and reading exact Symbol values from a CSV."
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

        layer_file = arcpy.Parameter(
            displayName="Template Layer File",
            name="layer_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        layer_file.filter.list = ["lyrx", "lyr"]

        layer_name = arcpy.Parameter(
            displayName="Template Layer Name",
            name="layer_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        template_value_field = arcpy.Parameter(
            displayName="Template Value Field",
            name="template_value_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        template_value_field.value = "MapUnit"

        lookup_csv = arcpy.Parameter(
            displayName="MapUnit Symbol CSV",
            name="lookup_csv",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        lookup_csv.filter.list = ["csv"]

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

        csv_mapunit_field = arcpy.Parameter(
            displayName="CSV MapUnit Column",
            name="csv_mapunit_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        csv_mapunit_field.value = "MapUnit"

        csv_symbol_field = arcpy.Parameter(
            displayName="CSV Symbol Column",
            name="csv_symbol_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        csv_symbol_field.value = "Symbol"

        return [
            input_fc,
            layer_file,
            layer_name,
            template_value_field,
            lookup_csv,
            mapunit_field,
            symbol_field,
            csv_mapunit_field,
            csv_symbol_field,
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import arcpy

        symbolizer = load_symbolizer_module()
        input_fc = parameters[0].valueAsText
        layer_file = parameters[1].valueAsText
        layer_name = parameters[2].valueAsText or None
        template_value_field = parameters[3].valueAsText or "MapUnit"
        lookup_csv = parameters[4].valueAsText
        mapunit_field = parameters[5].valueAsText or "MapUnit"
        symbol_field = parameters[6].valueAsText or "Symbol"
        csv_mapunit_field = parameters[7].valueAsText or "MapUnit"
        csv_symbol_field = parameters[8].valueAsText or "Symbol"

        try:
            updated, unmatched, resolved_layer_name, template_count = symbolizer.update_feature_class_from_layerfile_and_csv(
                feature_class=input_fc,
                layer_file_path=layer_file,
                csv_path=lookup_csv,
                mapunit_field=mapunit_field,
                symbol_field=symbol_field,
                template_value_field=template_value_field,
                layer_name=layer_name,
                csv_mapunit_field=csv_mapunit_field,
                csv_symbol_field=csv_symbol_field,
            )
        except RuntimeError as exc:
            arcpy.AddError(str(exc))
            raise

        arcpy.AddMessage(f"Template layer: {resolved_layer_name}")
        arcpy.AddMessage(f"Template MapUnit classes: {template_count}")
        arcpy.AddMessage(f"Updated {updated} rows.")
        arcpy.AddMessage(f"Rows with no template match: {unmatched}")


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

        symbolizer = load_symbolizer_module()
        input_fc = parameters[0].valueAsText
        mapunit_field = parameters[1].valueAsText or "MapUnit"
        symbol_field = parameters[2].valueAsText or "Symbol"
        override_csv = parameters[3].valueAsText or None

        try:
            updated, counts = symbolizer.update_feature_class(
                feature_class=input_fc,
                mapunit_field=mapunit_field,
                symbol_field=symbol_field,
                override_csv=override_csv,
            )
        except RuntimeError as exc:
            arcpy.AddError(str(exc))
            raise

        arcpy.AddMessage(f"Updated {updated} rows.")
        arcpy.AddMessage(symbolizer.format_summary(counts))
