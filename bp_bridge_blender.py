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
import os
import subprocess

from mathutils import Vector
import json

# def update_all_meshes(self, context):
#     if self.my_bool_all_meshes:
#         self.my_bool_selection = False
#
# def update_selection(self, context):
#     if self.my_bool_selection:
#         self.my_bool_all_meshes = False


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
        name = "Output path",
        description = "Path where exported files will be saved.",
        subtype = "FILE_PATH"
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

        # BAKING
        layout.label(text="Baking")
        box_baking = layout.box()
        box_baking.label(text="Mesh Maps")
        box_baking.prop(settings, "bake_normal_map")
        box_baking.prop(settings, "bake_ao_map")
        box_baking.prop(settings, "bake_curvature_map")

        box_baking.operator("bl.check_changes", text="Check Changes", icon="VIEWZOOM")
        box_baking.operator("bl.export_and_bake", text="Export and Bake", icon="CHECKMARK")

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


class CheckChanges(bpy.types.Operator):
    bl_idname = "bl.check_changes"
    bl_label = "CheckChanges"

    def execute(self, context):
        print("Changes checked")

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

    def execute(self, context):
        settings = context.scene.bp_settings

        to_export = []
        if settings.scope_mode == "All":
            to_export = [o for o in context.scene.objects if o.type == 'MESH']
        elif settings.scope_mode == "Selected":
            to_export = bpy.context.selected_objects

        output_directory = os.path.join(settings.output_path, "bp_bridge_output")
        for (root, dirs, files) in os.walk(output_directory, topdown=True):
            filenames = files

        if settings.mesh_state_name == "":
            self.report({"WARNING"}, "No mesh state name chosen.")
            return({"CANCELLED"})
        elif f"{settings.mesh_state_name}.fbx" in filenames:
            self.report({"WARNING"}, "Mesh state name already taken.")
            return({"CANCELLED"})
        else:
            assetname = settings.mesh_state_name


        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        filename = os.path.join(output_directory, assetname) + ".fbx"
        bpy.ops.export_scene.fbx(filepath=filename, use_selection=True, use_mesh_modifiers=True)

        bbox = self.get_bbox(to_export)
        json_path = self.save_data(output_directory, assetname, bbox)

        new_item = settings.mesh_states.add()
        new_item.label = assetname
        new_item.fbx_path = filename
        new_item.json_path = json_path

        print("State saved")

        return {"FINISHED"}

    def get_bbox(self, mesh_parts):
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

        return full_bbox

    def save_data(self, output_directory, asset_name, bbox):
        data = {}
        data["bbox"] = bbox

        json_filename = os.path.join(output_directory, asset_name) + ".json"
        with open(json_filename, "w") as write_file:
            json.dump(data, write_file)

        return json_filename


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
        if settings.mesh_states[selected_state].fbx_path:
            os.remove(settings.mesh_states[selected_state].fbx_path)
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
    bpy.utils.register_class(BPMeshState)
    bpy.utils.register_class(BP_UL_MeshStateList)
    bpy.utils.register_class(BPSettings)
    bpy.utils.register_class(CheckChanges)
    bpy.utils.register_class(ExportAndBake)
    bpy.utils.register_class(SaveState)
    bpy.utils.register_class(LoadState)
    bpy.utils.register_class(RemoveState)
    # bpy.utils.register_class(OpenSubstancePainter)
    bpy.utils.register_class(BlenderPainterBridge_PT_Main)
    bpy.types.Scene.bp_settings = bpy.props.PointerProperty(type=BPSettings)

def unregister():
    bpy.utils.unregister_class(BPMeshState)
    bpy.utils.UNregister_class(BP_UL_MeshStateList)
    del bpy.types.Scene.bp_settings
    bpy.utils.unregister_class(BlenderPainterBridge_PT_Main)
    bpy.utils.unregister_class(CheckChanges)
    bpy.utils.unregister_class(ExportAndBake)
    bpy.utils.unregister_class(SaveState)
    bpy.utils.unregister_class(LoadState)
    bpy.utils.unregister_class(RemoveState)
    # bpy.utils.unregister_class(OpenSubstancePainter)
    bpy.utils.unregister_class(BPSettings)


if __name__ == "__main__":
    register()