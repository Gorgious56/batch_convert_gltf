# This is released under CC0 licence. Do with it what you wish. No result guaranteed whatsoever. V1 Released 20/06/16
# Go to https://github.com/Gorgious56/batch_convert_gltf for more information

import os
import bpy


def batch_convert_gltf(blend_path, gltf_path, overwrite, target_faces, apply_decimate):
    """
    Batch convert gltf files with some initial clean up :
        Resetting translation
        Joining mesh objects
        Removing doubles
        Adding a decimate modifier to reduce geometry density
        
    Arguments:
        blend_path : The output blend files will be saved in this folder
        gltf_path : This folder should contain folders which each contain a gltf file, a bin file and a folder with matching textures
        overwrite : Overwrite file if it already exists in the target directory
        target_faces : The amount of faces the mesh should have after decimation. A value of 0 keeps the same amount of verts.
        apply_decimate : Actually apply the modifier to reduce file size (destructive)
        
    Returns:
        None
        
    Notes:
        The current file will freeze until the batch converting is finished
        Although you can follow the progress by toggling the window console before launching the script
        And the corresponding blend files will progressively be added to your target directory
        But there is no way to smoothly stop it once it began. You must kill the task in the task manager if you want to.
        
        After the operation is done, Change the target number of vertices in the custom properties of the resulting mesh object.
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
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=True)

            bpy.ops.import_scene.gltf(filepath=child_path + "\\" + content)
            bpy.ops.object.select_all(action='SELECT')
            mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
            active_object = mesh_objects[0]
            bpy.context.view_layer.objects.active = active_object
            bpy.ops.object.join()
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles()
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.location_clear(clear_delta=False)
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            active_object["target_faces"] = target_faces
            
            add_decimate_modifier(active_object)
            if apply_decimate:
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Decimate_collapse")

            bpy.ops.outliner.orphans_purge()
            bpy.ops.outliner.orphans_purge()
            bpy.ops.wm.save_as_mainfile(filepath=blend_path + "\\" + dir + ".blend")


def add_decimate_modifier(obj):
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


if __name__ == "__main__":
    batch_convert_gltf(
        blend_path=r"C:\Users\natha\Downloads\Scans",
        gltf_path=r"C:\Users\natha\Downloads\Scans\GLTF",
        overwrite=True,
        target_faces=8000,
        apply_decimate=False,
        )
