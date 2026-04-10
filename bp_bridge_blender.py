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



def update_all_meshes(self, context):
    if self.my_bool_all_meshes:
        self.my_bool_selection = False

def update_selection(self, context):
    if self.my_bool_selection:
        self.my_bool_all_meshes = False

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

    mesh_states : bpy.props.EnumProperty(
        name = "Mesh States",
        items = [
            ("state_1", "State 1", "First mesh state"),
            ("state 2", "State 2", "Second mesh state"),
            ("state_3", "State 3", "Third mesh state")
        ]
    )
        
    # painter_path : bpy.props.StringProperty(
    #     name = "Substance Painter project path",
    #     description = "The path to the .spp file you want the mesh maps to be updated from with the new ones from the bake.",
    #     default = "...",
    #     subtype='FILE_PATH'
    #     )

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
        scope_row.label(text="Objects:")
        scope_row.prop_enum(settings, "scope_mode", "Selected")
        scope_row.prop_enum(settings, "scope_mode", "All")

        box_setup.prop(settings, "suffix_low")
        box_setup.prop(settings, "suffix_high")

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
        box_baking.label(text="Mesh maps:")
        box_baking.prop(settings, "bake_normal_map")
        box_baking.prop(settings, "bake_ao_map")
        box_baking.prop(settings, "bake_curvature_map")

        box_baking.operator("bl.check_changes", text="Check Changes", icon="VIEWZOOM")
        box_baking.operator("bl.export_and_bake", text="Export and Bake", icon="CHECKMARK")

        # MESH STATES
        layout.label(text="Mesh States")
        box_states = layout.box()
        box_states.prop(settings, "mesh_states")
        state_btns_row = box_states.row()
        state_btns_row.operator("bl.save_state", text="Save State")
        state_btns_row.operator("bl.load_state", text="Load State")


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
        
        # blend_direct = os.path.dirname(bpy.data.filepath)
        # output_folder_name = bpy.path.basename(bpy.context.blend_data.filepath).replace(".blend", "") + "_output"
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
        print("State saved")
        return {"FINISHED"}

class LoadState(bpy.types.Operator):
    bl_idname = "bl.load_state"
    bl_label = "LoadState"

    def execute(self, context):
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
    bpy.utils.register_class(BPSettings)
    bpy.utils.register_class(CheckChanges)
    bpy.utils.register_class(ExportAndBake)
    bpy.utils.register_class(SaveState)
    bpy.utils.register_class(LoadState)
    # bpy.utils.register_class(OpenSubstancePainter)
    bpy.utils.register_class(BlenderPainterBridge_PT_Main)
    bpy.types.Scene.bp_settings = bpy.props.PointerProperty(type=BPSettings)

def unregister():
    del bpy.types.Scene.bp_settings
    bpy.utils.unregister_class(BlenderPainterBridge_PT_Main)
    bpy.utils.unregister_class(CheckChanges)
    bpy.utils.unregister_class(ExportAndBake)
    bpy.utils.unregister_class(SaveState)
    bpy.utils.unregister_class(LoadState)
    # bpy.utils.unregister_class(OpenSubstancePainter)
    bpy.utils.unregister_class(BPSettings)


if __name__ == "__main__":
    register()