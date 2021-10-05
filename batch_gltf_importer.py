# This is released under CC0 licence. Do with it what you wish. No result guaranteed whatsoever. V1 Released 20/06/16
# Go to https://github.com/Gorgious56/batch_convert_gltf for more information

import os
import pathlib
import bpy
from mathutils import Vector
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty
from bpy.types import Operator


def batch_convert_gltf(context, root_path, overwrite, target_faces, apply_decimate, unpack_textures, scale, expected_dimension):
    """
    Batch convert gltf files with some initial clean up :
        Resetting translation
        Joining mesh objects
        Removing doubles
        Adding a decimate modifier to reduce geometry density

    Arguments:
        context: Blender context
        blend_path : The output blend files will be saved in this folder
        gltf_path : This folder should contain folders which each contain a gltf file, a bin file and a folder with matching textures
        overwrite : Overwrite file if it already exists in the target directory
        target_faces : The amount of faces the mesh should have after decimation. A value of 0 keeps the same amount of verts.
        apply_decimate : Actually apply the modifier to reduce file size (destructive)
        unpack_textures : Unpack the textures in a separate Textures folder. The blend file size will be lower

    Returns:
        None

    Notes:
        The current file will freeze until the batch converting is finished
        Although you can follow the progress by toggling the window console before launching the script
        And the corresponding blend files will progressively be added to your target directory
        But there is no way to smoothly stop it once it began. You must kill the task in the task manager if you want to.

        After the operation is done, Change the target number of faces in the custom properties of the resulting mesh object.
    """

    p = pathlib.Path(str(root_path))
    for file_path in [fp for fp in p.glob('**/*.gltf') if fp.is_file()]:

        dir_name = os.path.dirname(file_path)
        gltf_name = os.path.basename(dir_name)
        blend_file = os.path.splitext(str(os.path.dirname(dir_name)) + "/" + str(gltf_name))[0] + ".blend"
        if os.path.exists(blend_file) and not overwrite:
            print(f"{blend_file} already exists. Do not overwrite.")
            continue
        clear_file_and_import(str(file_path))

        mesh_object = clean_geometry(context)
        mesh_object.name = mesh_object.data.name = gltf_name.capitalize()

        decimate_geometry_and_create_driver(mesh_object, target_faces, apply_decimate)

        link_family_to_collection(mesh_object)
        scale_model(mesh_object, scale, expected_dimension, context)
        mesh_object.asset_mark()
        delete_objects([o for o in bpy.data.objects if o.type == 'EMPTY'])      
        purge_and_save_file(str(blend_file), unpack_textures)


def delete_objects(objs):
    while objs:
        bpy.data.objects.remove(objs[0])
        objs.pop(0)


def unselect_all(context):
    bpy.ops.object.select_all(action='DESELECT')
    context.view_layer.objects.active = None


def select_and_set_active(obj, context):
    unselect_all(context)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def scale_model(obj, scale, expected_dimension, context):
    dim = obj.dimensions[0] / expected_dimension
    i = 0
    while True:
        if dim // (10 ** i) == 0:
            break
        i += 1
    obj.scale = (scale / (10 ** i),) * 3
    select_and_set_active(obj, context)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def clear_file_and_import(file_path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=True)
    bpy.ops.import_scene.gltf(filepath=file_path)


def purge_and_save_file(file_path, unpack_textures):
    if unpack_textures:
        bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()
    bpy.ops.wm.save_as_mainfile(filepath=file_path)


def decimate_geometry_and_create_driver(obj, target_faces, apply_decimate):
    obj["target_faces"] = target_faces

    dec_mod = obj.modifiers.new("Decimate_collapse", 'DECIMATE')

    driver = dec_mod.driver_add("ratio").driver
    var = driver.variables.new()
    var.name = "target"
    var.type = 'SINGLE_PROP'
    target = var.targets[0]
    target.id_type = 'OBJECT'
    target.id = obj
    target.data_path = '["target_faces"]'
    driver.expression = f"target / {max(1, len(obj.data.polygons))} if target > 0 else 1"

    if apply_decimate:
        bpy.ops.object.modifier_apply(
            apply_as='DATA', modifier="Decimate_collapse")


def clean_geometry(context):
    def reset_origin(context, obj):
        bbox_corners = [obj.matrix_world @
                        Vector(corner) for corner in obj.bound_box]
        center = sum((Vector(b) for b in bbox_corners), Vector()) / 8
        context.scene.cursor.location = (
            center.x,
            center.y,
            min([vec.z for vec in bbox_corners]))
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        bpy.ops.object.location_clear(clear_delta=False)
        context.scene.cursor.location = (0, 0, 0)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.location_clear(clear_delta=False)
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    mesh_object = mesh_objects[0]
    context.view_layer.objects.active = mesh_object
    bpy.ops.object.join()
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    reset_origin(context, mesh_object)

    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.editmode_toggle()

    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.location_clear(clear_delta=False)

    return mesh_object


def link_family_to_collection(child, col=None):
    if col is None:
        col = bpy.data.collections[0]
        col.name = child.name
    for prev_col in child.users_collection:
        prev_col.objects.unlink(child)
    col.objects.link(child)
    if child.parent:
        link_family_to_collection(child.parent, col)


class BatchConvertGLTF(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "batch_convert.gltf"
    bl_label = "Batch Convert GLTF Files"

    filter_glob: StringProperty(
        default="",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    overwrite: BoolProperty(
        name="Overwrite files",
        description="Overwrite the blend file if a file with the same name exists in the folder",
        default=True,
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
        batch_convert_gltf(
            context,
            root_path=os.path.dirname(self.filepath),
            overwrite=self.overwrite,
            target_faces=self.target_faces,
            apply_decimate=self.apply_decimate,
            unpack_textures=self.unpack_textures,
            scale=self.scale_model,
            expected_dimension=self.expected_dimension,
        )
        print("Batch conversion completed")
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(BatchConvertGLTF.bl_idname,
                         text="Batch Convert GLTF Files")


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
