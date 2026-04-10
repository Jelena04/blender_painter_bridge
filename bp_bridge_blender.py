bl_info = {
    "name": "Blender Painter Bridge",
    "author": "Jelena Rombouts",
    "version": (1,0),
    "blender": (4,4,3),
    "location": "View3d > Tool",
    "warning": "Blend file must be saved in order for the script to work. Exported models will be saved in the same directory.",
    "wiki_url": "https://www.artstation.com/jelenarombouts2",
    "category": "Import-Export"
    }

import bpy
import os
import subprocess

print("I am a super cool adjustment")

PAINTER_EXE = r"C:\Program Files\Adobe\Adobe Substance 3D Painter\Adobe Substance 3D Painter.exe"

def update_all_meshes(self, context):
    if self.my_bool_all_meshes:
        self.my_bool_selection = False

def update_selection(self, context):
    if self.my_bool_selection:
        self.my_bool_all_meshes = False

class BPSettings(bpy.types.PropertyGroup):
    
    my_bool_all_meshes : bpy.props.BoolProperty(
        name = "All meshes in scene",
        description = "When True, the add-on will take into account all meshes in the scene.",
        default = True,
        update = update_all_meshes
        )
        
    my_bool_selection : bpy.props.BoolProperty(
        name = "Based on selection",
        description = "When True, the add-on will only take into account the meshes that are selected.",
        default = False,
        update = update_selection
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
        
    painter_path : bpy.props.StringProperty(
        name = "Substance Painter project path",
        description = "The path to the .spp file you want the mesh maps to be updated from with the new ones from the bake.",
        default = "...",
        subtype='FILE_PATH'
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
        
        row = layout.row()
        layout.prop(settings, "my_bool_all_meshes")
        row = layout.row()
        layout.prop(settings, "my_bool_selection")
        row = layout.row()
        layout.prop(settings, "base_name")
        row = layout.row()
        layout.prop(settings, "suffix_low")
        row = layout.row()
        layout.prop(settings, "suffix_high")
        row = layout.row()
        row.operator("bl.export_high_low", text="Export meshes")
        row = layout.row()
        layout.prop(settings, "painter_path")
        row = layout.row()
        
        row.operator("bl.open_spp", text="Open Substance Painter Project")
        
class ExportMeshes(bpy.types.Operator):
    bl_idname = "bl.export_high_low"
    bl_label = "ExportMeshes"
    
    def execute(self, context):
        print("Export Meshes executed!")
        
        mesh_parts_to_export = []
        settings = context.scene.bp_settings
        
        if settings.my_bool_all_meshes:
            
            mesh_parts_to_export = [o for o in context.scene.objects if o.type == 'MESH']
            print(mesh_parts_to_export)
            
        elif settings.my_bool_selection:
            
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
        
        blend_direct = os.path.dirname(bpy.data.filepath)
        output_folder_name = bpy.path.basename(bpy.context.blend_data.filepath).replace(".blend", "") + "_output"
        output_directory = os.path.join(blend_direct, output_folder_name)
        
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        bpy.ops.object.select_all(action='DESELECT')
        
        # export low poly    
        for lp_part in low_poly_parts:
            lp_part.select_set(True)
        filename = os.path.join(output_directory, settings.base_name) + "_low.fbx"
        bpy.ops.export_scene.fbx(filepath=filename, use_selection=True, use_triangles=True)
        
        bpy.ops.object.select_all(action='DESELECT')
        
        # export high poly
        for hp_part in high_poly_parts:
            hp_part.select_set(True)
        filename = os.path.join(output_directory, settings.base_name) + "_high.fbx"
        bpy.ops.export_scene.fbx(filepath=filename, use_selection=True, use_mesh_modifiers=True)
        
        bpy.ops.object.select_all(action='DESELECT')

        print(f"Low poly: {low_poly_parts}")
        print(f"High poly: {high_poly_parts}")
        
        return {"FINISHED"}
    
class OpenSubstancePainter(bpy.types.Operator):
    bl_idname = "bl.open_spp"
    bl_label = "Open Substance Painter Project"

    def execute(self, context):
        settings = context.scene.bp_settings
        spp_path = bpy.path.abspath(settings.painter_path)

        if not spp_path.lower().endswith(".spp"):
            self.report({'ERROR'}, "Please select a valid .spp file")
            return {'CANCELLED'}

        if not os.path.exists(spp_path):
            self.report({'ERROR'}, "File does not exist")
            return {'CANCELLED'}

        subprocess.Popen([PAINTER_EXE, spp_path])
        return {'FINISHED'}
    
        
def register():
    bpy.utils.register_class(BPSettings)
    bpy.utils.register_class(ExportMeshes)
    bpy.utils.register_class(OpenSubstancePainter)
    bpy.utils.register_class(BlenderPainterBridge_PT_Main)
    bpy.types.Scene.bp_settings = bpy.props.PointerProperty(type=BPSettings)

def unregister():
    del bpy.types.Scene.bp_settings
    bpy.utils.unregister_class(BlenderPainterBridge_PT_Main)
    bpy.utils.unregister_class(ExportMeshes)
    bpy.utils.unregister_class(OpenSubstancePainter)
    bpy.utils.unregister_class(BPSettings)


if __name__ == "__main__":
    register()