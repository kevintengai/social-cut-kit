"""Inspect The Saved Blender Scene Without Rendering An Image Or Movie."""

import json
import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def check(condition,message):
    if not condition:
        raise RuntimeError(message)


def main():
    scene = bpy.context.scene
    check(scene.camera and scene.camera.type == "CAMERA","Missing Product Camera.")
    rotary = scene.objects["Dial Pivot"]
    key = scene.objects["Monitor Key Travel"]
    camera = scene.camera
    marker_count = len(scene.timeline_markers)
    check(marker_count == 4,"Missing Timeline Markers.")
    cells = [o for o in scene.objects if o.name.startswith("Indicator Cell ")]
    sources = [o for o in scene.objects if o.type == "LIGHT"]
    body_parts = [o for o in scene.objects if o.type == "MESH" and o.name != "Isolated Desk Surface"]
    check(len(cells) == 21 and len(sources) == 4,"Missing Indicator Cells Or Studio Lights.")
    check(all(o.data.materials for o in body_parts),"A Product Part Has No Material.")
    positions,depths,angles,meter_counts,bounds = [],[],[],[],[]
    for marker in sorted(scene.timeline_markers,key=lambda m:m.frame):
        scene.frame_set(marker.frame)
        dg = bpy.context.evaluated_depsgraph_get()
        evaluated_camera = camera.evaluated_get(dg)
        positions.append(tuple(round(k,4) for k in evaluated_camera.matrix_world.translation))
        depths.append(round(key.location.z,4))
        angles.append(round(math.degrees(rotary.rotation_euler.z),2))
        lit = sum(o.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value > .5 for o in cells)
        meter_counts.append(lit)
        coords = []
        for obj in body_parts:
            part = obj.evaluated_get(dg)
            coords.extend(world_to_camera_view(scene,evaluated_camera,part.matrix_world @ Vector(c)) for c in part.bound_box)
        check(all(p.z > 0 for p in coords),"Product Behind Camera.")
        edge = [min(p.x for p in coords), min(p.y for p in coords),max(p.x for p in coords),max(p.y for p in coords)]
        check(min(edge[:2]) >= -.002 and max(edge[2:]) <= 1.002,"Product Extends Outside The Camera Frame.")
        bounds.append([round(v,3) for v in edge])
    check(max(depths)-min(depths)>.04,"The Monitor Key Does Not Depress.")
    check(rotary.animation_data and camera.animation_data,"Missing Motion Tracks.")
    check(not any(i.filepath for i in bpy.data.images if i.source == "FILE"),"Unexpected External Image Dependency.")
    scene.frame_set(scene.frame_start)
    print(json.dumps({"objects":len(scene.objects),"materials":len(bpy.data.materials),"lights":len(sources),
                      "frames":scene.frame_end,"fps":scene.render.fps,"markers":marker_count,
                      "camera_positions":positions,"dial_degrees":angles,"key_heights":depths,
                      "lit_indicator_cells":meter_counts,"projected_product_bounds":bounds}))


if __name__ == "__main__":
    main()
