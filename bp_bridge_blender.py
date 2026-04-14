from numpy.distutils.system_info import lapack_ilp64_opt_info

bl_info = {
    "name": "Blender Painter Bridge",
    "author": "Jelena Rombouts",
    "version": (1,0),
    "blender": (4,4,3),
    "location": "View3d > Tool",
    "wiki_url": "https://www.artstation.com/jelenarombouts2",
    "category": "Import-Export"
    }

import bpy
from bpy_extras import bmesh_utils
import bmesh
import os
import subprocess

from mathutils import Vector
import json

CONFIG = {
            "bbox_threshold": 10,
            "uv_islands_threshold": 2
}

class LoadConfig(bpy.types.Operator):
    bl_idname = "bl.load_config"
    bl_label = "Load Config"

    def execute(self, context):
        global CONFIG
        config_path = os.path.join(os.path.dirname(__file__), "check_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                CONFIG = json.load(f)
        else:
            CONFIG = {
                "bbox_threshold": 10,
                "uv_islands_threshold": 2
            }

        return ({"FINISHED"})

class BPMeshState(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty()
    fbx_path: bpy.props.StringProperty()
    json_path: bpy.props.StringProperty()

class BP_UL_MeshStateList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index): # called once for each item in the collection
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "label", text="", emboss=False)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.label)

class BPSettings(bpy.types.PropertyGroup):

    scope_mode : bpy.props.EnumProperty(
        name = "Scope",
        items = [
            ('Selected', "Selected", "Use all selected meshes"),
            ('All', "All", "Use all meshes in the scene"),
        ],
        default = "Selected"
    )

    base_name : bpy.props.StringProperty(
        name = "Asset base name",
        description = "The name of the asset. Will dictate the exported file names (ex. base name 'Crate' > Crate_low.fbx)",
        default = "",
        )

    suffix_low : bpy.props.StringProperty(
        name = "Suffix low",
        description = "Suffix of meshes that add-on will export as part of the low poly mesh.",
        default = "_low"
        )

    suffix_high : bpy.props.StringProperty(
        name = "Suffix high",
        description = "Suffix of meshes that add-on will export as part of the high poly mesh.",
        default = "_high"
        )

    output_path : bpy.props.StringProperty(
        name = "Working directory",
        description = "Path where exported files will be saved.",
        subtype = "FILE_PATH",
        update = lambda self, context: bpy.ops.bl.check_existing_states()
    )

    spp_project : bpy.props.EnumProperty(
        name = "spp_project",
        items = [
            ("UseOpen", "Use Open", "Use currently opened Substance Painter project for baking"),
            ("New", "Use New", "Open new Substance Painter project for baking"),
        ]
    )

    bake_normal_map : bpy.props.BoolProperty(
        name = "Normal",
        description = "Bake normal map",
        default = True
    )

    bake_ao_map : bpy.props.BoolProperty(
        name = "Ambient Occlusion",
        description = "Bake ambient occlusion map",
        default = False
    )

    bake_curvature_map : bpy.props.BoolProperty(
        name = "Curvature",
        description = "Bake curvature map",
        default = False
    )

    mesh_state_name : bpy.props.StringProperty(
        name = "Name",
        description = "Name that mesh state should be saved with",
    )

    mesh_states : bpy.props.CollectionProperty(
        name = "States",
        type = BPMeshState,
        description = "Different saved mesh states"
    )

    mesh_states_index: bpy.props.IntProperty(
        name="Active State Index"
    )

    change_count: bpy.props.IntProperty(default=-1)



class BlenderPainterBridge_PT_Main(bpy.types.Panel):

    bl_label = "Blender Painter Bridge"
    bl_idname = "VIEW3D_PT_painter_bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bp_settings

        # SETUP
        layout.label(text="Setup")
        box_setup = layout.box()

        scope_row = box_setup.row()
        scope_row.label(text="Objects")
        scope_row.prop_enum(settings, "scope_mode", "Selected")
        scope_row.prop_enum(settings, "scope_mode", "All")

        box_setup.prop(settings, "suffix_low", text="Suffix low")
        box_setup.prop(settings, "suffix_high", text="Suffix high")

        box_setup.prop(settings, "output_path")

        # SP PROJECT
        layout.label(text="Substance Painter project")
        box_project = layout.box()
        project_row = box_project.row()
        project_row.prop_enum(settings, "spp_project", "UseOpen")
        project_row.prop_enum(settings, "spp_project", "New")

        # MESH STATES
        layout.label(text="Mesh States")
        box_states = layout.box()
        box_states.prop(settings, "mesh_state_name", text="Name")
        # box_states.prop(settings, "mesh_states", text="States")
        box_states.template_list(
            "BP_UL_MeshStateList",  # UIList class name
            "",  # list ID (empty because i'm only using 1)
            settings,  # data that holds the collection
            "mesh_states",  # collection property name
            settings,  # data that holds the active index
            "mesh_states_index"  # index property name
        )

        state_btns_row = box_states.row()
        state_btns_row.operator("bl.save_state", text="Save")
        state_btns_row.operator("bl.load_state", text="Load")
        state_btns_row.operator("bl.remove_state", text="Remove")

        # BAKING
        layout.label(text="Baking")
        box_baking = layout.box()
        change_split = box_baking.split(factor=0.75)
        change_split.operator("bl.check_changes", text="Check Changes", icon="VIEWZOOM")
        change_split.operator("bl.load_config", text="Config", icon="FILE_REFRESH")

        if settings.change_count < 0:
            data_box = box_baking.box()
            status_row = data_box.row()
        elif  settings.change_count == 0:
            data_box = box_baking.box()
            status_row = data_box.row()
            status_row.label(text="Safe to reload", icon="STRIP_COLOR_04")
            data_box.label(text="Unlikely to affect layer assignments", icon="FAKE_USER_ON")
        elif settings.change_count == 1:
            data_box = box_baking.box()
            status_row = data_box.row()
            status_row.label(text="Reload with caution", icon="STRIP_COLOR_02")
            data_box.label(text="Rebaking may break layer assignments", icon="ERROR")
        elif settings.change_count >= 2:
            data_box = box_baking.box()
            status_row = data_box.row()
            status_row.label(text="Risky to reload", icon="STRIP_COLOR_01")
            data_box.label(text="Consider baking in a new .spp file", icon="ERROR")

        box_baking.label(text="Mesh Maps")
        box_baking.prop(settings, "bake_normal_map")
        box_baking.prop(settings, "bake_ao_map")
        box_baking.prop(settings, "bake_curvature_map")

        box_baking.operator("bl.export_and_bake", text="Export and Bake", icon="CHECKMARK")

class BP_OT_CheckExistingStates(bpy.types.Operator):
    bl_idname = "bl.check_existing_states"
    bl_label = "Check Existing Mesh States"

    def execute(self, context):
        print("RUN!")
        settings = context.scene.bp_settings

        directory = os.path.join(settings.output_path, "bp_bridge_output", "mesh_states")

        if not os.path.exists(directory):
            return {'FINISHED'}

        # find all .fbx files
        for file in os.listdir(directory):
            if file.endswith(".fbx"):
                name = file[:-4]  # remove .fbx
                print(name)
                json_path = os.path.join(directory, name + ".json")
                fbx_path = os.path.join(directory, file)

                item = settings.mesh_states.add()
                item.label = name
                item.fbx_path = fbx_path
                item.json_path = json_path

        return {'FINISHED'}

class CheckChanges(bpy.types.Operator):
    bl_idname = "bl.check_changes"
    bl_label = "CheckChanges"

    def execute(self, context):
        parts_to_check = []
        settings = context.scene.bp_settings

        settings.change_count = 0
        if settings.scope_mode == "All":
            parts_to_check = [o for o in context.scene.objects if o.type == 'MESH']

        elif settings.scope_mode == "Selected":
            parts_to_check = [o for o in bpy.context.selected_objects if o.type == "MESH"]

        bbox = get_bbox(self, parts_to_check)
        materials = get_materials(self, parts_to_check)
        uv_islands = get_uv_islands(self, parts_to_check)

        print(f"New data: {bbox}, {materials}. {uv_islands}")

        current_selected = settings.mesh_states[settings.mesh_states_index]
        json_file = current_selected.json_path
        with open(json_file, "r") as read_file:
            state_data = json.load(read_file)

        print(f"State data (old): {state_data}")

        # BBOX CHANGE
        state_bbox = state_data["bbox"]
        threshold = CONFIG["bbox_threshold"]
        for old_val, new_val in zip(state_bbox, bbox):
            if old_val == 0:
                continue
            diff = abs(new_val - old_val) / abs(old_val) * 100
            if diff > threshold:
                settings.change_count += 1
                break

        # MATERIALS CHANGE
        state_materials = state_data["materials"]
        if state_materials != materials:
            settings.change_count += 1

        # UVS CHANGE
        state_uvs = state_data["uv_islands"]
        threshold = CONFIG["uv_islands_threshold"]

        limit_min = state_uvs - threshold
        limit_max = state_uvs + threshold

        if uv_islands < limit_min or uv_islands > limit_max:
            settings.change_count += 1

        print(f"Changes: {settings.change_count}")

        return ({'FINISHED'})

class ExportAndBake(bpy.types.Operator):
    bl_idname = "bl.export_and_bake"
    bl_label = "ExportMeshes"

    def execute(self, context):
        print("Export and Bake executed")

        mesh_parts_to_export = []
        settings = context.scene.bp_settings

        if settings.scope_mode == "All":
            mesh_parts_to_export = [o for o in context.scene.objects if o.type == 'MESH']
            print(mesh_parts_to_export)

        elif settings.scope_mode == "Selected":
            mesh_parts_to_export = [o for o in bpy.context.selected_objects if o.type == "MESH"]
            print(mesh_parts_to_export)

        low_poly_parts = []
        high_poly_parts = []
        suffix_low = settings.suffix_low
        suffix_high = settings.suffix_high
        for obj in mesh_parts_to_export:
            if suffix_low in obj.name:
                low_poly_parts.append(obj)
            elif suffix_high in obj.name:
                high_poly_parts.append(obj)

        output_directory = os.path.join(settings.output_path, "bp_bridge_output")

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        bpy.ops.object.select_all(action='DESELECT')

        if bpy.data.filepath:
            assetname = bpy.path.basename(bpy.context.blend_data.filepath).replace(".blend", "") # name of file
        else:
            assetname = "exported_asset"

        # export low poly
        for lp_part in low_poly_parts:
            lp_part.select_set(True)
        filename = os.path.join(output_directory, assetname) + "_low.fbx"
        bpy.ops.export_scene.fbx(filepath=filename, use_selection=True, use_triangles=True)

        bpy.ops.object.select_all(action='DESELECT')

        # export high poly
        for hp_part in high_poly_parts:
            hp_part.select_set(True)
        filename = os.path.join(output_directory, assetname) + "_high.fbx"
        bpy.ops.export_scene.fbx(filepath=filename, use_selection=True, use_mesh_modifiers=True)

        bpy.ops.object.select_all(action='DESELECT')

        print(f"Low poly: {low_poly_parts}")
        print(f"High poly: {high_poly_parts}")

        return {"FINISHED"}

class SaveState(bpy.types.Operator):
    bl_idname = "bl.save_state"
    bl_label = "SaveState"

    # controls the "mode" the operator is in
    overwrite: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        settings = context.scene.bp_settings

        # determine what objects to export
        to_export = []
        if settings.scope_mode == "All":
            to_export = [o for o in context.scene.objects if o.type == 'MESH']
        elif settings.scope_mode == "Selected":
            to_export = bpy.context.selected_objects

        # ensures output directory exists
        output_directory = os.path.join(settings.output_path, "bp_bridge_output", "mesh_states")
        os.makedirs(output_directory, exist_ok=True)

        assetname = settings.mesh_state_name
        if assetname == "":
            self.report({"WARNING"}, "No mesh state name chosen.")
            return {'CANCELLED'}

        # check if this state already exists
        existing_index = self.find_state_index(settings, assetname)
        fbx_exists = os.path.exists(os.path.join(output_directory, assetname + ".fbx"))

        # if file exists and overwrite is False -> show popup
        if fbx_exists and not self.overwrite:
            bpy.ops.wm.overwrite('INVOKE_DEFAULT', asset_name=assetname)
            return {'CANCELLED'}

        # collect mesh data
        try:
            bbox = get_bbox(self, to_export)
            materials = get_materials(self, to_export)
            uv_islands = get_uv_islands(self, to_export)
            print(f"UV islands: {uv_islands}")
            json_path = self.save_data(output_directory, assetname, bbox, materials, uv_islands)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to save mesh state: {e}")
            return({"CANCELLED"})

        # save fbx
        filename = os.path.join(output_directory, assetname) + ".fbx"
        bpy.ops.export_scene.fbx(filepath=filename, use_selection=True, use_mesh_modifiers=True)

        # update or create UIList entry
        if existing_index >= 0:
            item = settings.mesh_states[existing_index]
            item.fbx_path = filename
            item.json_path = json_path
        else:
            new_item = settings.mesh_states.add()
            new_item.label = assetname
            new_item.fbx_path = filename
            new_item.json_path = json_path

        print("State saved")
        return {'FINISHED'}

    def find_state_index(self, settings, name):
        for i, item in enumerate(settings.mesh_states):
            if item.label == name:
                return i
        return -1

    def save_data(self, output_directory, asset_name, bbox, materials, uv_islands):
        data = {}

        data["bbox"] = bbox
        data["materials"] = materials
        data["uv_islands"] = uv_islands
        json_filename = os.path.join(output_directory, asset_name) + ".json"
        with open(json_filename, "w") as write_file:
            json.dump(data, write_file)

        return json_filename

class MY_OT_overwrite(bpy.types.Operator):
    bl_idname = "wm.overwrite"
    bl_label = "Overwrite Mesh State?"

    asset_name: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.bp_settings
        settings.mesh_state_name = self.asset_name
        bpy.ops.bl.save_state(overwrite=True)
        return ({'FINISHED'})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Mesh state '{self.asset_name}' already exists.")
        layout.label(text="Do you want to overwrite that state?")

def get_bbox(operator, mesh_parts):
    try:
        x_values = []
        y_values = []
        z_values = []

        for object in mesh_parts:
            for corner in object.bound_box:
                world_corner = object.matrix_world @ Vector(corner)
                x_values.append(world_corner.x)
                y_values.append(world_corner.y)
                z_values.append(world_corner.z)
        total_width = max(x_values) - min(x_values)
        total_height = max(y_values) - min(y_values)
        total_depth = max(z_values) - min(z_values)

        full_bbox = [total_width, total_height, total_depth]
    except Exception as e:
        operator.report({"ERROR"}, str(e))
        return ({"CANCELLED"})

    return full_bbox

def get_materials(operator, mesh_parts):
    try:
        materials = []
        for object in mesh_parts:
            for material in object.material_slots:
                if  material.name not in materials:
                    materials.append(material.name)
    except Exception as e:
        operator.report({"ERROR"}, str(e))
        return ({"CANCELLED"})

    return materials

def get_uv_islands(operator, mesh_parts):
    try:
        islands = 0
        for object in mesh_parts:
            bm = bmesh.new()
            bm.from_mesh(object.data)

            uv_layer = bm.loops.layers.uv[object.data.uv_layers.active.name]

            islands += len(bmesh_utils.bmesh_linked_uv_islands(bm, uv_layer))
    except Exception as e:
        operator.report({"ERROR"}, str(e))
        return ({"CANCELLED"})

    return islands

class LoadState(bpy.types.Operator):
    bl_idname = "bl.load_state"
    bl_label = "LoadState"

    def execute(self, context):
        settings = context.scene.bp_settings

        selected_state = settings.mesh_states_index

        bpy.ops.import_scene.fbx(filepath=settings.mesh_states[selected_state].fbx_path)

        print("State loaded")
        return {"FINISHED"}

class RemoveState(bpy.types.Operator):
    bl_idname = "bl.remove_state"
    bl_label = "RemoveState"

    def execute(self, context):
        settings = context.scene.bp_settings

        selected_state = settings.mesh_states_index
        if os.path.exists(settings.mesh_states[selected_state].fbx_path):
            os.remove(settings.mesh_states[selected_state].fbx_path)

        if os.path.exists(settings.mesh_states[selected_state].json_path):
            os.remove(settings.mesh_states[selected_state].json_path)

        settings.mesh_states.remove(selected_state)

        print("State loaded")
        return {"FINISHED"}

# class OpenSubstancePainter(bpy.types.Operator):
#     bl_idname = "bl.open_spp"
#     bl_label = "Open Substance Painter Project"
#
#     def execute(self, context):
#         settings = context.scene.bp_settings
#         spp_path = bpy.path.abspath(settings.painter_path)
#
#         if not spp_path.lower().endswith(".spp"):
#             self.report({'ERROR'}, "Please select a valid .spp file")
#             return {'CANCELLED'}
#
#         if not os.path.exists(spp_path):
#             self.report({'ERROR'}, "File does not exist")
#             return {'CANCELLED'}
#
#         subprocess.Popen([PAINTER_EXE, spp_path])
#         return {'FINISHED'}


def register():
    bpy.utils.register_class(LoadConfig)
    bpy.utils.register_class(BP_OT_CheckExistingStates)
    bpy.utils.register_class(BPMeshState)
    bpy.utils.register_class(BP_UL_MeshStateList)
    bpy.utils.register_class(BPSettings)
    bpy.utils.register_class(MY_OT_overwrite)
    bpy.utils.register_class(CheckChanges)
    bpy.utils.register_class(ExportAndBake)
    bpy.utils.register_class(SaveState)
    bpy.utils.register_class(LoadState)
    bpy.utils.register_class(RemoveState)
    # bpy.utils.register_class(OpenSubstancePainter)
    bpy.utils.register_class(BlenderPainterBridge_PT_Main)
    bpy.types.Scene.bp_settings = bpy.props.PointerProperty(type=BPSettings)

def unregister():
    bpy.utils.unregister_class(LoadConfig)
    bpy.utils.unregister_class(BP_OT_CheckExistingStates)
    bpy.utils.unregister_class(BPMeshState)
    bpy.utils.UNregister_class(BP_UL_MeshStateList)
    del bpy.types.Scene.bp_settings
    bpy.utils.unregister_class(BlenderPainterBridge_PT_Main)
    bpy.utils.unregister_class(MY_OT_overwrite)
    bpy.utils.unregister_class(CheckChanges)
    bpy.utils.unregister_class(ExportAndBake)
    bpy.utils.unregister_class(SaveState)
    bpy.utils.unregister_class(LoadState)
    bpy.utils.unregister_class(RemoveState)
    # bpy.utils.unregister_class(OpenSubstancePainter)
    bpy.utils.unregister_class(BPSettings)


if __name__ == "__main__":
    register()