"""
Base module required for Blender registration
"""

import subprocess
import pkg_resources
import sys
from . import auto_load

bl_info = {
    "name": "Batch gltf Converter",
    "author": "Gorgious",
    "description":"Batch convert GLTF files",
    "blender": (3, 0, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Import-Export"
}


def register():
    auto_load.init()
    auto_load.register()


def unregister():
    auto_load.unregister()
