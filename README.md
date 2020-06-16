# batch_convert_gltf
A script to batch convert gltf to blend format and apply some cleaning operations automatically, and reduce the number of polygons

The purpose of this script is to batch convert models gotten from various websites, from the gltf format, into a blend file.

Blender is a free and open-source software for 3D modelling (and a lot of other things !!)

This script must be used inside blender's interface.

Each file will be cleaned a little bit :
  The translation will be reset
  The different mesh objects will be joined into one
  The double vertices will be merged
  A decimate modifier will be added to lower the poly count


You have to tweak the last few lines to your liking :

blend_path : Replace the expression after the equal sign and between the double quotes by the path of where you want your blend files to be created
gltf_path : The path where your gltf folders are located. This path must be a folder which contains folders, in which there must be a gltf file, a bin file and a folder with the matching textures
overwrite : True if you want to replace the file if it already is located in the target folder (the name will be the same as the gltf folder), False if you don't want to
target_vertices : This is the amount of vertices your final object will have. Set to 0 to keep the same number
apply_decimate : Set to True to destructively reduce the number of vertices, set to False to keep it non-destructive and use a modifier.

How to run a script in blender : https://stackoverflow.com/q/11604548/7092409
