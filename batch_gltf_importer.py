# This is released under CC0 licence. Do with it what you wish. No result guaranteed whatsoever. V2 Released 21/10/21
# Go to https://github.com/Gorgious56/batch_convert_gltf for more information

import os
import pathlib
import bpy
from mathutils import Matrix, Vector
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty
from bpy.types import Operator


def unselect_all(context):
    bpy.ops.object.select_all(action="DESELECT")
    context.view_layer.objects.active = None


def select_and_set_active(obj, context):
    unselect_all(context)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def scale_my_model(obj, scale, expected_dimension, context):
    dim = obj.dimensions[0] / expected_dimension
    i = 0
    while True:
        if dim // (10 ** i) == 0:
            break
        i += 1
    obj.scale = (scale / (10 ** i),) * 3
    select_and_set_active(obj, context)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def decimate_geometry_and_create_driver(obj, target_faces, apply_decimate):
    obj["target_faces"] = target_faces
    prop = obj.id_properties_ui("target_faces")
    prop.update(min=0)
    print(obj)
    # obj.property_overridable_library_set("target_faces", True)

    dec_mod = obj.modifiers.new("Decimate_collapse", "DECIMATE")

    driver = dec_mod.driver_add("ratio").driver
    var = driver.variables.new()
    var.name = "target"
    var.type = "SINGLE_PROP"
    target = var.targets[0]
    target.id_type = "OBJECT"
    target.id = obj
    target.data_path = '["target_faces"]'
    driver.expression = (
        f"target / {max(1, len(obj.data.polygons))} if target > 0 else 1"
    )

    if apply_decimate:
        bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Decimate_collapse")


def clean_geometry(context):
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    mesh_object = mesh_objects[0]

    window = context.window_manager.windows[0]
    screen = window.screen

    area_3dview = next(a for a in screen.areas if a.ui_type == "VIEW_3D")
    override_3dview = {
        "area": area_3dview,
        "window": window,
        "screen": screen,
        "active_object": mesh_object,
        "selected_objects": mesh_objects,
    }

    bpy.ops.object.join(override_3dview)

    area_properties = next(a for a in screen.areas if a.ui_type == "PROPERTIES")
    override_properties = {
        "area": area_properties,
        "window": window,
        "screen": screen,
        "active_object": mesh_object,
        "selected_objects": mesh_object,
        "apply_as": "DATA",
        "modifier": "weld",
    }
    bpy.ops.mesh.customdata_custom_splitnormals_clear(override_properties)
    bpy.ops.object.parent_clear(override_3dview, type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(
        override_3dview, location=True, rotation=True, scale=True
    )

    mesh_object.modifiers.new("weld", "WELD")
    bpy.ops.object.modifier_apply(override_properties, modifier="weld")

    bbox_corners = [
        mesh_object.matrix_world @ Vector(corner) for corner in mesh_object.bound_box
    ]
    center = sum((Vector(b) for b in bbox_corners), Vector()) / 8
    trans = Vector((center.x, center.y, min([vec[2] for vec in bbox_corners])))
    cursor_local_loc = mesh_object.matrix_world.inverted() @ trans
    mesh_object.data.transform(Matrix.Translation(-cursor_local_loc))

    return mesh_object


class BatchConvertGLTF(Operator, ImportHelper):
    bl_idname = "batch_convert.gltf"
    bl_label = "Batch Convert GLTF Files"

    filter_glob: StringProperty(
        default="",
        options={"HIDDEN"},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    write_in_subfolders: BoolProperty(
        name="Save in subfolders",
        description="If Checked, blend files will be saved in the source sub folders\nOtherwise they are saved in the root folder",
        default=True,
    )    
    
    overwrite: BoolProperty(
        name="Overwrite files",
        description="Overwrite the blend file if a file with the same name exists in the folder",
        default=True,
    )

    prevent_backup: BoolProperty(
        name="Remove Backup",
        description="Check to automatically delete the creation of backup files when 'Save Versions' is enabled in the preferences\nThis will prevent duplicating files when they are overwritten\nWarning : Backup files will be deleted permantently",
        default=False,
    )

    target_faces: IntProperty(
        name="Target Faces",
        description="The decimate modifier will give this number of polygons (0 keeps the same number of faces)",
        min=0,
        default=0,
    )

    apply_decimate: BoolProperty(
        name="Apply decimate modifier",
        description="Check this to destructively decimate the geometry",
        default=False,
    )

    unpack_textures: BoolProperty(
        name="Unpack Textures",
        description="Unpack the textures in a separate Textures folder. The blend file size will be lower",
        default=False,
    )

    scale_model: FloatProperty(
        name="Scale",
        description="Scale the model by this amount",
        default=1,
    )

    expected_dimension: IntProperty(
        name="Expected maximum dimension",
        description="Scale the model by this amount",
        default=1,
    )

    def execute(self, context):
        p = pathlib.Path(str(os.path.dirname(self.filepath)))
        gltfs = [fp for fp in p.glob("**/*.gltf") if fp.is_file()]
        for i, gltf in enumerate(gltfs):
            if i == 0:                
                wipe_and_purge_blend()
            print(f"{len(gltfs) - i} files left")            
            dir_name = os.path.dirname(gltf)
            gltf_basename = os.path.basename(dir_name)
            blend_file = (
                os.path.splitext(str(os.path.dirname(gltf if self.write_in_subfolders else dir_name)) + "\\" + str(gltf_basename))[0]
                + ".blend"
            )
            if os.path.exists(blend_file) and not self.overwrite:
                print(f"{blend_file} already exists. Do not overwrite.")
                continue
            import_and_clean(gltf, gltf_basename, context, self.target_faces, self.apply_decimate, self.scale_model, self.expected_dimension)           
            if self.unpack_textures:
                bpy.ops.file.unpack_all(method="WRITE_LOCAL")
            bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
            if os.path.exists(blend_file + "1") and self.prevent_backup:
                os.remove(blend_file + "1") 
            wipe_and_purge_blend()

        print("Batch conversion completed")
        return {"FINISHED"}

def wipe_and_purge_blend():    
    bpy.data.batch_remove(bpy.data.objects)
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

def import_and_clean(gltf, gltf_basename, context, target_faces, apply_decimate, scale_model, expected_dimension):
    bpy.ops.import_scene.gltf(filepath=str(gltf))

    mesh_object = clean_geometry(context)

    decimate_geometry_and_create_driver(mesh_object, target_faces, apply_decimate)

    mesh_object.users_collection[0].objects.unlink(mesh_object)
    bpy.data.collections[0].objects.link(mesh_object)

    scale_my_model(mesh_object, scale_model, expected_dimension, context)

    bpy.data.batch_remove([o for o in bpy.data.objects if o != mesh_object])

    mesh_object.name = mesh_object.data.name = gltf_basename.title().replace("_", " ").replace("-", " ")


def menu_func_import(self, context):
    self.layout.operator(BatchConvertGLTF.bl_idname, text="Batch Convert GLTF Files")


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
