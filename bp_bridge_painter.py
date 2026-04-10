from PySide6 import QtWidgets, QtCore
import substance_painter.ui
import substance_painter.project
import substance_painter.baking
import substance_painter.textureset as textureset
import os


class PainterBridge(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Blender Painter Bridge")

        main_layout = QtWidgets.QVBoxLayout(self)

        blender_label = QtWidgets.QLabel("Blender file")
        self.blender_path_edit = QtWidgets.QLineEdit()
        self.blender_path_edit.setPlaceholderText("Path to .blend file")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_blend_file)

        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.blender_path_edit)
        path_layout.addWidget(browse_button)

        main_layout.addWidget(blender_label)
        main_layout.addLayout(path_layout)

        asset_label = QtWidgets.QLabel("Asset base name")
        self.asset_name_edit = QtWidgets.QLineEdit()
        self.asset_name_edit.setPlaceholderText("e.g. crate")

        main_layout.addWidget(asset_label)
        main_layout.addWidget(self.asset_name_edit)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(line)

        self.reload_button = QtWidgets.QPushButton("Reload Meshes")
        main_layout.addWidget(self.reload_button)
        self.reload_button.clicked.connect(self.reload_low_poly_mesh)

        self.bake_button = QtWidgets.QPushButton("Bake")
        main_layout.addWidget(self.bake_button)
        self.bake_button.clicked.connect(self.bake)

        self.low_poly_fbx = None
        self.high_poly_fbx = None

        substance_painter.event.DISPATCHER.connect(
            substance_painter.event.BakingProcessEnded,
            self.on_baking_finished
        )

    def browse_blend_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Blender File",
            "",
            "Blender Files (*.blend)"
        )

        if path:
            self.blender_path_edit.setText(path)

    def get_output_folder(self):
        blender_path = self.blender_path_edit.text()
        blend_name = os.path.basename(blender_path).replace(".blend", "")
        output_folder = os.path.join(os.path.dirname(blender_path), f"{blend_name}_output")
        return output_folder

    def reload_low_poly_mesh(self):
        output_folder = self.get_output_folder()
        print(f"Output folder: {output_folder}")
        asset_name = self.asset_name_edit.text()
        print(f"Asset name: {asset_name}")

        for root, dirs, files in os.walk(output_folder):
            if f"{asset_name}_low.fbx" in files:
                self.low_poly_fbx = os.path.join(root, f"{asset_name}_low.fbx")
                print(f"Low poly mesh: {self.low_poly_fbx}")

        mesh_reloading_settings = substance_painter.project.MeshReloadingSettings(
            import_cameras=False,
            preserve_strokes=False)
        substance_painter.project.reload_mesh(self.low_poly_fbx, mesh_reloading_settings, self.on_mesh_reload)

        print(self.low_poly_fbx)

    def on_mesh_reload(self, status: substance_painter.project.ReloadMeshStatus):
        if status == substance_painter.project.ReloadMeshStatus.SUCCESS:
            print("The low poly mesh was reloaded successfully.")
        else:
            print("The low poly mesh couldn't be reloaded.")

    def bake(self):
        output_folder = self.get_output_folder()
        asset_name = self.asset_name_edit.text()

        for root, dirs, files in os.walk(output_folder):
            if f"{asset_name}_high.fbx" in files:
                self.high_poly_fbx = os.path.join(root, f"{asset_name}_high.fbx")

        if not self.high_poly_fbx:
            print("High poly mesh not found!")
            return

        texture_sets = textureset.all_texture_sets()

        if not texture_sets:
            print("No texture sets found!")
            return

        for ts in texture_sets:
            baking_params = substance_painter.baking.BakingParameters.from_texture_set_name(ts.name())
            common_params = baking_params.common()

            # Convert path to proper URL format
            highpoly_mesh_path = QtCore.QUrl.fromLocalFile(self.high_poly_fbx).toString()

            # Set only the high poly mesh and match setting
            substance_painter.baking.BakingParameters.set({
                common_params['HipolyMesh']: highpoly_mesh_path,
            })

            substance_painter.baking.bake_selected_textures_async()

    def on_baking_finished(self, event):
        """Called when baking process ends"""

        if event.status == substance_painter.baking.BakingStatus.Success:
            print("Baking completed successfully!")
        elif event.status == substance_painter.baking.BakingStatus.Cancel:
            print("Baking was cancelled.")
        else:
            print("Baking failed.")

plugin_widgets = []

def start_plugin():
    print("Hey this works!")
    bridge_widget = PainterBridge()
    substance_painter.ui.add_dock_widget(bridge_widget)
    plugin_widgets.append(bridge_widget)

def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()

if __name__ == "__main__":
    start_plugin()