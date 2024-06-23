# -*- coding: utf-8 -*-

from typing import Dict, List, Tuple
import os, subprocess
from pathlib import Path
import logging
from dataclasses import dataclass
from formats.base_classes import BaseReader
from configutil import config
from formats.obj_reader import ObjReader
from geoutil import Polygon, Vertex, Vector3D, flip_faces, average_normals

logger = logging.getLogger(__name__)


@dataclass
class RawModel:
    outname: str
    polygons: List[Polygon]
    offset: Vector3D
    bounds: Tuple[Vector3D, Vector3D]
    clip: Tuple[Vector3D, Vector3D]
    smoothing: float
    alwaysmooth: List[Tuple[Vector3D, Vector3D]]
    neversmooth: List[Tuple[Vector3D, Vector3D]]
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
        smoothing = config.smoothing_treshhold
        if entity.classname == 'worldspawn' or own_model:
            if 'scale' in entity.properties and entity.properties['scale']:
                scale = float(entity.properties['scale'])
                if scale == 0.0: scale = 1.0
            
            if 'angles' in entity.properties:
                angles = entity.properties['angles'].split(' ')
                if len(angles) == 3 and angles != ['0', '0', '0']:
                    rotation = (rotation + float(angles[1])) % 360
            
            if 'smoothing' in entity.properties:
                smoothing = float(entity.properties['smoothing'])

        if outname not in models:
            models[outname] = RawModel(
                outname=outname,
                polygons=[],
                offset=Vector3D.zero(),
                bounds=(Vector3D.zero(), Vector3D.zero()),
                clip=(Vector3D.zero(), Vector3D.zero()),
                smoothing=smoothing,
                alwaysmooth=(Vector3D.zero(), Vector3D.zero()),
                neversmooth=(Vector3D.zero(), Vector3D.zero()),
                scale=scale,
                rotation=rotation,
                maskedtextures=[],
            )

        origin_found: bool = False
        bound_found: bool = False
        clip_found: bool = False
        for brush in entity.brushes:
            # Look for ORIGIN brushes, use first found
            if models[outname].offset == Vector3D(0, 0, 0) and brush.is_tool_brush('origin'):
                if origin_found:
                    logger.info(f"Multiple ORIGIN brushes found in {entity.classname} "\
                                f"near {brush.center}")
                    continue
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].offset = brush.center
                origin_found = True
                continue  # Don't add brush

            # Look for BOUNDINGBOX brushes, use first found
            if models[outname].bounds == (Vector3D.zero(), Vector3D.zero())\
                and brush.is_tool_brush('boundingbox'):
                if bound_found:
                    logger.info(f"Multiple BOUNDINGBOX brushes found in {entity.classname} "\
                                f"near {brush.center}")
                    continue
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].bounds = brush.bounds
                bound_found = True
                continue  # Don't add brush

            # Look for CLIP brushes, use first found
            if models[outname].clip == (Vector3D.zero(), Vector3D.zero())\
                and brush.is_tool_brush('clip'):
                if clip_found:
                    logger.info(f"Multiple CLIP brushes found in {entity.classname} "\
                                f"near {brush.center}")
                    continue
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].clip = brush.bounds
                clip_found = True
                continue  # Don't add brush

            # Look for BEVEL brushes
            if models[outname].alwaysmooth == (Vector3D.zero(), Vector3D.zero())\
                and brush.is_tool_brush('bevel'):
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].alwaysmooth.append(brush.bounds)
                continue  # Don't add brush

            # Look for BEVELCLIP brushes
            if models[outname].neversmooth == (Vector3D.zero(), Vector3D.zero())\
                and brush.is_tool_brush('bevelclip'):
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].neversmooth.append(brush.bounds)
                continue  # Don't add brush

            if brush.maskedtextures:
                for texture in brush.maskedtextures:
                    if texture not in models[outname].maskedtextures:
                        models[outname].maskedtextures.append(texture)

            models[outname].polygons.extend(brush.all_polygons)

            if brush.has_contentwater:
                models[outname].polygons.extend(flip_faces(brush.all_polygons))
    
    return models


def vertex_in_list(vertex: Vertex, vertex_list: List[Vertex]) -> bool:
    for other in vertex_list:
        if vertex.v == other:
            return True
    return False


def apply_smooth(models: Dict[str, RawModel]) -> Dict[str, RawModel]:
    for model in models.values():
        if model.smoothing == 0.0:
            continue

        vertices: Dict[Vector3D, List[Vertex]] = {}
        flipped_vertices: Dict[Vector3D, List[Vertex]] = {}
        vertex_polygon_map: Dict[Vector3D, List[Polygon]] = {}
        flipped_vertex_polygon_map: Dict[Vector3D, List[Polygon]] = {}
        for polygon in model.polygons:
            if polygon.flipped:
                vlist = flipped_vertices
                vpolymap = flipped_vertex_polygon_map
            else:
                vlist = vertices
                vpolymap = vertex_polygon_map

            for vertex in polygon.vertices:
                if not vertex_in_list(vertex, vlist):
                    vlist[vertex.v] = [vertex]
                else:
                    vlist[vertex.v].append(vertex)
                if vertex.v not in vpolymap:
                    vpolymap[vertex.v] = [polygon]
                    continue
                if polygon not in vpolymap[vertex.v]:
                    vpolymap[vertex.v].append(polygon)
    
        for vertex, points in vertices.items():
            normals = {p.normal: p.normal for p in vertex_polygon_map[vertex] if not p.flipped}
            averaged = average_normals(normals.values())
            for point in points:
                point.n = averaged
    
        for vertex, points in flipped_vertices.items():
            normals = {p.normal: p.normal for p in flipped_vertex_polygon_map[vertex] if p.flipped}
            averaged = average_normals(normals.values())
            for point in points:
                point.n = averaged

    return models


def process_models(filename: str, outputdir: Path, filereader: BaseReader) -> None:
    models = prepare_models(filename, filereader)
    models = apply_smooth(models)
    num_models = len(models)

    if not num_models:
        logger.info(f"No props found in {filename}")
        return
    if num_models == 1:
        logger.info(f"{filename} prepared.")
    else:
        logger.info(f"{len(models)} models from {filename} prepared.")

    returncodes = 0
    failed: List[str] = []
    for model in models.values():
        write_smd(model, outputdir, filereader)
        write_qc(model, outputdir)

        if config.autocompile:
            if (returncode := compile(model, outputdir, filereader)):
                failed.append(model.outname)
            returncodes += returncode

    
    if config.autocompile:
        if returncodes == 0:
            logger.info(f"Successfully compiled {num_models} models!")
        else:
            logger.info('Something went wrong during model compilation, check the logs.')
            logger.info(f"The following models did not compile: {', '.join(failed)}")


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


def compile(model: RawModel, outputdir: Path, filereader: BaseReader) -> int:
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
        os.chdir((Path(current_dir) / outputdir).absolute())

        returncode = 0
        try:
            completed_process = subprocess.run([
                config.studiomdl,
                Path(f"{model.outname}.qc"),
            ], check=False, timeout=config.timeout, capture_output=True, encoding='charmap')

            compile_output = completed_process.stdout

            returncode = completed_process.returncode
            if returncode == 0:
                logger.info(compile_output)
                logger.info(
                    f"{outputdir / model.outname}.mdl compiled successfully!")
            else:
                logger.warning(compile_output)
                logger.info(
                    'Something went wrong. Check the compiler output '
                    + 'above for errors.')
        except Exception:
            returncode = 1
            logger.exception('Model compilation failed with exception')
            
        os.chdir(current_dir)
    return returncode
