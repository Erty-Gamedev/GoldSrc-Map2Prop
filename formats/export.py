# -*- coding: utf-8 -*-

from typing import Dict, List
import os, subprocess
from pathlib import Path
import logging
from dataclasses import dataclass
from formats.base_classes import BaseReader
from configutil import config
from formats.obj_reader import ObjReader
from geoutil import Polygon, Vector3D, flip_faces

logger = logging.getLogger(__name__)


@dataclass
class RawModel:
    outname: str
    polygons: List[Polygon]
    offset: Vector3D
    scale: float
    rotation: float
    maskedtextures: List[str]


def prepare_models(filename: str, filereader: BaseReader) -> Dict[str, RawModel]:
    models: Dict[str, RawModel] = {}

    n = 0
    for entity in filereader.entities:
        outname = filename
        own_model = False

        if entity.classname == 'func_map2prop':
            if 'own_model' in entity.properties and entity.properties['own_model'] == '1':
                own_model = True
                outname = f"{filename}_{n}"
                if 'outname' in entity.properties and entity.properties['outname']:
                    outname = f"{entity.properties['outname']}"
                    if entity.properties['outname'] in models:
                        outname = f"{outname}_{n}"
                        n += 1
        
        scale = config.qc_scale
        rotation = config.qc_rotate
        if entity.classname == 'worldspawn' or own_model:
            if 'scale' in entity.properties and entity.properties['scale']:
                scale = float(entity.properties['scale'])
                if scale == 0.0: scale = 1.0
            
            if 'angles' in entity.properties:
                angles = entity.properties['angles'].split(' ')
                if len(angles) == 3 and angles != ['0', '0', '0']:
                    rotation = (rotation + float(angles[1])) % 360

        if outname not in models:
            models[outname] = RawModel(outname, [], Vector3D(0, 0, 0), scale, rotation, [])

        origin_found: bool = False
        for brush in entity.brushes:
            # Look for ORIGIN brushes, use first found
            if models[outname].offset == Vector3D(0, 0, 0) and brush.is_origin:
                if origin_found:
                    logger.info(f"Multiple ORIGIN brushes found in {entity.classname} "\
                                f"near {brush.center}")
                    continue
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].offset = brush.center
                origin_found = True
                continue  # Don't add brush

            if brush.maskedtextures:
                for texture in brush.maskedtextures:
                    if texture not in models[outname].maskedtextures:
                        models[outname].maskedtextures.append(texture)

            models[outname].polygons.extend(brush.all_polygons)

            if brush.has_contentwater:
                models[outname].polygons.extend(flip_faces(brush.all_polygons))
    
    return models


def process_models(filename: str, outputdir: Path, filereader: BaseReader) -> None:
    models = prepare_models(filename, filereader)
    num_models = len(models)

    if not num_models:
        logger.info(f"No props found in {filename}")
        return
    if num_models == 1:
        logger.info(f"{filename} prepared.")
    else:
        logger.info(f"{len(models)} models from {filename} prepared.")


    for model in models.values():
        write_smd(model, outputdir, filereader)
        write_qc(model, outputdir)

        if config.autocompile:
            compile(model, outputdir, filereader)


def write_smd(model: RawModel, outputdir: Path, filereader: BaseReader) -> None:
    with open(outputdir / f"{model.outname}.smd", 'w') as output:
        logger.info(f"Writing to {outputdir / f"{model.outname}.smd"}")

        output.write('''version 1
nodes
0 "root" -1
end
skeleton
time 0
0 0 0 0 0 0 0
end
triangles
''')

        for polygon in model.polygons:
            output.write(f"{polygon.texture}.bmp\n")

            for v in polygon.vertices:
                line = "0\t"
                if isinstance(filereader, ObjReader):
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.v.x, -v.v.z, v.v.y))
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.n.x, -v.n.z, v.n.y))
                    line += "{:.6f} {:.6f}".format(v.t.x, v.t.y + 1)
                else:
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.v.x, v.v.y, v.v.z))
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.n.x, v.n.y, v.n.z))
                    line += "{:.6f} {:.6f}".format(v.t.x, v.t.y + 1)
                output.write(line + "\n")

        output.write('end' + "\n")
        logger.info(f"Successfully written to {outputdir / f"{model.outname}.smd"}")
    return

def write_qc(model: RawModel, outputdir: Path) -> None:
    with open(outputdir / f"{model.outname}.qc", 'w') as output:
        logger.info('Writing .qc file')

        rendermodes = ''
        if model.maskedtextures:
            for texture in model.maskedtextures:
                rendermodes += f"$texrendermode {texture}.bmp masked\n"

        if model.offset != Vector3D(0, 0, 0):
            offset = f"{model.offset.x} {model.offset.y} {model.offset.z}"
        else: offset = config.qc_offset

        output.write(f"""/*
 Automatically generated by Erty's GoldSrc Map2Prop.
*/

$modelname {model.outname}.mdl
$cd "."
$cdtexture "."
$scale {model.scale}
$origin {offset} {model.rotation}
{rendermodes}$gamma {config.qc_gamma}
$body studio "{model.outname}"
$sequence "Generated_with_Erty's_Map2Prop" "{model.outname}"
""")
        logger.info(f"Successfully written to {outputdir / model.outname}.qc")
    return


def compile(model: RawModel, outputdir: Path, filereader: BaseReader) -> None:
    if not config.studiomdl or not config.studiomdl.is_file():
        logger.info(
            'Autocompile enabled, but could not proceed. '
            + f"{config.studiomdl} was not found or is not a file.")
    elif filereader.missing_textures:
        logger.info(
            'Autocompile enabled, but could not proceed. '
            + 'Model has missing textures. Check logs for more info.')
    else:
        logger.info('Autocompile enabled, compiling model...')

        current_dir = os.path.abspath(os.curdir)
        os.chdir(outputdir.absolute())

        try:
            completed_process = subprocess.run([
                config.studiomdl,
                Path(f"{model.outname}.qc"),
            ], check=False, timeout=config.timeout, capture_output=True)

            logger.info(completed_process.stdout.decode('charmap'))

            if completed_process.returncode == 0:
                logger.info(
                    f"{outputdir / model.outname}.mdl compiled successfully!")
            else:
                logger.info(
                    'Something went wrong. Check the compiler output '
                    + 'above for errors.')
        except Exception:
            logger.exception('Model compilation failed with exception')
            
        os.chdir(current_dir)
    return
