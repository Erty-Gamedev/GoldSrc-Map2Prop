# Obj2GoldSmd

## Introduction

Obj2GoldSmd is a tool for converting .obj files exported from the Steam version of J.A.C.K to goldsrc .smd file that can then be compiled into a goldsrc format studio model without the hastle of using an 3D editor.

## How To Use

* Get the latest executable from [Releases](https://github.com/Erty-Gamedev/Obj2GoldSmd/releases).
* Drag the exported .obj file onto the Obj2GoldSmd.exe executable. A .smd file and a .qc file will be created in the .obj file's directory.
* Ensure that any textures used are extracted from its .wad package and placed in the same directory as the .smd file.
* The .qc file is now ready to be compiled with studiomdl.exe.

## Reporting Problems/Bugs

Please notify Erty (erty.gamedev@gmail.com) along with the .obj and associated .mtl file used as well as the logs/ folder produced by the executable.

## Features

* Automatic triangulation of all >3-gons.
* Skipping of faces covered in NULL texture.
* Faces covered in {-prefixed textures will automatically be given the masked (transparent) rendermode.
* The target directory will be checked for existence of any referenced textures and notify the user of missing textures.

## Future

One of the planned features is full commandline options support such as
specifying an output folder,
disabling NULL face skipping and setting masked rendermode on transparent textures,
and whether to use edge smoothing and the threshold for it.

It's also planned to implement .rmf/.jmf support.

## Special Thanks

Thanks to Captain P for showing me the .rmf/.jmf parsing code from MESS!

### Alpha Testers
Many thanks goes out to the kind people who helped me test this program durings its alpha stage:
* SV BOY
