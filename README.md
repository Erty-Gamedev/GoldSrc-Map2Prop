# GoldSrc Map2Prop

## Introduction

GoldSrc Map2Prop is a tool for converting .rmf and .jmf files, as well as .obj files exported from the Steam version of J.A.C.K, to goldsrc .smd file that can then be compiled into a goldsrc format studio model without the hastle of using an 3D editor.

## Installation

No installation required, simply get the latest executable from [Releases](https://github.com/Erty-Gamedev/GoldSrc-Map2Prop/releases) and place it in your folder of choice.

## How To Use (Hammer/J.A.C.K .rmf/.jmf)

* Create your object(s) in a new project or copy object(s) from an existing project to a new, empty project as save as .rmf/.jmf file.
* To make use of smooth shading, either enable it in `config.ini`, or put the `_smooth{x}` suffix on the filename (this will override the config.ini settings for this file). `{x}` is an optional parameter for the angle threshold in degrees for when smooth shading will be applied (e.g. `_smooth60` will smooth all angles less than 60°).
* Place any .wad packages used in creating your object(s) in the project file directory to make use of the automatic texture extraction. Alternatively you can specify a wad list in `config.ini`, and/or specify game/mod directories for the application to search in (it will prioritize wad list first, game/mod directory second, project file directory last).
* Drag the .rmf/.jmf file onto the Map2Prop.exe executable. A .smd file and a .qc file will be created in the project file's directory. If autocompile is set to yes in `config.ini` (it is by default) and a valid [Sven Co-op studiomdl.exe](http://www.the303.org/backups/sven_studiomdl_2019.rar) is found, then the application will automatically compile the .qc for you.

## How To Use (J.A.C.K .obj)

* Create your object in J.A.C.K and go to *File* -> *Export to OBJ...* (note: this will export the *entire* map as an .obj file so make sure the object is by itself in its own file, e.g. by copy-pasting it into a new map).
* To make use of smooth shading, either enable it in `config.ini`, or put the `_smooth{x}` suffix on the filename (this will override the config.ini settings for this file). `{x}` is an optional parameter for the angle threshold in degrees for when smooth shading will be applied (e.g. `_smooth60` will smooth all angles less than 60°).
* Place any .wad packages used for making the .obj in its directory to make use of the automatic texture extraction. Alternatively you can specify a wad list in `config.ini`, and/or specify game/mod directories for the application to search in (it will prioritize wad list first, game/mod directory second, project file directory last).
* Drag the exported .obj file onto the Map2Prop.exe executable. A .smd file and a .qc file will be created in the .obj file's directory. If autocompile is set to yes in `config.ini` (it is by default) and a valid [Sven Co-op studiomdl.exe](http://www.the303.org/backups/sven_studiomdl_2019.rar) is found, then the application will automatically compile the .qc for you.

## Reporting Problems/Bugs

Please notify Erty (erty.gamedev@gmail.com) along with the project file (either .rmf/.jmf, or .obj and its associated .mtl file) that was used as well as the logs/ folder produced by the executable.

## Features

* Automatic triangulation of all >3-gons.
* Skipping of faces covered in NULL texture, as well as several other tool textures.
* Faces covered in {-prefixed textures will automatically be given the masked (transparent) rendermode.
* The project file directory will be checked for existence of any referenced textures, and if missing will attempt to find and extract it from .wad packages in the wad list and game/mod directory specified in `config.ini` and project file directory, and if failed it will notify the user of missing textures.
* Smooth shading that can be enabled with or without angle threshold using filename suffix parameter (`_smooth{x}`) or in `config.ini`.
* CLI interface (run `Map2Prop.exe --help` to see a list of arguments).

## Why is the Sven Co-op studiomdl.exe required for compilation?

The reason for requiring the Sven Co-op studiomdl.exe for compiling these models is because of how map textures work, i.e. they may tile or otherwise extend beyond the UV bounds. Legacy studiomdl.exe compilers will clamp UV coordinates which is no good for this. Don't worry, the compiled model will still work perfectly fine in vanilla Half-Life.

## Future

Currently planning on using an option to split up an input file into several models based on, for example, VISGroup or tied entity. Leaning towards the latter as the .jmf format's ability to nest VISGroup might make it complicated.

## Special Thanks

Thanks to Captain P for showing me the .rmf/.jmf parsing code from MESS!

### Alpha Testers
Many thanks goes out to the kind people who helped me test this program and provide useful feedback and suggestions during its alpha stage:
* SV BOY
* TheMadCarrot
* Descen
