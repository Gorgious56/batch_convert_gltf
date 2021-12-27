"""
Base module required for Blender registration
"""

from . import auto_load

bl_info = {
    "name": "Batch gltf Converter",
    "author": "Gorgious",
    "description":"Batch convert GLTF files",
    "blender": (3, 0, 0),
    "version": (0, 0, 2),
    "location": "",
    "warning": "",
    "category": "Import-Export"
}


def register():
    auto_load.init()
    auto_load.register()


def unregister():
    auto_load.unregister()
