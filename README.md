# GoldSrc Map2Prop

## Introduction

GoldSrc Map2Prop is a tool for converting .rmf and .jmf files, as well as .obj files exported from the Steam version of J.A.C.K, to goldsrc .smd file that can then be compiled into a goldsrc format studio model without the hastle of using an 3D editor.

## Installation

No installation required, simply get the latest executable from [Releases](https://github.com/Erty-Gamedev/GoldSrc-Map2Prop/releases) and place it in your folder of choice.

## How To Use

For most basic use you just need to ensure all required textures are in the same folder as the project file (the .rmf/.jmf/.obj file), or make use of automatic .wad extraction (explained further down). Then simply drag your project file onto the executable.

You may also use the CLI interface. Run `Map2Prop.exe -h` to list all available options.

The application will produce a .smd file as well as generate a .qc file already filled out for as a basic static prop.

#### Note: Model origin

The model will use the project file's origin as its own origin. Typically it's preferred to have the origin at the center bottom of the model to make it more convenient to place the model in-editor. This can also be adjusted with the `--offset` command line option.

### Automatic .wad extraction

Map2Prop is able to read and extract textures from .wad packages found in a wad list defined in `config.ini` or by command line, from a game/mod defined in `config.ini`, or within the project file's directory, prioritised in that order. The application will automatically do this for all texture files not found within the project file's directory.

### Smoothing

Smooth shading and the angle threshold for smoothing can be set in config.ini and/or command line, but may also be set by suffixing the file name with `_smooth{x}` where `{x}` is the optional parameter for angle threshold. Leaving out the threshold parameter or setting it to zero will smooth all edges of the model.

Example:<br>`mymodel_smooth60.rmf` will have smooth shading applied to all edges less than 60° apart.

### Skip faces

Neither input format does any "inside face" culling. This is not the same as backface culling, but rather the faces inside of objects will typically remain in these formats.
I recommend covering all unseen faces (as well as any other faces you want to skip) with *NULL* texture as these will be stripped out during the process.

### Autocompile

If the path to a [Sven Co-op studiomdl.exe](http://www.the303.org/backups/sven_studiomdl_2019.rar) is set up either in `config.ini` or through command line option (`-m`, `--studiomdl`), you may use autocompile (enabled by default in `config.ini`) to compile the .smd file into a GoldSrc .mdl model at the end of the conversion process.

### Exporting .obj file from J.A.C.K

*(Only available in the paid version of J.A.C.K)*

Either copy your object to a new, empty file or select the object in J.A.C.K and go to *File* -> *Export to OBJ...*

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
