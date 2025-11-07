#!/usr/bin/env python3
"""
Verify that concept_service.py has been updated correctly with the new data source
and the clear_db functionality works
"""
import sys
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def verify_concept_service():
    """Verify changes to concept_service.py"""
    print("=" * 60)
    print("Verifying concept_service.py changes")
    print("=" * 60)
    
    from data_management import concept_service
    
    # 1. Check for clear_concept_tables_for_testing function
    print("\n1. Checking for clear_concept_tables_for_testing function...")
    if hasattr(concept_service, 'clear_concept_tables_for_testing'):
        print("   ✓ Function exists")
        sig = inspect.signature(concept_service.clear_concept_tables_for_testing)
        print(f"   Signature: {sig}")
    else:
        print("   ✗ Function not found")
        return False
    
    # 2. Check collect_concepts_task signature
    print("\n2. Checking collect_concepts_task function...")
    sig = inspect.signature(concept_service.collect_concepts_task)
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    if 'clear_db' in params:
        print("   ✓ Has clear_db parameter")
        default = sig.parameters['clear_db'].default
        print(f"   Default value: {default}")
    else:
        print("   ✗ Missing clear_db parameter")
        return False
    
    # 3. Check create_concept_collection_task signature
    print("\n3. Checking create_concept_collection_task function...")
    sig = inspect.signature(concept_service.create_concept_collection_task)
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    if 'clear_db' in params:
        print("   ✓ Has clear_db parameter")
        default = sig.parameters['clear_db'].default
        print(f"   Default value: {default}")
    else:
        print("   ✗ Missing clear_db parameter")
        return False
    
    return True


def verify_api():
    """Verify changes to api.py"""
    print("\n" + "=" * 60)
    print("Verifying api.py changes")
    print("=" * 60)
    
    from api import collect_concepts
    
    print("\n1. Checking collect_concepts function...")
    sig = inspect.signature(collect_concepts)
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    if 'clear_db' in params:
        print("   ✓ Has clear_db parameter")
        default = sig.parameters['clear_db'].default
        print(f"   Default value: {default}")
    else:
        print("   ✗ Missing clear_db parameter")
        return False
    
    return True


def verify_database_ops():
    """Verify database operations work correctly"""
    print("\n" + "=" * 60)
    print("Verifying database operations")
    print("=" * 60)
    
    from models import engine, create_db_and_tables, ConceptInfo, ConceptStock
    from sqlmodel import Session, select
    from data_management.concept_service import clear_concept_tables_for_testing
    
    print("\n1. Initializing database...")
    try:
        create_db_and_tables()
        print("   ✓ Database initialized")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    print("\n2. Testing clear_concept_tables_for_testing...")
    try:
        # First add some test data
        with Session(engine) as session:
            test_concept = ConceptInfo(code="test_001", name="Test Concept", stock_count=10)
            session.add(test_concept)
            session.commit()
        
        # Check it exists
        with Session(engine) as session:
            concepts_before = len(session.exec(select(ConceptInfo)).all())
            print(f"   Before clear: {concepts_before} concepts")
            if concepts_before == 0:
                print("   ⚠ No test data found, adding...")
                test_concept = ConceptInfo(code="test_001", name="Test Concept", stock_count=10)
                session.add(test_concept)
                session.commit()
        
        # Clear
        clear_concept_tables_for_testing()
        print("   ✓ Clear completed")
        
        # Verify it's gone
        with Session(engine) as session:
            concepts_after = len(session.exec(select(ConceptInfo)).all())
            stocks_after = len(session.exec(select(ConceptStock)).all())
            print(f"   After clear: {concepts_after} concepts, {stocks_after} stocks")
            if concepts_after == 0 and stocks_after == 0:
                print("   ✓ Tables successfully cleared")
            else:
                print("   ✗ Tables not fully cleared")
                return False
    
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    print("\n" + "=" * 60)
    print("Concept Data Source Integration Verification")
    print("=" * 60)
    
    checks = [
        ("concept_service.py changes", verify_concept_service),
        ("api.py changes", verify_api),
        ("database operations", verify_database_ops),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"\n✗ Error in {check_name}: {e}")
            import traceback
            traceback.print_exc()
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    for check_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {check_name}")
    
    all_passed = all(results.values())
    print("\n" + ("✓ All verifications PASSED!" if all_passed else "✗ Some verifications FAILED"))
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
