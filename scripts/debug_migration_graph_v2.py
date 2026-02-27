import os
import django
from django.db.migrations.loader import MigrationLoader
from django.db import connections

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def debug_graph():
    connection = connections['default']
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    
    print("Migration Graph Nodes:")
    for node in loader.graph.nodes:
        print(f"  {node}")
    
    print("\nDependency Issues:")
    try:
        plan = loader.graph.leaf_nodes()
        print(f"Leaf nodes: {plan}")
    except Exception as e:
        print(f"Error calculating leaf nodes: {e}")

if __name__ == "__main__":
    debug_graph()
