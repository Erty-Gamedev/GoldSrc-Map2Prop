# Obj2GoldSmd

## Introduction

Obj2GoldSmd is a tool for converting .obj files exported from the Steam version of J.A.C.K to goldsrc .smd file that can then be compiled into a goldsrc format studio model without the hastle of using an 3D editor.

## Installation

No installation required, simply get the latest executable from [Releases](https://github.com/Erty-Gamedev/Obj2GoldSmd/releases) and place it in your folder of choice.

## How To Use

* Create your object in J.A.C.K and go to *File* -> *Export to OBJ...* (note: this will export the *entire* map as an .obj file so make sure the object is by itself in its own file, e.g. by copy-pasting it into a new map).
* To make use of smooth shading, put the `_smooth{x}` suffix on the filename. `{x}` is an optional parameter for the angle threshold in degrees for when smooth shading will be applied (e.g. `_smooth60` will smooth all angles less than 60°).
* Place any .wad packages used for making the .obj in its directory to make use of the automatic texture extraction.
* Drag the exported .obj file onto the Obj2GoldSmd.exe executable. A .smd file and a .qc file will be created in the .obj file's directory.
* The .qc file is now ready to be compiled with studiomdl.exe.

## Reporting Problems/Bugs

Please notify Erty (erty.gamedev@gmail.com) along with the .obj and associated .mtl file used as well as the logs/ folder produced by the executable.

## Features

* Automatic triangulation of all >3-gons.
* Skipping of faces covered in NULL texture.
* Faces covered in {-prefixed textures will automatically be given the masked (transparent) rendermode.
* The target directory, and any .wad packages in it, will be checked for existence of any referenced textures and notify the user of missing textures.
* Smooth shading that can be enabled with our without angle threshold using filename suffix parameter (`_smooth{x}`).

## Future

One of the planned features is full commandline options support such as specifying an output folder, and disabling NULL face skipping and setting masked rendermode on transparent textures.

I'm also planning on adding config file support with paths to various games and mods directories so the converter can look in these directories for .wad packages to perform texture extraction on.
To avoid texture name conflicts there will additionally be a wadlist config parameter to tell the converter which .wad packages to search for the textures in.
The config file will also contain a list of parameter sets to easily re-use the same parameters for converting multiple .obj files.

It's also planned to implement .rmf/.jmf support.

## Special Thanks

Thanks to Captain P for showing me the .rmf/.jmf parsing code from MESS!

### Alpha Testers
Many thanks goes out to the kind people who helped me test this program and provide useful feedback and suggestions during its alpha stage:
* SV BOY
* TheMadCarrot
* Descen
