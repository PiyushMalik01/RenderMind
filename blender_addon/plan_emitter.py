"""
Deterministic plan -> Blender Python script emitter.
Keep templates canonical so model outputs small DSL and emitter produces stable code.
Extend templates to add more operations.
"""

def register():
    pass

def unregister():
    pass

def emitter_plan_to_script(plan: str) -> str:
    """
    Very small DSL parser and template filler.
    Expects plan to contain keywords like 'uv_sphere', 'cylinder', 'vase', etc.
    Returns Python source with a single function: rendermind_action(context)
    """
    lines = [
        "def rendermind_action(context: dict) -> None:",
        "    import bpy"
    ]
    p = plan.lower()
    # Sphere template
    if "uv_sphere" in p or "sphere" in p:
        # attempt to parse radius and location (simple heuristics)
        r = 0.5
        loc = "(0,0,0.5)"
        if "r=" in p:
            try:
                # crude parse
                ii = p.index("r=") + 2
                r = float(p[ii:].split(",")[0].split()[0].strip(");"))
            except Exception:
                pass
        lines += [
            f"    bpy.ops.mesh.primitive_uv_sphere_add(radius={r}, location={loc})",
            "    obj = bpy.context.active_object",
            "    obj.name = 'rm_sphere'",
            "    mat = bpy.data.materials.new('rm_mat')",
            "    mat.use_nodes = True",
            "    bsdf = mat.node_tree.nodes.get('Principled BSDF')",
            "    if bsdf: bsdf.inputs['Base Color'].default_value=(0.8,0.2,0.2,1)",
            "    obj.data.materials.append(mat)"
        ]
    # Cylinder / vase template
    elif "cylinder" in p:
        lines += [
            "    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=0.6, location=(0,1,0.3))",
            "    obj = bpy.context.active_object",
            "    obj.name = 'rm_cylinder'",
            "    mat = bpy.data.materials.new('rm_ceramic')",
            "    mat.use_nodes = True",
            "    bsdf = mat.node_tree.nodes.get('Principled BSDF')",
            "    if bsdf: bsdf.inputs['Roughness'].default_value = 0.15",
            "    obj.data.materials.append(mat)"
        ]
    else:
        lines += ["    # Plan not implemented in emitter placeholder", "    print('Plan not implemented')"]
    return "\n".join(lines)
