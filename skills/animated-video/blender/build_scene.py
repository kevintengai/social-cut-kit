"""Build An Editable Pulse Dial Product Scene In A Fresh Background Blender Process."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

import bpy
from mathutils import Vector


DEFAULTS = {
    "width": 1080, "height": 1350, "fps": 30, "seconds": 5,
    "body_color": "#203544", "dial_color": "#384C55", "accent_color": "#72F5CC",
    "initial_level": 0.08, "peak_level": 0.92, "final_level": 0.64,
    "camera_travel": 1.0,
}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New Blender Project Filename.")
    parser.add_argument("--config", type=Path, help="Optional JSON Art Direction.")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def settings(path):
    config = dict(DEFAULTS)
    if path:
        supplied = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(supplied, dict) or set(supplied) - set(config):
            raise ValueError("Use Only The Configuration Fields In The Example.")
        config.update(supplied)
    for key in ("width","height","fps","seconds"):
        if type(config[key]) is not int:
            raise ValueError(f"{key} Must Be A Whole Number.")
    bounds = {"width":(64,4096),"height":(64,4096),"fps":(12,60),"seconds":(2,30),
              "initial_level":(0,1),"peak_level":(0,1),"final_level":(0,1),"camera_travel":(0,1.5)}
    for key,(low,high) in bounds.items():
        value = config[key]
        if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} Must Be Between {low} And {high}.")
    for key in ("body_color","dial_color","accent_color"):
        rgb(config[key])
    if not config["initial_level"] <= config["final_level"] <= config["peak_level"]:
        raise ValueError("Choose Levels In Ascending Order From Initial Through Final To Peak.")
    return config


def rgb(value):
    if not isinstance(value,str) or len(value) != 7 or value[0] != "#":
        raise ValueError("Use A Six-Digit Hex Color With A Leading Hash.")
    def linear(channel):
        s = int(channel,16) / 255
        return s / 12.92 if s <= .04045 else ((s+.055)/1.055)**2.4
    return tuple(linear(value[i:i+2]) for i in (1,3,5)) + (1,)


def material(name,color,metal=0,rough=.4,grain=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgb(color)
    m.use_nodes = True
    tree = m.node_tree
    shader = tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = m.diffuse_color
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    if grain:
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.name = "Fine Surface Grain"
        noise.inputs["Scale"].default_value = 165
        noise.inputs["Detail"].default_value = 2
        normal = tree.nodes.new("ShaderNodeBump")
        normal.inputs["Strength"].default_value = grain
        normal.inputs["Distance"].default_value = .018
        tree.links.new(noise.outputs["Fac"],normal.inputs["Height"])
        tree.links.new(normal.outputs["Normal"],shader.inputs["Normal"])
        noise.location,normal.location = (-550,-125),(-330,-125)
    return m


def emission(m,color,power):
    shader = m.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Emission Color"].default_value = rgb(color)
    strength = shader.inputs["Emission Strength"]
    strength.default_value = power
    return strength


def collection(name):
    group = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(group)
    return group


def place(obj,name,group,mat=None,parent=None):
    obj.name = name
    for previous in list(obj.users_collection):
        previous.objects.unlink(obj)
    group.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    return obj


def bevel(obj,width,segments=4):
    mod = obj.modifiers.new("Rounded Machined Edges","BEVEL")
    mod.width,mod.segments = width,segments
    mod.limit_method = "ANGLE"
    smooth = obj.modifiers.new("Face Normals","WEIGHTED_NORMAL")
    smooth.keep_sharp = True


def block(name,loc,dimensions,group,mat,rounding=.04,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    place(obj,name,group,mat,parent)
    if rounding:
        bevel(obj,rounding)
    return obj


def disk(name,loc,radius,depth,group,mat,parent=None,edge=.02,sides=80):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=radius,depth=depth,location=loc)
    obj = place(bpy.context.object,name,group,mat,parent)
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    if edge:
        bevel(obj,edge)
    return obj


def empty(name,loc,group):
    obj = bpy.data.objects.new(name,None)
    group.objects.link(obj)
    obj.location = loc
    obj.empty_display_size = .18
    return obj


def label(name,words,loc,size,group,mat):
    data = bpy.data.curves.new(name,"FONT")
    data.body = words
    data.size,data.space_character,data.extrude = size,1.16,.001
    obj = bpy.data.objects.new(name,data)
    group.objects.link(obj)
    obj.location = loc
    data.materials.append(mat)
    return obj


def arc_cell(name,cx,cy,z,inner,outer,a,b,group,mat):
    segments = 5
    vertices,polygons = [],[]
    for i in range(segments+1):
        angle = math.radians(a+(b-a)*i/segments)
        for radius in (inner,outer):
            vertices.append((cx+radius*math.cos(angle),cy+radius*math.sin(angle),z))
        if i:
            j = i*2
            polygons.append((j-2,j,j+1,j-1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],polygons)
    mesh.update()
    obj = bpy.data.objects.new(name,mesh)
    group.objects.link(obj)
    mesh.materials.append(mat)
    solid = obj.modifiers.new("Inset Lens Thickness","SOLIDIFY")
    solid.thickness = .013
    return obj


def build(config):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Pulse Dial"
    shell = collection("01 | Housing And Controls")
    dial = collection("02 | Rotary Assembly")
    meter = collection("03 | Segmented Indicator")
    lettering = collection("04 | Surface Markings")
    studio = collection("05 | Studio And Camera")
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x,scene.render.resolution_y = config["width"],config["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = config["fps"]
    scene.frame_start,scene.frame_end = 1,config["fps"]*config["seconds"]
    scene.render.image_settings.file_format = "PNG"

    casing = material("Satin Anodized Housing",config["body_color"],.72,.32,.1)
    anodized = material("Spun Aluminum Dial",config["dial_color"],.84,.26,.07)
    rubber = material("Graphite Rubber","#1B2226",.04,.65,.22)
    enamel = material("Matte Printed Legend","#C6D0C9",0,.46)
    trim = material("Brushed Rim","#8F9A98",.9,.25)
    lens = material("Dark Indicator Lens","#143830",.12,.27)
    marker = material("Dial Pointer",config["accent_color"],.08,.28)
    emission(marker,config["accent_color"],.36)
    ground = material("Studio Slate","#292F35",.12,.5,.1)

    block("Isolated Desk Surface",(0,0,-.14),(200,200,.28),studio,ground,.06)
    for x in (-1.62,1.62):
        for y in (-.98,.98):
            disk("Elastomer Foot",(x,y,.1),.21,.2,shell,rubber,edge=.028,sides=32)
    block("Lower Chassis",(0,0,.30),(4.34,2.96,.34),shell,rubber,.14)
    block("Machined Upper Body",(0,0,.56),(4.42,3.02,.51),shell,casing,.14)
    top = .815
    for x in (-1.95,1.95):
        for y in (-1.26,1.26):
            disk("Recessed Fastener",(x,y,top+.003),.065,.012,shell,trim,edge=.006,sides=24)
            drive = block("Fastener Slot",(x,y,top+.013),(.067,.012,.005),shell,rubber,.002)
            drive.rotation_euler.z = math.radians(28 if x*y>0 else -34)
    cx,cy = -.65,.10
    disk("Fixed Encoder Collar",(cx,cy,.85),.82,.095,dial,rubber,edge=.028)
    pivot = empty("Dial Pivot",(cx,cy,.86),dial)
    disk("Rotary Grip Core",(0,0,.155),.71,.32,dial,anodized,pivot,.045)
    for i in range(36):
        angle = i * math.tau/36
        rib = block(f"Grip Flute {i+1:02d}",(.705*math.cos(angle),.705*math.sin(angle),.152),
                    (.04,.045,.205),dial,rubber,.012,pivot)
        rib.rotation_euler.z = angle
    disk("Inset Dial Crown",(0,0,.316),.61,.04,dial,anodized,pivot,.016)
    block("Luminous Index",(.42,0,.341),(.255,.043,.015),dial,marker,.012,pivot)
    label("Encoder Legend","LEVEL",(cx-.27,-1.02,top+.009),.15,lettering,enamel)

    switch = empty("Monitor Key Travel",(1.04,-.62,top),shell)
    block("Monitor Key Bezel",(1.04,-.62,top+.016),(.93,.60,.065),shell,trim,.1)
    block("Monitor Key",(0,0,.086),(.85,.52,.15),shell,rubber,.075,switch)
    block("Key Index",(0,-.065,.165),(.29,.024,.013),shell,marker,.006,switch)
    label("Key Legend","MONITOR",(.57,-1.15,top+.009),.115,lettering,enamel)
    label("Meter Legend","SIGNAL",(.63,.3,top+.009),.128,lettering,enamel)
    for i in range(7):
        block(f"Rear Grille Slot {i+1:02d}",(.64 + i*.13,.79,top+.006),(.046,.43,.018),shell,rubber,.012)
    for x in (-.13,.13):
        disk("Rear Pair Marker",(1.47+x,.35,top+.017),.038,.018,shell,lens,edge=.006,sides=24)
    block("Front Status Window",(1.19,-1.517,.52),(.67,.032,.067),shell,rubber,.022)
    block("Front Status Light",(1.19,-1.536,.52),(.39,.01,.02),shell,marker,.004)

    first,peak,last = (config[key] for key in ("initial_level","peak_level","final_level"))
    phases = [(0,first),(.16,first),(.58,peak),(.71,peak),(.91,last),(1,last)]
    def frame(fraction):
        return 1 + round(fraction*(scene.frame_end-1))
    for t,level in phases:
        pivot.rotation_euler.z = math.radians(220-260*level)
        pivot.keyframe_insert(data_path="rotation_euler",index=2,frame=frame(t))
    for t,depth in [(0,0),(.09,0),(.14,-.056),(.19,0),(.95,0),(1,0)]:
        switch.location.z = top+depth
        switch.keyframe_insert(data_path="location",index=2,frame=frame(t))

    for i in range(21):
        angle = 220-260*i/20
        material_name = f"Indicator Cell {i+1:02d}"
        light_mat = material(material_name,"#224840",.08,.28)
        strength = emission(light_mat,config["accent_color"],.03)
        arc_cell(material_name,cx,cy,top+.019,.912,1.002,angle+3.6,angle-3.6,meter,light_mat)
        threshold = (i+.35)/21
        for j,(t,level) in enumerate(phases):
            if j:
                t0,v0 = phases[j-1]
                if (v0 < threshold <= level) or (level < threshold <= v0):
                    crossing = t0+(t-t0)*(threshold-v0)/(level-v0)
                    strength.default_value = 1.9 if v0 >= threshold else .025
                    strength.keyframe_insert(data_path="default_value",frame=max(1,frame(crossing)-1))
                    strength.default_value = 1.9 if level >= threshold else .025
                    strength.keyframe_insert(data_path="default_value",frame=frame(crossing))
            strength.default_value = 1.9 if level >= threshold else .025
            strength.keyframe_insert(data_path="default_value",frame=frame(t))

    aim = empty("Camera Focus",(0,.03,.73),studio)
    optics = bpy.data.cameras.new("Product Optics")
    cam = bpy.data.objects.new("Travelling Product Camera",optics)
    studio.objects.link(cam)
    tracking = cam.constraints.new("TRACK_TO")
    tracking.target,tracking.track_axis,tracking.up_axis = aim,"TRACK_NEGATIVE_Z","UP_Y"
    optics.dof.use_dof = True
    optics.dof.focus_object = aim
    optics.dof.aperture_fstop = 7.1
    scene.camera = cam
    ratio = config["width"]/config["height"]
    # Increase The Distance For A Narrow Portrait Gate Or A Wide Landscape Gate.
    distance = max(1.32,1.2/ratio) if ratio < 1 else max(1.32,ratio/1.12)
    travel = config["camera_travel"]
    for t,offset,lens_mm in [(0,(-1.2,-.4,.0),49),(.52,(0,.0,.35),52),(1,(1.15,.15,.48),54)]:
        base = (2.9,-5.8,5.65)
        cam.location = tuple(aim.location[j]+(base[j]+offset[j]*travel)*distance for j in range(3))
        cam.keyframe_insert(data_path="location",frame=frame(t))
        optics.lens = lens_mm
        optics.keyframe_insert(data_path="lens",frame=frame(t))

    def area(name,loc,energy,size,tint):
        data = bpy.data.lights.new(name,"AREA")
        data.energy,data.shape,data.size = energy,"DISK",size
        data.color = rgb(tint)[:3]
        light = bpy.data.objects.new(name,data)
        studio.objects.link(light)
        light.location = loc
        light.rotation_euler = (aim.location-Vector(loc)).to_track_quat("-Z","Y").to_euler()
    area("Large Softbox Left",(-4,-3.4,7),780,5.4,"#FFFFFF")
    area("Long Rim Right",(3.6,2.7,4.4),790,3.0,"#D1EFFF")
    area("Warm Dial Reflection",(-3.4,3.6,3.0),370,2.5,"#FFDAC7")
    area("Front Fill",(1.5,-4.8,3.1),220,4.0,"#EEF3FF")
    world = bpy.data.worlds.new("Studio Ambient")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = rgb("#BEC9CE")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .22
    scene.world = world
    for name,t in (("Hold",0),("Key Press",.14),("Peak Level",.58),("Settled Level",.91)):
        scene.timeline_markers.new(name,frame=frame(t))
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = pivot
    for screen in bpy.data.screens:
        for area_space in screen.areas:
            if area_space.type == "VIEW_3D":
                area_space.spaces.active.region_3d.view_perspective = "CAMERA"
                area_space.spaces.active.overlay.show_overlays = False
                area_space.spaces.active.shading.color_type = "MATERIAL"
    return scene


def main():
    if not bpy.app.background:
        raise RuntimeError("Run This Builder In A Fresh Background Blender Process.")
    args = arguments()
    target = args.output.resolve()
    if target.suffix.lower() != ".blend" or target.exists() or not target.parent.is_dir():
        raise ValueError("Choose A New .blend Filename Inside An Existing Directory.")
    config = settings(args.config)
    scene = build(config)
    with tempfile.TemporaryDirectory(dir=target.parent,prefix=".pulse-dial-") as temp:
        source = Path(temp)/target.name
        result = bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
        if "FINISHED" not in result:
            raise OSError("Blender Could Not Save The Project.")
        try:
            os.link(source,target)
        except FileExistsError:
            raise
        except OSError:
            with target.open("xb") as out:
                try:
                    with source.open("rb") as inp:
                        shutil.copyfileobj(inp,out)
                except BaseException:
                    out.close()
                    target.unlink()
                    raise
    print(json.dumps({"project":str(target),"objects":len(scene.objects),"frames":scene.frame_end,"fps":scene.render.fps}))


if __name__ == "__main__":
    main()
