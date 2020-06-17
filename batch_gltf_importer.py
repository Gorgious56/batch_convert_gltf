# This is released under CC0 licence. Do with it what you wish. No result guaranteed whatsoever. V1 Released 20/06/16
# Go to https://github.com/Gorgious56/batch_convert_gltf for more information


import os
import bpy
from mathutils import Vector
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Operator


def batch_convert_gltf(context, blend_path, gltf_path, overwrite, target_faces, apply_decimate, unpack_textures):
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
    
    blends_in_parent_dir = [blend[:-6] for blend in os.listdir(blend_path) if os.path.splitext(blend)[-1] == ".blend"]
    
    for dir in os.listdir(gltf_path):
        if not overwrite and dir in blends_in_parent_dir:  # Do not overwrite if file already exists
            continue
        child_path = os.path.join(gltf_path + "\\" + dir)
        if not os.path.isdir(child_path):
            continue
        for content in os.listdir(child_path):
            if not os.path.splitext(content)[-1] == ".gltf":
                continue

            clear_file_and_import(child_path, content)

            mesh_object = clean_geometry(context)            
            root_obj = rename_objects(mesh_object, dir)
            clean_family(context, mesh_object, root_obj)
            decimate_geometry_and_create_driver(mesh_object, root_obj, target_faces, apply_decimate)

            link_family_to_collection(mesh_object)
            purge_and_save_file(blend_path, dir, unpack_textures)
            
            return
    
    return {'FINISHED'}


def clean_family(context, leaf, root):
    """
    Gets rid of any unwanted matrix empty and applies loc rot scale
    """
    bpy.ops.object.select_all(action='DESELECT')
    leaf.select_set(True)
    root.select_set(True)
    context.view_layer.objects.active = root
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action='INVERT')
    bpy.ops.object.delete(use_global=False, confirm=False)


def clear_file_and_import(child_path, file_path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=True)
    bpy.ops.import_scene.gltf(filepath=child_path + "\\" + file_path)   


def purge_and_save_file(blend_path, file_name, unpack_textures):
    if unpack_textures:
        bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()
    bpy.ops.wm.save_as_mainfile(filepath=blend_path + "\\" + file_name + ".blend")
    

def rename_objects(obj, file_name):
    def get_root(obj):
        parent = obj.parent
        while parent:
            obj = parent
            parent = obj.parent
        return obj

    root_obj = get_root(obj)
    
    obj.name = obj.data.name = file_name.upper()
    root_obj.name = obj.name + "_MAIN"

    return root_obj


def decimate_geometry_and_create_driver(obj, root_obj, target_faces, apply_decimate):    
    root_obj["target_faces"] = target_faces

    dec_mod = obj.modifiers.new("Decimate_collapse", 'DECIMATE')

    driver = dec_mod.driver_add("ratio").driver
    var = driver.variables.new()
    var.name = "target"
    var.type = 'SINGLE_PROP'
    target = var.targets[0]
    target.id_type = 'OBJECT'
    target.id = root_obj
    target.data_path = '["target_faces"]'    
    driver.expression = f"target / {max(1, len(obj.data.polygons))} if target > 0 else 1"

    if apply_decimate:
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Decimate_collapse")


def clean_geometry(context):
    def reset_origin(context, obj):
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        center = sum((Vector(b) for b in bbox_corners), Vector()) / 8
        context.scene.cursor.location = (
            center.x, 
            center.y, 
            min([vec.z for vec in bbox_corners]))
        print(center.x, 
            center.y,min([vec.z for vec in bbox_corners]))
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        bpy.ops.object.location_clear(clear_delta=False)
        context.scene.cursor.location = (0, 0, 0)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.location_clear(clear_delta=False)
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    mesh_object =  mesh_objects[0]
    context.view_layer.objects.active = mesh_object
    bpy.ops.object.join()
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    reset_origin(context, mesh_object)

    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.editmode_toggle()

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
    bl_idname = "batch_convert.gltf"  # important since its how bpy.ops.import_test.some_data is constructed
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
        default=8000,
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

    def execute(self, context):
        return batch_convert_gltf(
                context,
                blend_path=os.path.dirname(self.filepath),
                gltf_path=os.path.dirname(self.filepath),
                overwrite=self.overwrite,
                target_faces=self.target_faces,
                apply_decimate=self.apply_decimate,
                unpack_textures=self.unpack_textures,
                )


def menu_func_import(self, context):
    self.layout.operator(BatchConvertGLTF.bl_idname, text="Batch Convert GLTF Files")


def register():
    bpy.utils.register_class(BatchConvertGLTF)


def unregister():
    try:
        bpy.utils.unregister_class(BatchConvertGLTF)
    except RuntimeError:
        pass


if __name__ == "__main__":
    unregister()
    register()

    bpy.ops.batch_convert.gltf('INVOKE_DEFAULT')
