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
        self.tools = [AssignSymbolsFromLayerFile, AssignMapUnitSymbols]


class AssignSymbolsFromLayerFile(object):
    def __init__(self):
        self.label = "Assign Symbols From Layer File"
        self.description = (
            "Populate the Symbol field in MapUnitPolys by reading MapUnit-to-symbol mappings "
            "from a predefined .lyrx unique-value renderer."
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

        code_source = arcpy.Parameter(
            displayName="FGDC Code Source In Template",
            name="code_source",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        code_source.filter.list = ["AUTO", "LABEL", "DESCRIPTION", "SYMBOL_NAME"]
        code_source.value = "AUTO"

        code_pattern = arcpy.Parameter(
            displayName="FGDC Code Pattern",
            name="code_pattern",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        code_pattern.value = r"([A-Z0-9]+)"

        return [
            input_fc,
            layer_file,
            layer_name,
            template_value_field,
            mapunit_field,
            symbol_field,
            code_source,
            code_pattern,
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import arcpy

        input_fc = parameters[0].valueAsText
        layer_file = parameters[1].valueAsText
        layer_name = parameters[2].valueAsText or None
        template_value_field = parameters[3].valueAsText or "MapUnit"
        mapunit_field = parameters[4].valueAsText or "MapUnit"
        symbol_field = parameters[5].valueAsText or "Symbol"
        code_source = parameters[6].valueAsText or "AUTO"
        code_pattern = parameters[7].valueAsText or None

        try:
            updated, unmatched, resolved_layer_name = mapunit_symbolizer.update_feature_class_from_layerfile(
                feature_class=input_fc,
                layer_file_path=layer_file,
                mapunit_field=mapunit_field,
                symbol_field=symbol_field,
                template_value_field=template_value_field,
                layer_name=layer_name,
                code_source=code_source,
                code_pattern=code_pattern,
            )
        except RuntimeError as exc:
            arcpy.AddError(str(exc))
            raise

        arcpy.AddMessage(f"Template layer: {resolved_layer_name}")
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

        input_fc = parameters[0].valueAsText
        mapunit_field = parameters[1].valueAsText or "MapUnit"
        symbol_field = parameters[2].valueAsText or "Symbol"
        override_csv = parameters[3].valueAsText or None

        try:
            updated, counts = mapunit_symbolizer.update_feature_class(
                feature_class=input_fc,
                mapunit_field=mapunit_field,
                symbol_field=symbol_field,
                override_csv=override_csv,
            )
        except RuntimeError as exc:
            arcpy.AddError(str(exc))
            raise

        arcpy.AddMessage(f"Updated {updated} rows.")
        arcpy.AddMessage(mapunit_symbolizer.format_summary(counts))
