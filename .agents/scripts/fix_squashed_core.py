import re

path = r"C:\Users\ARMANDO\travelhub_project\core\migrations\0001_squashed_0057_apisecret.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 1. Add function imports at the top (after existing imports, before class)
# Read the functions from the old migration files
func_0021 = r"C:\Users\ARMANDO\travelhub_project\core\migrations\0021_migrate_agencia_data.py"
func_0027 = r"C:\Users\ARMANDO\travelhub_project\core\migrations\0027_seed_feature_flags.py"
func_0037 = (
    r"C:\Users\ARMANDO\travelhub_project\core\migrations\0037_rename_remaining_core_tables.py"
)

import ast


def get_function_source(filepath, func_names):
    """Extract function source code from a migration file."""
    with open(filepath, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in func_names:
                start_line = node.lineno - 1
                end_line = node.end_lineno
                lines = source.splitlines()[start_line:end_line]
                result.append("\n".join(lines))
    return result


# Get function sources
funcs_0021 = get_function_source(
    func_0021, {"migrate_agencia_data", "reverse_migrate_agencia_data"}
)
funcs_0027 = get_function_source(func_0027, {"seed_feature_flags", "remove_feature_flags"})
funcs_0037 = get_function_source(
    func_0037,
    {
        "_get_existing_tables",
        "_index_exists",
        "_constraint_exists",
        "_rename_index",
        "_rename_constraint",
        "_replace_core_prefix",
        "_rename_tables",
        "_rename_indexes_and_constraints",
        "_rename_fk_references_on_other_tables",
        "_reverse_rename_tables",
        "_reverse_rename_indexes_and_constraints",
    },
)

# Build the functions block to insert
functions_block = (
    """

# === Manually copied from 0021_migrate_agencia_data ===
"""
    + "\n\n".join(funcs_0021)
    + """


# === Manually copied from 0027_seed_feature_flags ===
"""
    + "\n\n".join(funcs_0027)
    + """


# === Manually copied from 0037_rename_remaining_core_tables ===
"""
    + "\n\n".join(funcs_0037)
    + """

"""
)

# Insert functions before "class Migration("
content = content.replace(
    "\nclass Migration(migrations.Migration):",
    functions_block + "\nclass Migration(migrations.Migration):",
)

# 2. Remove the comment about manual copying
content = re.sub(
    r"\n# Functions from the following migrations need manual copying\..*?# core\.migrations\.0037_rename_remaining_core_tables",
    "",
    content,
    flags=re.DOTALL,
)

# 3. Fix the RunPython references (replace dotted paths with local names)
replacements = [
    ("core.migrations.0021_migrate_agencia_data.migrate_agencia_data", "migrate_agencia_data"),
    (
        "core.migrations.0021_migrate_agencia_data.reverse_migrate_agencia_data",
        "reverse_migrate_agencia_data",
    ),
    ("core.migrations.0027_seed_feature_flags.seed_feature_flags", "seed_feature_flags"),
    ("core.migrations.0027_seed_feature_flags.remove_feature_flags", "remove_feature_flags"),
    ("core.migrations.0037_rename_remaining_core_tables._rename_tables", "_rename_tables"),
    (
        "core.migrations.0037_rename_remaining_core_tables._reverse_rename_tables",
        "_reverse_rename_tables",
    ),
    (
        "core.migrations.0037_rename_remaining_core_tables._rename_indexes_and_constraints",
        "_rename_indexes_and_constraints",
    ),
    (
        "core.migrations.0037_rename_remaining_core_tables._reverse_rename_indexes_and_constraints",
        "_reverse_rename_indexes_and_constraints",
    ),
]
for old, new in replacements:
    content = content.replace(old, new)

# 4. Remove contabilidad and finance from dependencies
# Find the dependencies list and filter out contabilidad and finance
# The dependencies list looks like:
#     dependencies = [
#         ('automation', '0005_...'),
#         ...
#         ('contabilidad', '0004_...'),
#         ...
#         ('finance', '0003_...'),
#         ...
#     ]
# We need to remove entries where app is 'contabilidad' or 'finance'

# Simple approach: regex to remove those lines
content = re.sub(
    r"\s+\('contabilidad', '[^']+'\),\n",
    "\n",
    content,
)
content = re.sub(
    r"\s+\('finance', '[^']+'\),\n",
    "\n",
    content,
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done - fixed squashed core migration")
print(f"File size: {len(content)} bytes")
