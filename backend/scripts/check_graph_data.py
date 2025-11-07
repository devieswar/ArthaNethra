#!/usr/bin/env python3
"""
Diagnostic script to check what data exists in the knowledge graph.
Usage: python scripts/check_graph_data.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.indexing import IndexingService
from loguru import logger


def main():
    """Check Neo4j graph data"""
    
    print("\n" + "="*60)
    print("🔍 ArthaNethra Knowledge Graph Diagnostic")
    print("="*60 + "\n")
    
    indexing = IndexingService()
    
    if not indexing.neo4j_driver:
        print("❌ Neo4j driver not available!")
        print("   Check config.py settings:")
        print("   - ENABLE_NEO4J = True")
        print("   - NEO4J_URI = 'bolt://localhost:7687'")
        return
    
    print("✅ Neo4j connected\n")
    
    # Count entities by type
    print("📊 Entity Counts by Type:")
    print("-" * 40)
    
    entity_types = ["Location", "Company", "Loan", "Invoice", "Metric", "Person", "Vendor", "Clause"]
    
    with indexing.neo4j_driver.session() as session:
        total_count = 0
        
        for entity_type in entity_types:
            result = session.run(
                "MATCH (e:Entity {type: $type}) RETURN count(e) AS count",
                type=entity_type
            )
            count = result.single()["count"]
            if count > 0:
                print(f"   {entity_type:<20} {count:>6}")
                total_count += count
        
        print("-" * 40)
        print(f"   {'TOTAL':<20} {total_count:>6}\n")
        
        if total_count == 0:
            print("⚠️  No entities found in knowledge graph!")
            print("\n📝 To populate data:")
            print("   1. Upload a document via the UI or API")
            print("   2. Wait for extraction & indexing to complete")
            print("   3. Run this script again to verify\n")
            return
        
        # Show sample entities
        print("\n📋 Sample Entities (first 5):")
        print("-" * 40)
        
        result = session.run(
            """
            MATCH (e:Entity)
            RETURN e.name AS name, e.type AS type, e.graphId AS graphId
            LIMIT 5
            """
        )
        
        for record in result:
            print(f"   • {record['name']} ({record['type']}) [graph: {record['graphId']}]")
        
        # Count relationships
        print("\n🔗 Relationship Counts:")
        print("-" * 40)
        
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
        rel_count = result.single()["count"]
        print(f"   Total relationships: {rel_count}\n")
        
        # List unique graph IDs
        print("\n🗂️  Knowledge Graphs:")
        print("-" * 40)
        
        result = session.run(
            """
            MATCH (e:Entity)
            RETURN DISTINCT e.graphId AS graphId, count(e) AS entity_count
            ORDER BY entity_count DESC
            """
        )
        
        for record in result:
            print(f"   • {record['graphId']}: {record['entity_count']} entities")
        
    print("\n" + "="*60)
    print("✅ Diagnostic complete")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

