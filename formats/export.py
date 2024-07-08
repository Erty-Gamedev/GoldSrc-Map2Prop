from typing import Dict, List, Tuple, Optional, Final
import os, subprocess
from shutil import copy2
from pathlib import Path
import logging
from dataclasses import dataclass
from formats.base_classes import BaseReader
from configutil import config
from formats.obj_reader import ObjReader
from formats.map_reader import MapReader, Entity
from geoutil import (Polygon, Vertex, Vector3D, geometric_center,
                     flip_faces, deg2rad, point_in_bounds,
                     smooth_near_normals, smooth_all_normals)

logger = logging.getLogger(__name__)


CONVERT_TO_MAPPING: Final[Dict[int, str]] = {
    0: 'cycler',
    1: 'cycler_sprite',
    2: 'env_sprite',
    3: 'item_generic',
    4: 'monster_furniture',
    5: 'monster_generic',
}

@dataclass
class RawModel:
    outname: str
    subdir: Path
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
    rename_chrome: bool


def prepare_models(filename: str, filereader: BaseReader) -> Dict[str, RawModel]:
    models: Dict[str, RawModel] = {}
    outputdir = config.output_dir

    n = 0
    for entity in filereader.entities:
        if not entity.brushes:
            continue

        if config.mapcompile and entity.classname != 'func_map2prop':
            continue

        outname = filename
        own_model = False
        subdir = ''

        if entity.classname == 'worldspawn' and not isinstance(filereader, MapReader):
            entity.properties['wad'] = ';'.join(
                [p.resolve().as_posix() for p in filereader.wadhandler.used_wads]
            )

        if entity.classname == 'func_map2prop':
            if 'spawnflags' in entity.properties and (int(entity.properties['spawnflags']) & 1):
                continue  # Model is disabled
            if 'parent_model' in entity.properties and entity.properties['parent_model']:
                # Entity uses a template, model is defined in parent.
                # We can still find its origin to store it on the entity.
                for brush in entity.brushes:
                    if not brush.all_points: continue  # Skip empty brushes

                    if brush.is_tool_brush('origin'):
                        ori = geometric_center(brush.bounds)
                        entity.properties['origin'] = f"{ori.x} {ori.y} {ori.z}"
                        break
                continue  # Don't need to do anything else
            if 'own_model' in entity.properties and entity.properties['own_model'] == '1':
                own_model = True
                outname = f"{filename}_{n}"
                if 'outname' in entity.properties and entity.properties['outname']:
                    outname = f"{entity.properties['outname']}"
                    if entity.properties['outname'] in models:
                        outname = f"{outname}_{n}"
                        n += 1
            if 'subdir' in entity.properties and entity.properties['subdir']:
                subdir = f"{entity.properties['subdir']}/"
        
            if config.mapcompile and config.mod_path:
                parent_folder = (config.mod_path / 'models' / outputdir / f"{subdir}{outname}.mdl").parent
            else:
                parent_folder = (outputdir / f"{subdir}{outname}.mdl").parent
            
            if not parent_folder.is_dir():
                parent_folder.mkdir()

            entity.properties['model'] = f"models/{outputdir}/{subdir}{outname}.mdl"

        scale = config.qc_scale
        rotation = config.qc_rotate
        smoothing = config.smoothing
        chrome = config.renamechrome
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
            
            if 'chrome' in entity.properties:
                chrome = int(entity.properties['chrome']) == 1

        if outname not in models:
            models[outname] = RawModel(
                outname=outname,
                subdir=subdir,
                polygons=[],
                offset=Vector3D.zero(),
                bounds=(Vector3D.zero(), Vector3D.zero()),
                clip=(Vector3D.zero(), Vector3D.zero()),
                smoothing=smoothing,
                alwaysmooth=[],
                neversmooth=[],
                scale=scale,
                rotation=rotation,
                maskedtextures=[],
                rename_chrome=chrome
            )

        origin_found: bool = False
        bound_found: bool = False
        clip_found: bool = False
        for brush in entity.brushes:
            if not brush.all_points:  # Skip empty brushes
                continue

            # Look for ORIGIN brushes, use first found
            if models[outname].offset == Vector3D(0, 0, 0) and brush.is_tool_brush('origin'):
                if origin_found:
                    logger.info(f"Multiple ORIGIN brushes found in {entity.classname} "\
                                f"near {brush.center}")
                    continue
                if entity.classname == 'worldspawn' or own_model:
                    ori = geometric_center(brush.bounds)
                    models[outname].offset = ori
                    entity.properties['origin'] = f"{ori.x} {ori.y} {ori.z}"
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

            # Look for CLIPBEVEL brushes
            if brush.is_tool_brush('clipbevel'):
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].neversmooth.append(brush.bounds)
                continue  # Don't add brush

            # Look for BEVEL brushes
            if brush.is_tool_brush('bevel'):
                if entity.classname == 'worldspawn' or own_model:
                    models[outname].alwaysmooth.append(brush.bounds)
                continue  # Don't add brush

            if brush.maskedtextures:
                for texture in brush.maskedtextures:
                    if texture not in models[outname].maskedtextures:
                        models[outname].maskedtextures.append(texture)

            models[outname].polygons.extend(brush.all_polygons)

            if brush.has_contentwater:
                models[outname].polygons.extend(flip_faces(brush.all_polygons))
    
    return models


def vertex_in_list(vertex: Vertex,
                   vertex_list: Dict[Vector3D, List[Vertex]]) -> Optional[Vector3D]:
    for other in vertex_list:
        if vertex.v == other:
            return other
    return None


def apply_smooth(models: Dict[str, RawModel]) -> None:
    for model in models.values():
        if model.smoothing == 0.0:
            continue

        vertices: Dict[Vector3D, List[Vertex]] = {}
        flipped_vertices: Dict[Vector3D, List[Vertex]] = {}
        always_smooth: Dict[Vector3D, List[Vertex]] = {}
        flipped_always_smooth: Dict[Vector3D, List[Vertex]] = {}
        
        for polygon in model.polygons:
            for vertex in polygon.vertices:
                skip = False
                if model.neversmooth:
                    for bounds in model.neversmooth:
                        if point_in_bounds(vertex.v, bounds):
                            skip = True
                            break

                if skip: continue

                should_alwayssmooth = False
                if model.alwaysmooth:
                    for bounds in model.alwaysmooth:
                        if point_in_bounds(vertex.v, bounds):
                            should_alwayssmooth = True
                            break

                if vertex.flipped:
                    vlist = flipped_always_smooth if should_alwayssmooth else flipped_vertices
                else:
                    vlist = always_smooth if should_alwayssmooth else vertices
                
                if (other := vertex_in_list(vertex, vlist)):
                    vertex.v = other  # Merge near vertices
                    vlist[vertex.v].append(vertex)
                else:
                    vlist[vertex.v] = [vertex]
                    
    
        angle_threshold = deg2rad(model.smoothing)
        smooth_near_normals(vertices, angle_threshold)
        smooth_near_normals(flipped_vertices, angle_threshold)
        smooth_all_normals(always_smooth)
        smooth_all_normals(flipped_always_smooth)


def rename_chrome(models: Dict[str, RawModel], outputdir: Path) -> None:
    for model in models.values():
        if not model.rename_chrome:
            continue

        for polygon in model.polygons:
            if 'CHROME' not in polygon.texture.upper():
                continue
            
            texture_filepath = outputdir / f"{polygon.texture}.bmp"
            if not texture_filepath.exists():
                FileNotFoundError(f"Could not find {texture_filepath}")
            
            new_name = polygon.texture.upper().replace('CHROME', 'CHRM')
            new_filepath = outputdir / f"{new_name}.bmp"

            if not new_filepath.exists():
                copy2(texture_filepath, new_filepath)

            polygon.texture = new_name

    return None


def process_models(filename: str, outputdir: Path, filereader: BaseReader) -> int:
    models = prepare_models(filename, filereader)

    apply_smooth(models)
    rename_chrome(models, outputdir)

    processed = [m for m in models.values() if m.polygons]
    num_models = len(models)

    if not num_models:
        logger.info(f"No props found in {filename}")
        return 1
    if num_models == 1:
        logger.info(f"{filename} prepared.")
    else:
        logger.info(f"{len(processed)} models from {filename} prepared.")

    returncodes = 0
    failed: List[str] = []
    for model in processed:
        if not model.polygons:  # Skip empty models, such as empty worldspawns
            continue
    
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
    
    return returncodes


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
                output.write(f"{line}\n")

        output.write("end\n")
        logger.info(f"Successfully written to {outputdir / f"{model.outname}.smd"}")
    return

def write_qc(model: RawModel, outputdir: Path) -> None:
    with open(outputdir / f"{model.outname}.qc", 'w') as output:
        logger.info('Writing .qc file')

        rendermodes = ''
        if model.maskedtextures:
            for texture in model.maskedtextures:
                rendermodes += f"$texrendermode {texture}.bmp masked\n"

        if model.offset != Vector3D.zero():
            offset = f"{model.offset.x} {model.offset.y} {model.offset.z}"
        else:
            offset = config.qc_offset

        bbox = ''
        if model.bounds != (Vector3D.zero(), Vector3D.zero()):
            bmin = model.bounds[0] - model.offset
            bmax = model.bounds[1] - model.offset
            bbox = f"$bbox {bmin.x} {bmin.y} {bmin.z} {bmax.x} {bmax.y} {bmax.z}\n"

        cbox = ''
        if model.clip != (Vector3D.zero(), Vector3D.zero()):
            bmin = model.clip[0] - model.offset
            bmax = model.clip[1] - model.offset
            cbox = f"$cbox {bmin.x} {bmin.y} {bmin.z} {bmax.x} {bmax.y} {bmax.z}\n"

        output.write(f"""/*
 Automatically generated by Erty's GoldSrc Map2Prop.
*/

$modelname {model.subdir}{model.outname}.mdl
$cd "."
$cdtexture "."
$scale {model.scale}
$origin {offset} {model.rotation}
{rendermodes}{bbox}{cbox}$gamma {config.qc_gamma}
$body studio "{model.outname}"
$sequence "Generated_with_Erty's_Map2Prop" "{model.outname}"
""")
        logger.info(f"Successfully written to {outputdir}/{model.subdir}{model.outname}.qc")
    return


def compile(model: RawModel, outputdir: Path, filereader: BaseReader) -> int:
    if not config.studiomdl or not config.studiomdl.is_file():
        logger.info(
            'Autocompile enabled, but could not proceed. '\
            f"{config.studiomdl} was not found or is not a file.")
    elif filereader.missing_textures:
        logger.info(
            'Autocompile enabled, but could not proceed. '\
            'Model has missing textures. Check logs for more info.')
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
                    'Something went wrong. Check the compiler output '\
                    'above for errors.')
        except Exception:
            returncode = 1
            logger.exception('Model compilation failed with exception')
            
        os.chdir(current_dir)
    return returncode

    
def rewrite_map(filepath: Path, filereader: MapReader) -> None:
    filedir = filepath.parent
    filename = filepath.stem

    # Create a backup
    copy2(filepath, filedir / f"{filename}.m2p")

    # Not a true edict as we all know and love.
    # It is just to map func_map2prop entities to their targetnames
    edict: Dict[str, Entity] = {}
    for entity in filereader.entities:
        if entity.classname != 'func_map2prop':
            continue

        if not 'targetname' in entity.properties or not entity.properties['targetname']:
            continue
        
        if entity.properties['targetname'] in edict:
            logger.info('Naming conflict: Multiple func_map2prop '\
                        f"entities with name '{entity.properties['targetname']}'. "\
                        'Only the first one will be used as template parent')
            continue
        
        # Reset entity angles, as they're baked into the model now
        entity.properties['angles'] = '0 0 0'

        edict[entity.properties['targetname']] = entity
    
    # Convert func_map2prop entities
    with filepath.open('w') as file:
        for entity in filereader.entities:
            if entity.classname != 'func_map2prop':
                file.write(entity.raw)
                continue

            kvs = entity.properties

            if 'spawnflags' in kvs and (int(kvs['spawnflags']) & 1):
                continue  # Entity is disabled, skip

            if 'parent_model' in kvs and kvs['parent_model']:
                parent_model = kvs['parent_model']
                if parent_model not in edict:
                    logger.info(f"Entity with invalid template parent near {kvs['origin']}")
                
                parent = edict[parent_model]
                kvs['model'] = parent.properties['model']
            
            new_class = 'env_sprite'
            if 'convert_to' in kvs and kvs['convert_to']:
                convert_to = kvs['convert_to']
                if convert_to.isdigit() and int(convert_to) in CONVERT_TO_MAPPING:
                    new_class = CONVERT_TO_MAPPING[int(convert_to)]
                else:
                    new_class = convert_to

            spawnflags = 0
            if new_class.startswith('monster_'):
                spawnflags |= 16  # Prisoner
            if new_class == 'monster_generic':
                spawnflags |= 4  # Not solid
            
            new_raw = "{\n" f"\"classname\" \"{new_class}\"\n"\
                f"\"model\" \"{kvs['model']}\"\n"\
                f"\"spawnflags\" \"{spawnflags}\"\n"
            if 'angles' in kvs and kvs['angles']:
                new_raw += f"\"angles\" \"360 {kvs['angles'].split(' ')[1]} 360\"\n"
            if 'origin' in kvs and kvs['origin']:
                new_raw += f"\"origin\" \"{kvs['origin']}\"\n"
            new_raw += "}\n"

            file.write(new_raw)

    return None
