-- Single SQL script to verify Actor.id_number migration data integrity
-- Run this script AFTER the migration to ensure no data loss

-- Test 1: Verify all actors have valid JSONB arrays for id_number
SELECT 
    'TEST 1: JSONB Array Validation' as test_name,
    COUNT(*) as total_actors,
    COUNT(CASE WHEN jsonb_typeof(id_number) = 'array' THEN 1 END) as valid_arrays,
    COUNT(CASE WHEN jsonb_typeof(id_number) != 'array' THEN 1 END) as invalid_arrays
FROM actor;

-- Test 2: Verify no actors have null id_number (should all be arrays, empty or populated)
SELECT 
    'TEST 2: No NULL id_number values' as test_name,
    COUNT(*) as total_actors,
    COUNT(CASE WHEN id_number IS NULL THEN 1 END) as null_count,
    COUNT(CASE WHEN id_number IS NOT NULL THEN 1 END) as non_null_count
FROM actor;

-- Test 3: Verify array structure - all elements have required fields
SELECT 
    'TEST 3: Array Element Structure' as test_name,
    COUNT(*) as actors_with_id_numbers,
    COUNT(CASE WHEN (
        SELECT bool_and(
            (elem->>'type') IS NOT NULL AND 
            (elem->>'number') IS NOT NULL AND
            jsonb_typeof(elem->'type') = 'string' AND
            jsonb_typeof(elem->'number') = 'string'
        ) 
        FROM jsonb_array_elements(id_number) AS elem
    ) THEN 1 END) as valid_structure_count
FROM actor 
WHERE jsonb_array_length(id_number) > 0;

-- Test 4: Verify backup table exists and check data consistency
SELECT 
    'TEST 4: Backup Table Check' as test_name,
    COUNT(*) as backup_records
FROM actor_id_number_backup;

-- Test 5: Data consistency check - compare backup with migrated data
-- For actors that had non-empty strings, verify they now have that string as first array element's number
SELECT 
    'TEST 5: Data Consistency Check' as test_name,
    COUNT(*) as total_backup_records,
    COUNT(CASE 
        WHEN a.id_number->0->>'number' = b.id_number 
        THEN 1 
    END) as matching_records,
    COUNT(CASE 
        WHEN a.id_number->0->>'number' != b.id_number 
        THEN 1 
    END) as mismatched_records
FROM actor_id_number_backup b
JOIN actor a ON a.id = b.id
WHERE b.id_number IS NOT NULL AND b.id_number != '';

-- Test 6: Verify all migrated string data uses default type "1"
SELECT 
    'TEST 6: Default Type Assignment' as test_name,
    COUNT(*) as actors_with_id_numbers,
    COUNT(CASE 
        WHEN (
            SELECT bool_and(elem->>'type' = '1') 
            FROM jsonb_array_elements(id_number) AS elem
        ) THEN 1 
    END) as using_default_type
FROM actor 
WHERE jsonb_array_length(id_number) > 0;

-- Test 7: Final summary - potential data loss indicators
SELECT 
    'TEST 7: FINAL SUMMARY' as test_name,
    (SELECT COUNT(*) FROM actor_id_number_backup) as original_non_empty_records,
    (SELECT COUNT(*) FROM actor WHERE jsonb_array_length(id_number) > 0) as migrated_non_empty_records,
    (SELECT COUNT(*) FROM actor WHERE id_number = '[]'::jsonb) as empty_array_records,
    (SELECT COUNT(*) FROM actor) as total_actor_records;

-- Expected Results for Successful Migration:
-- TEST 1: invalid_arrays should be 0, all should be valid_arrays
-- TEST 2: null_count should be 0, all should be non_null_count  
-- TEST 3: All actors with id_numbers should have valid_structure_count
-- TEST 4: Should show backup records exist
-- TEST 5: matching_records should equal total_backup_records, mismatched_records should be 0
-- TEST 6: All actors with id_numbers should be using_default_type (unless manually modified)
-- TEST 7: migrated_non_empty_records should equal original_non_empty_records (no data loss) 