#!/usr/bin/env python3
"""
Generates a text representation of the directory structure, focusing on specific file types.

This script walks through the specified directory and its subdirectories,
listing folders and files matching common source code extensions (.py, .json, .ts, .js).
It respects .gitignore files, excluding matching files and directories from the output.
"""

import os
import argparse
from pathlib import Path
import fnmatch
import sys
import ast
import re

# Define the set of file extensions to include
INCLUDED_EXTENSIONS = {'.py', '.json', '.ts', '.js'}

def get_file_size(filepath):
    """
    Gets the size of a file in bytes.
    
    Args:
        filepath (Path): Path to the file.
        
    Returns:
        int: Size in bytes, or 0 if file cannot be accessed.
    """
    try:
        return filepath.stat().st_size
    except (IOError, OSError):
        return 0

def format_file_size(size_bytes):
    """
    Formats file size into a human-readable string.
    
    Args:
        size_bytes (int): Size in bytes.
        
    Returns:
        str: Formatted size string (e.g., '1.2 KB', '3.4 MB').
    """
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 1)
    return f"{s} {size_names[i]}"

def read_gitignore(path):
    """
    Reads a .gitignore file and returns a list of patterns.

    Args:
        path (Path): The path object representing the directory containing .gitignore.

    Returns:
        list: A list of pattern strings from the .gitignore file.
              Returns an empty list if .gitignore does not exist.
    """
    gitignore_file = path / '.gitignore'
    if gitignore_file.is_file():
        try:
            with open(gitignore_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Filter out empty lines and comments (starting with #)
            patterns = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
            return patterns
        except (IOError, OSError):
            # Silently ignore errors reading .gitignore, behave as if it's empty
            pass
    return []

def parse_gitignore_patterns(patterns):
    """
    Parses .gitignore patterns into include and exclude lists.
    Patterns starting with ! are include patterns.
    """
    include_patterns = []
    exclude_patterns = []
    
    for pattern in patterns:
        if pattern.startswith('!'):
            include_patterns.append(pattern[1:])  # Remove the !
        else:
            exclude_patterns.append(pattern)
    
    return include_patterns, exclude_patterns

def is_ignored(name, full_path, exclude_patterns, include_patterns):
    """
    Checks if a given name (file or directory) matches .gitignore patterns.
    
    This function implements .gitignore logic where:
    - If a file/dir matches an exclude pattern, it's ignored UNLESS
    
    Args:
        name (str): The name of the file or directory to check.
        full_path (Path): The full path for matching patterns that start with /
        exclude_patterns (list): List of patterns to exclude.
        include_patterns (list): List of patterns to explicitly include.

    Returns:
        bool: True if the name should be ignored, False otherwise.
    """
    # Normalize the path for matching (convert to forward slashes)
    normalized_path = str(full_path.as_posix())
    
    # Check for directory exclusions ending with /
    is_dir = full_path.is_dir()
    
    # First check exclude patterns
    excluded = False
    for pattern in exclude_patterns:
        match = False
        
        # Handle patterns starting with /
        if pattern.startswith('/'):
            # Match only in the current directory
            if fnmatch.fnmatch(name, pattern[1:]):
                match = True
        else:
            # Can match anywhere in the path
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(os.path.basename(name), pattern):
                match = True
            # For directories, also check if pattern ends with /
            if is_dir and pattern.endswith('/'):
                if fnmatch.fnmatch(name, pattern.rstrip('/')) or fnmatch.fnmatch(os.path.basename(name), pattern.rstrip('/')):
                    match = True
            # Also check full path relative to git root
            if '/' in pattern:
                if fnmatch.fnmatch(normalized_path, f"**/{pattern}") or fnmatch.fnmatch(normalized_path, pattern):
                    match = True
        
        if match:
            excluded = True
            break

    # If excluded, check if there's an include pattern that overrides it
    if excluded:
        for pattern in include_patterns:
            match = False
            
            # Handle patterns starting with /
            if pattern.startswith('/'):
                if fnmatch.fnmatch(name, pattern[1:]):
                    match = True
            else:
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(os.path.basename(name), pattern):
                    match = True
                if is_dir and pattern.endswith('/'):
                    if fnmatch.fnmatch(name, pattern.rstrip('/')) or fnmatch.fnmatch(os.path.basename(name), pattern.rstrip('/')):
                        match = True
                # Also check full path relative to git root
                if '/' in pattern:
                    if fnmatch.fnmatch(normalized_path, f"**/{pattern}") or fnmatch.fnmatch(normalized_path, pattern):
                        match = True
            
            if match:
                return False  # Overridden by include pattern
    
    return excluded

def extract_all_docstrings(filepath, docstring_mode='all'):
    """
    Extracts docstrings from a Python file with their associated entities.
    
    Args:
        filepath (Path): Path to the Python file.
        docstring_mode (str): 'all', 'module_only', or 'none'
        
    Returns:
        list: List of tuples (entity_type, entity_name, docstring_content).
    """
    if filepath.suffix.lower() != '.py':
        return []
    
    if docstring_mode == 'none':
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        
        docstrings = []
        
        # Add module docstring
        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            docstrings.append(('module', '__main__', module_docstring))
        
        # If we only want module docstrings, return now
        if docstring_mode == 'module_only':
            return docstrings
        
        # Walk through all nodes to find classes, functions, and methods
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_docstring = ast.get_docstring(node)
                if func_docstring:
                    docstrings.append(('function', node.name, func_docstring))
            elif isinstance(node, ast.ClassDef):
                class_docstring = ast.get_docstring(node)
                if class_docstring:
                    docstrings.append(('class', node.name, class_docstring))
                
                # Look for methods in the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_docstring = ast.get_docstring(item)
                        if method_docstring:
                            docstrings.append(('method', f"{node.name}.{item.name}", method_docstring))
        
        return docstrings
    except (IOError, OSError):
        return []

def read_file_content(filepath):
    """
    Reads the content of a file and returns it as a string.
    
    Args:
        filepath (Path): Path to the file.
        
    Returns:
        str: Content of the file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except (IOError, OSError):
        return f"Could not read file: {filepath}"

def generate_structure(start_path, prefix="", gitignore_patterns=None, current_depth=0, max_depth=None, base_path=None, detailed_items=None, exclude_dirs=None, display_to_terminal=False, docstring_mode='all'):
    """
    Recursively generates the directory structure string, respecting .gitignore.

    Args:
        start_path (Path): The path object representing the current directory to process.
        prefix (str): The indentation prefix used for the current recursion level.
        gitignore_patterns (list): A list of patterns inherited from parent directories.
        current_depth (int): The current depth in the directory tree (for potential depth limiting).
        max_depth (int, optional): The maximum allowed depth. If specified, recursion stops beyond this level.
        base_path (Path, optional): The base path for relative path calculations.
        detailed_items (set, optional): Set of file/directory names to include detailed content for.
        exclude_dirs (set, optional): Set of directory names to exclude from file listing but show structure.
        display_to_terminal (bool): Whether to print output to terminal as well as file.
        docstring_mode (str): 'all', 'module_only', or 'none'

    Returns:
        list: A list of strings representing the formatted structure for this path and its children.
    """
    output_lines = []
    start_path = Path(start_path)

    if max_depth is not None and current_depth > max_depth:
        return output_lines

    # Set base path if not provided (for relative path calculations)
    if base_path is None:
        base_path = start_path

    # Use patterns from parent directory or initialize for root
    if gitignore_patterns is None:
        gitignore_patterns = []
        # Read .gitignore from the starting path (root) if it exists
        gitignore_patterns.extend(read_gitignore(start_path))
    
    # Parse patterns into include and exclude lists
    include_patterns, exclude_patterns = parse_gitignore_patterns(gitignore_patterns)

    # Get all items (files and directories) in the current directory
    try:
        items = sorted(start_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except (PermissionError, OSError):
        # If directory cannot be read, return empty list or a message
        # print(f"{prefix}[Permission Denied or Error reading {start_path}]")
        return output_lines

    # Separate directories and files, applying ignore rules
    dirs = []
    files = []
    for item in items:
        # Skip .git directory
        if item.name == '.git' and item.is_dir():
            continue
            
        # Calculate relative path from base for matching
        relative_path = item.relative_to(base_path).as_posix()
        
        # Check if item itself is ignored based on current patterns
        if is_ignored(item.name, item, exclude_patterns, include_patterns):
            continue  # Skip this item entirely

        if item.is_dir():
            # Skip if directory is in exclude list
            if exclude_dirs and item.name in exclude_dirs:
                # Still add the directory to the output but without its files
                dirs.append((item, combined_patterns, True))  # True indicates it's excluded
                continue
            
            # Read .gitignore specific to this subdirectory
            subdir_gitignore_patterns = read_gitignore(item)
            # Combine parent patterns with current directory's patterns for children
            combined_patterns = gitignore_patterns + subdir_gitignore_patterns
            dirs.append((item, combined_patterns, False))  # False indicates it's not excluded
        elif item.is_file() and item.suffix.lower() in INCLUDED_EXTENSIONS:
            # Check if the file should be included based on gitignore rules
            # Also check if it's in a directory that should be excluded
            is_in_excluded_dir = any(exclude_dirs and parent.name in exclude_dirs for parent in item.parents)
            if not is_in_excluded_dir:
                files.append(item)

    # Process directories first
    all_items_count = len([d for d in dirs if not d[2]]) + len(files)  # Count only non-excluded items
    dir_idx = 0
    for i, (d, child_gitignore_patterns, is_excluded) in enumerate(dirs):
        # Count only non-excluded directories for determining if this is the last item
        if not is_excluded:
            dir_idx += 1
        is_last_item = (dir_idx == all_items_count)  # Check if this dir is the last item overall
        current_prefix = "└── " if is_last_item else "├── "
        next_prefix = prefix + ("    " if is_last_item else "│   ")

        output_lines.append(f"{prefix}{current_prefix}{d.name}/")
        if display_to_terminal:
            print(f"{prefix}{current_prefix}{d.name}/")
        
        # Add detailed content if requested
        if not is_excluded and detailed_items and d.name in detailed_items:
            output_lines.append(f"{prefix}{'    ' if is_last_item else '│   '}[Contents of {d.name}:]")
            if display_to_terminal:
                print(f"{prefix}{'    ' if is_last_item else '│   '}[Contents of {d.name}:]")
            # List contents of the detailed directory
            try:
                dir_contents = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                for content_item in dir_contents:
                    content_item_is_excluded = exclude_dirs and content_item.name in exclude_dirs
                    if content_item_is_excluded:
                        content_prefix = f"{prefix}{'    ' if is_last_item else '│   '}├── "
                        output_lines.append(f"{content_prefix}{content_item.name}/")
                        if display_to_terminal:
                            print(f"{content_prefix}{content_item.name}/")
                        continue
                        
                    if content_item.is_file():
                        if content_item.suffix.lower() in INCLUDED_EXTENSIONS:
                            content_prefix = f"{prefix}{'    ' if is_last_item else '│   '}├── "
                            output_lines.append(f"{content_prefix}{content_item.name}")
                            if display_to_terminal:
                                print(f"{content_prefix}{content_item.name}")
                            
                            # Add file content if it's in detailed_items or if detailed_items is empty (meaning all)
                            if detailed_items is None or content_item.name in detailed_items or str(content_item) in detailed_items:
                                file_content = read_file_content(content_item)
                                content_lines = file_content.split('\n')
                                for line in content_lines:
                                    detailed_line = f"{prefix}{'        ' if is_last_item else '│       '}{line}"
                                    output_lines.append(detailed_line)
                                    if display_to_terminal:
                                        print(detailed_line)
                    else:
                        content_prefix = f"{prefix}{'    ' if is_last_item else '│   '}├── "
                        output_lines.append(f"{content_prefix}{content_item.name}/")
                        if display_to_terminal:
                            print(f"{content_prefix}{content_item.name}/")
            except (PermissionError, OSError):
                msg = f"{prefix}{'    ' if is_last_item else '│   '}[Permission denied or error reading directory]"
                output_lines.append(msg)
                if display_to_terminal:
                    print(msg)
        
        # Recurse only if not excluded
        if not is_excluded:
            child_lines = generate_structure(
                d, next_prefix, child_gitignore_patterns, current_depth + 1, max_depth, base_path, detailed_items, exclude_dirs, display_to_terminal, docstring_mode
            )
            output_lines.extend(child_lines)
            if display_to_terminal:
                for line in child_lines:
                    print(line)

    # Process files
    for i, f in enumerate(files):
        is_last_item = (i == len(files) - 1)  # Check if this file is the last item in *this* directory
        current_prefix = "└── " if is_last_item else "├── "
        
        # Get file size
        file_size = format_file_size(get_file_size(f))
        
        # Extract docstrings for Python files
        docstrings = extract_all_docstrings(f, docstring_mode)
        if docstrings:
            line = f"{prefix}{current_prefix}{f.name} ({file_size})"
            output_lines.append(line)
            if display_to_terminal:
                print(line)
            # Add docstrings with indentation
            for entity_type, entity_name, docstring in docstrings:
                # Format the docstring content for display
                formatted_docstring = docstring.replace('\n', ' ').strip()
                if len(formatted_docstring) > 100:
                    formatted_docstring = formatted_docstring[:97] + "..."
                doc_line = f"{prefix}{'    ' if is_last_item else '│   '}{entity_type} {entity_name}: {formatted_docstring}"
                output_lines.append(doc_line)
                if display_to_terminal:
                    print(doc_line)
                
            # Add file content if requested
            if detailed_items and (f.name in detailed_items or str(f) in detailed_items):
                file_content = read_file_content(f)
                content_lines = file_content.split('\n')
                for line in content_lines:
                    detailed_line = f"{prefix}{'        ' if is_last_item else '│       '}{line}"
                    output_lines.append(detailed_line)
                    if display_to_terminal:
                        print(detailed_line)
        else:
            line = f"{prefix}{current_prefix}{f.name} ({file_size})"
            output_lines.append(line)
            if display_to_terminal:
                print(line)
            
            # Add file content if requested
            if detailed_items and (f.name in detailed_items or str(f) in detailed_items):
                file_content = read_file_content(f)
                content_lines = file_content.split('\n')
                for line in content_lines:
                    detailed_line = f"{prefix}{'        ' if is_last_item else '│       '}{line}"
                    output_lines.append(detailed_line)
                    if display_to_terminal:
                        print(detailed_line)

    return output_lines

def main():
    """
    Main function to handle command-line arguments and initiate structure generation.
    """
    parser = argparse.ArgumentParser(
        description="Generate a text representation of directory structure for specific file types, respecting .gitignore.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="The path to the directory to analyze. Defaults to current directory."
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        help="Maximum depth to recurse into subdirectories."
    )
    parser.add_argument(
        "--detail", "-dt",
        nargs='*',
        help="Names of files or directories to include detailed content for"
    )
    parser.add_argument(
        "--output", "-o",
        default="tree_output.txt",
        help="Output file name. Defaults to tree_output.txt"
    )
    parser.add_argument(
        "--exclude-dir", "-e",
        nargs='*',
        help="Names of directories to exclude from file listing but show directory structure"
    )
    parser.add_argument(
        "--display", "-ds",
        action="store_true",
        help="Display output to terminal as well as writing to file"
    )
    parser.add_argument(
        "--docstring-mode", "-dm",
        choices=['all', 'module_only', 'none'],
        default='all',
        help="Control which docstrings to include: 'all', 'module_only', or 'none'"
    )

    args = parser.parse_args()
    root_path = Path(args.path)

    if not root_path.exists():
        print(f"Error: Path '{root_path}' does not exist.", file=sys.stderr)
        return

    if not root_path.is_dir():
        print(f"Error: Path '{root_path}' is not a directory.", file=sys.stderr)
        return

    # Prepare detailed items set
    detailed_items = set(args.detail) if args.detail else None
    # Prepare exclude directories set
    exclude_dirs = set(args.exclude_dir) if args.exclude_dir else None

    output_lines = []
    root_line = f"{root_path.name}/"
    output_lines.append(root_line)
    if args.display:
        print(root_line)
    
    structure_lines = generate_structure(
        root_path, 
        max_depth=args.max_depth, 
        detailed_items=detailed_items, 
        exclude_dirs=exclude_dirs,
        display_to_terminal=args.display,
        docstring_mode=args.docstring_mode
    )
    output_lines.extend(structure_lines)
    
    # Write to file only if not displaying to terminal (or always if both are enabled)
    with open(args.output, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    if not args.display:
        print(f"Output written to {args.output}")

if __name__ == "__main__":
    main()