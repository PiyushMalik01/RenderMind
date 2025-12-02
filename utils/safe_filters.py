"""
Safety filters - Static checks for dangerous code patterns
"""

import re


# Blacklist of dangerous operations
DANGEROUS_PATTERNS = [
    # File system operations
    r'os\.system',
    r'os\.remove',
    r'os\.rmdir',
    r'shutil\.rmtree',
    r'subprocess\.',
    
    # Network operations
    r'urllib\.request',
    r'requests\.',
    r'socket\.',
    r'http\.',
    
    # Code execution
    r'eval\(',
    r'exec\(',
    r'__import__',
    r'compile\(',
    
    # File operations outside Blender
    r'open\(',
    r'file\(',
    r'with\s+open',
]

# Whitelist - only allow these imports
ALLOWED_IMPORTS = {
    'bpy',
    'mathutils',
    'bmesh',
    'math',
    'random',
    'datetime',
}


def check_dangerous_patterns(code):
    """
    Check for dangerous code patterns
    Returns: (is_safe, violations)
    """
    violations = []
    
    for pattern in DANGEROUS_PATTERNS:
        matches = re.finditer(pattern, code, re.IGNORECASE)
        for match in matches:
            violations.append({
                'pattern': pattern,
                'match': match.group(),
                'position': match.start()
            })
    
    return len(violations) == 0, violations


def check_imports(code):
    """
    Check if code only uses allowed imports
    Returns: (is_safe, disallowed_imports)
    """
    import_pattern = r'(?:from|import)\s+(\w+)'
    matches = re.finditer(import_pattern, code)
    
    disallowed = []
    for match in matches:
        module = match.group(1)
        if module not in ALLOWED_IMPORTS:
            disallowed.append(module)
    
    return len(disallowed) == 0, disallowed


def validate_code_safety(code):
    """
    Run all safety checks on code
    Returns: (is_safe, error_message)
    """
    # Check dangerous patterns
    patterns_safe, violations = check_dangerous_patterns(code)
    if not patterns_safe:
        violation_list = ', '.join([v['match'] for v in violations])
        return False, f"Dangerous patterns detected: {violation_list}"
    
    # Check imports
    imports_safe, disallowed = check_imports(code)
    if not imports_safe:
        return False, f"Disallowed imports: {', '.join(disallowed)}"
    
    # Check for basic Python syntax (try to compile)
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    
    return True, None


def sanitize_code(code):
    """
    Attempt to sanitize code by removing dangerous parts
    Returns: (sanitized_code, warnings)
    """
    warnings = []
    sanitized = code
    
    # Remove dangerous function calls
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sanitized, re.IGNORECASE):
            warnings.append(f"Removed dangerous pattern: {pattern}")
            sanitized = re.sub(pattern + r'[^)]*\)', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized, warnings
