"""
Model Library - Search and import 3D models from local collection
"""

import bpy
import os
from pathlib import Path
import re


def get_models_directory():
    """Get the assets directory path"""
    addon_dir = Path(__file__).parent.parent  # Go up to main addon dir
    assets_dir = addon_dir / "assets"
    return assets_dir


def search_models(query):
    """
    Search for 3D model files matching the query
    Returns list of (filepath, filename, category) tuples
    """
    assets_dir = get_models_directory()
    
    print(f"[ModelLibrary] Assets directory: {assets_dir}")
    print(f"[ModelLibrary] Directory exists: {assets_dir.exists()}")
    
    if not assets_dir.exists():
        print(f"[ModelLibrary] Assets directory not found!")
        return []
    
    # Supported file extensions
    supported_formats = {'.blend', '.fbx', '.obj', '.gltf', '.glb', '.stl'}
    
    # Normalize query for matching
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    
    print(f"[ModelLibrary] Query: '{query_lower}', Words: {query_words}")
    
    matches = []
    file_count = 0
    
    # Walk through assets directory
    for root, dirs, files in os.walk(assets_dir):
        print(f"[ModelLibrary] Scanning directory: {root}")
        print(f"[ModelLibrary] Files found: {files}")
        for file in files:
            file_count += 1
            file_lower = file.lower()
            file_path = Path(root) / file
            file_ext = file_path.suffix.lower()
            
            print(f"[ModelLibrary] Checking file: {file} (ext: {file_ext})")
            
            # Check if it's a supported format
            if file_ext not in supported_formats:
                print(f"[ModelLibrary]   - Skipped (unsupported format)")
                continue
            
            # Get relative category path
            try:
                rel_path = file_path.parent.relative_to(assets_dir)
                category = str(rel_path) if str(rel_path) != '.' else 'root'
            except:
                category = 'root'
            
            # Score the match
            score = 0
            file_stem = file_path.stem.lower()
            
            print(f"[ModelLibrary]   - File stem: '{file_stem}', Category: '{category}'")
            
            # Remove common prefixes/suffixes for better matching
            clean_filename = file_stem.replace('food_', '').replace('_01', '').replace('_02', '').replace('_4k', '').replace('_8k', '')
            
            print(f"[ModelLibrary]   - Clean filename: '{clean_filename}'")
            
            # Filter meaningful query words (exclude common words like 'a', 'an', 'the', 'add', 'create', 'make')
            meaningful_words = [w for w in query_words if len(w) >= 3 and w not in ['add', 'the', 'create', 'make', 'place', 'import', 'put']]
            print(f"[ModelLibrary]   - Meaningful words: {meaningful_words}")
            
            # Exact match gets highest score
            if query_lower == file_stem or query_lower == clean_filename:
                score = 100
                print(f"[ModelLibrary]   - EXACT MATCH! Score: {score}")
            # Check if any meaningful word matches the filename exactly
            elif any(word == clean_filename for word in meaningful_words):
                score = 100
                print(f"[ModelLibrary]   - WORD EXACT MATCH! Score: {score}")
            # Check if any meaningful word is in cleaned filename
            elif any(word in clean_filename for word in meaningful_words):
                score = 90
                print(f"[ModelLibrary]   - Meaningful word in filename! Score: {score}")
            # Check if query is in cleaned filename
            elif query_lower in clean_filename:
                score = 85
                print(f"[ModelLibrary]   - Query in clean filename! Score: {score}")
            # Check if query is in original filename
            elif query_lower in file_stem:
                score = 80
                print(f"[ModelLibrary]   - Query in filename! Score: {score}")
            # Check if all query words are in filename (only if 2+ words)
            elif len(query_words) >= 2 and all(word in file_stem for word in query_words if len(word) > 2):
                score = 70
                print(f"[ModelLibrary]   - All words match! Score: {score}")
            # Single word match (must be at least 4 chars to avoid false positives)
            elif len(query_words) == 1 and len(query_lower) >= 4 and query_lower in file_stem:
                score = 60
                print(f"[ModelLibrary]   - Single word match! Score: {score}")
            # Category match alone is not enough
            else:
                score = 0
                print(f"[ModelLibrary]   - No match (score: 0)")
            
            if score > 0:
                print(f"[ModelLibrary]   ✓ ADDED TO MATCHES")
                matches.append({
                    'path': str(file_path),
                    'filename': file,
                    'category': category,
                    'score': score,
                    'format': file_ext
                })
    
    print(f"[ModelLibrary] Total files scanned: {file_count}")
    print(f"[ModelLibrary] Total matches: {len(matches)}")
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    return matches


def import_model(filepath, collection_name=None):
    """
    Import a 3D model file into Blender
    Returns (success, message, imported_objects)
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        return False, f"File not found: {filepath}", []
    
    file_ext = file_path.suffix.lower()
    imported_objects = []
    
    try:
        # Store objects before import
        objects_before = set(bpy.data.objects)
        
        # Import based on file type
        if file_ext == '.blend':
            # Import from .blend file
            with bpy.data.libraries.load(str(file_path), link=False) as (data_from, data_to):
                data_to.objects = data_from.objects
            
            # Add to scene
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
                    imported_objects.append(obj)
        
        elif file_ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=str(file_path))
        
        elif file_ext == '.obj':
            bpy.ops.import_scene.obj(filepath=str(file_path))
        
        elif file_ext in ['.gltf', '.glb']:
            bpy.ops.import_scene.gltf(filepath=str(file_path))
        
        elif file_ext == '.stl':
            bpy.ops.import_mesh.stl(filepath=str(file_path))
        
        else:
            return False, f"Unsupported format: {file_ext}", []
        
        # Get newly imported objects (for formats using operators)
        if not imported_objects:
            objects_after = set(bpy.data.objects)
            imported_objects = list(objects_after - objects_before)
        
        # Move to collection if specified
        if collection_name and imported_objects:
            # Create or get collection
            if collection_name not in bpy.data.collections:
                collection = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(collection)
            else:
                collection = bpy.data.collections[collection_name]
            
            # Move objects to collection
            for obj in imported_objects:
                # Unlink from current collections
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                # Link to target collection
                collection.objects.link(obj)
        
        obj_names = [obj.name for obj in imported_objects]
        return True, f"Imported {len(imported_objects)} object(s): {', '.join(obj_names)}", imported_objects
    
    except Exception as e:
        return False, f"Import failed: {str(e)}", []


def generate_import_code(model_info, user_prompt):
    """
    Generate Python code to import the model
    """
    filepath = model_info['path'].replace('\\', '\\\\')  # Escape backslashes
    filename = model_info['filename']
    
    code = f'''import bpy
from pathlib import Path

def rendermind_action(context):
    """Import {filename} model"""
    
    # Model path
    model_path = r"{filepath}"
    
    # Import the model
    file_ext = Path(model_path).suffix.lower()
    
    print(f"Importing {{file_ext}} model: {filename}")
    
    try:
        if file_ext == '.blend':
            with bpy.data.libraries.load(model_path, link=False) as (data_from, data_to):
                data_to.objects = data_from.objects
            
            # Link objects to the current scene collection
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
                    print(f"Imported: {{obj.name}}")
        
        elif file_ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=model_path)
        
        elif file_ext == '.obj':
            bpy.ops.import_scene.obj(filepath=model_path)
        
        elif file_ext in ['.gltf', '.glb']:
            bpy.ops.import_scene.gltf(filepath=model_path)
        
        elif file_ext == '.stl':
            bpy.ops.import_mesh.stl(filepath=model_path)
        
        print(f"✓ Successfully imported {filename}")
        
    except Exception as e:
        print(f"✗ Import failed: {{e}}")
        raise
'''
    
    return code


def register():
    pass


def unregister():
    pass
