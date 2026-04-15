import json
import os
import threading
from PySide6 import QtCore

import substance_painter as sp
import substance_painter.baking as baking
import substance_painter.event as event
import substance_painter.textureset as ts

plugin_events = []

TASK_DIRECTORY =  r"C:\Users\jelen\Desktop\personal\blender_painter_bridge\bp_bridge_output\tasks"

class PainterBridge:
    def __init__(self):
        print("PainterBridge initialized!")

        self.high_path = None
        self.suffix_low = None
        self.suffix_high = None
        self.normal = False
        self.ao = False
        self.curv = False

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.on_timer_tick)
        self.timer.start()
        self.running = True

        event.DISPATCHER.connect_strong(event.ProjectEditionEntered, self.on_project_ready)
        plugin_events.append((event.ProjectEditionEntered, self.on_project_ready))
        self.project_ready = False

        self.pending_bake = False

        event.DISPATCHER.connect_strong(event.BakingProcessEnded, self.on_baking_finished)
        plugin_events.append((event.BakingProcessEnded, self.on_baking_finished))


    def on_project_ready(self, e: sp.event.Event):
        self.project_ready = True

    def on_timer_tick(self):
        if self.pending_bake and self.project_ready:
            self.pending_bake = False
            self.bake(self.high_path, self.normal, self.ao, self.curv)
            return

        for (root, dirs, files) in os.walk(TASK_DIRECTORY):
            for file in files:
                filepath = os.path.join(root, file)
                with open(filepath, "r") as f:
                    task_data = json.load(f)
                os.remove(filepath)

                self.process_task(task_data)

    def process_task(self, task_data):
        low_path = task_data["meshes"]["low_path"]
        self.high_path = task_data["meshes"]["high_path"]
        self.suffix_low = task_data["suffixes"]["low"]
        self.suffix_high = task_data["suffixes"]["high"]
        self.normal = task_data["mesh_maps"]["normal"]
        self.ao = task_data["mesh_maps"]["ao"]
        self.curv = task_data["mesh_maps"]["curvature"]

        spp_project = task_data["procedure"]

        if spp_project == "use_new":

            project_settings = sp.project.Settings(
                import_cameras=False,
                default_texture_resolution=1024,
                normal_map_format=sp.project.NormalMapFormat.DirectX
            )
            sp.project.create(mesh_file_path=low_path, settings=project_settings)
            self.pending_bake = True

        elif spp_project == "use_open":

            mesh_reloading_settings = sp.project.MeshReloadingSettings(
                import_cameras=False,
                preserve_strokes=False
            )

            sp.project.reload_mesh(low_path, mesh_reloading_settings, self.on_mesh_reload)

    def on_mesh_reload(self, status: sp.project.ReloadMeshStatus):
        if status == sp.project.ReloadMeshStatus.SUCCESS:
            print("Mesh reloaded successfully, starting bake...")
            self.bake(self.high_path, self.normal, self.ao, self.curv)
        else:
            print("Mesh reload failed.")

    def bake(self, high_path, normal, ao, curv):
        from PySide6 import QtCore
        highpoly_url = QtCore.QUrl.fromLocalFile(high_path).toString()

        texture_sets = ts.all_texture_sets()

        for texture_set in texture_sets:
            baking_params = sp.baking.BakingParameters.from_texture_set_name(texture_set.name)
            common_params = baking_params.common()

            sp.baking.BakingParameters.set({
                common_params["HipolyMesh"]: highpoly_url,
                common_params["LowpolySuffix"]: self.suffix_low,
                common_params["HipolySuffix"]: self.suffix_high,
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

    def on_baking_finished(self, e: sp.event.Event):
        if e.status == sp.baking.BakingStatus.Success:
            print("Baking completed successfully!")
        elif e.status == sp.baking.BakingStatus.Cancel:
            print("Baking was cancelled.")
        else:
            print("Baking failed.")

    def stop(self):
        try:
            if self.timer and self.timer.isActive():
                self.timer.timeout.disconnect()
                self.timer.stop()
                self.timer.deleteLater()
        except Exception as e:
            print(f"Exception stopping timer: {e}")
        finally:
            self.running = False

def start_plugin():
    global my_plugin
    my_plugin = PainterBridge()


def close_plugin():
    global my_plugin
    if my_plugin:
        try:
            my_plugin.stop()
        except Exception as e:
            print(f"Error stopping plugin: {e}")
        finally:
            for evt, cb in plugin_events:
                try:
                    event.DISPATCHER.disconnect(evt, cb)
                except Exception as e:
                    print(f"Error disconnecting event: {e}")
                    pass
            plugin_events.clear()

        my_plugin = None

if __name__ == "__main__":
    start_plugin()
