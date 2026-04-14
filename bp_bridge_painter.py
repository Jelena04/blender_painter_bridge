import json
import os
import threading

import substance_painter as sp
import substance_painter.baking as baking
import substance_painter.event as event
import substance_painter.textureset as ts

def on_baking_finished(e: sp.event.BakingProcessEnded):
    if e.status == sp.baking.BakingStatus.Success:
        print("Baking completed successfully!")
    elif e.status == sp.baking.BakingStatus.Cancel:
        print("Baking was cancelled.")
    else:
        print("Baking failed.")

plugin_events = []

class PainterBridge():
    def __init__(self):
        print("PainterBridge initialized!")

        self.pending_high_path = None
        self.pending_normal = False
        self.pending_ao = False
        self.pending_curv = False

        event.DISPATCHER.connect_strong(event.ProjectEditionEntered, self.on_project_ready)
        plugin_events.append((event.ProjectEditionEntered, self.on_project_ready))
        # self.ready = False
        event.DISPATCHER.connect_strong(event.BakingProcessEnded, on_baking_finished)
        plugin_events.append((event.BakingProcessEnded, on_baking_finished))

        self.run_task_checking()

    def check_for_tasks(self):
        task_directory = r"C:\Users\jelen\Desktop\personal\blender_painter_bridge\bp_bridge_output\tasks"

        print("Checking for tasks")

        for (root, dirs, files) in os.walk(task_directory):
            for file in files:
                filepath = os.path.join(root, file)
                with open(filepath, "r") as f:
                    task_data = json.load(f)
                print(f"Task found! {file}")
                # os.remove(filepath)

                # if self.ready:
                sp.project.execute_when_not_busy(lambda t=task_data: self.process_task(t))

    def run_task_checking(self):
        self.check_for_tasks()
        threading.Timer(2, self.run_task_checking).start()

    def process_task(self, task_data):
        low_path = task_data["meshes"]["low_path"]
        high_path = task_data["meshes"]["high_path"]

        self.pending_high_path = high_path
        self.pending_normal = task_data["mesh_maps"]["normal"]
        self.pending_ao = task_data["mesh_maps"]["ao"]
        self.pending_curv = task_data["mesh_maps"]["curvature"]

        spp_project = task_data["procedure"]

        if spp_project == "use_new":
            if sp.project.is_open():
                print("A project is already open, cannot create a new one.")
                return

            project_settings = sp.project.Settings(
                import_cameras=False,
                default_texture_resolution=1024,
                normal_map_format=sp.project.NormalMapFormat.DirectX
            )
            sp.project.create(mesh_file_path=low_path, settings=project_settings)

        elif spp_project == "use_open":
            if not sp.project.is_open():
                print("No project is open.")
                return

            mesh_reloading_settings = sp.project.MeshReloadingSettings(
                import_cameras=False,
                preserve_strokes=False
            )
            sp.project.reload_mesh(low_path, mesh_reloading_settings, self.on_mesh_reload)

    def on_project_ready(self, e: sp.event.ProjectEditionEntered):
        self.ready = True
        if self.pending_high_path:
            self.bake(self.pending_high_path, self.pending_normal, self.pending_ao, self.pending_curv)

    def on_mesh_reload(self, status: sp.project.ReloadMeshStatus):
        if status == sp.project.ReloadMeshStatus.SUCCESS:
            print("Mesh reloaded successfully, starting bake...")
            self.bake(self.pending_high_path, self.pending_normal, self.pending_ao, self.pending_curv)
        else:
            print("Mesh reload failed.")

    def bake(self, high_path, normal, ao, curv):
        from PySide6 import QtCore
        highpoly_url = QtCore.QUrl.fromLocalFile(high_path).toString()

        texture_sets = ts.all_texture_sets()

        for texture_set in texture_sets:
            baking_params = sp.baking.BakingParameters.from_texture_set_name(texture_set.name())
            common_params = baking_params.common()

            sp.baking.BakingParameters.set({
                common_params["HipolyMesh"]: highpoly_url
            })

            enabled_maps = []
            if normal:
                enabled_maps.append(baking.MeshMapUsage.Normal)
            if ao:
                enabled_maps.append(baking.MeshMapUsage.AO)
            if curv:
                enabled_maps.append(baking.MeshMapUsage.Curvature)

            baking_params.set_enabled_bakers(enabled_maps)

        sp.baking.bake_selected_textures_async()

        self.pending_high_path = None


def start_plugin():
    print("Plugin started")
    my_plugin = PainterBridge()


def close_plugin():
    for evt, cb in plugin_events:
        event.DISPATCHER.disconnect(evt, cb)
    plugin_events.clear()
    print("Plugin closed")


if __name__ == "__main__":
    start_plugin()