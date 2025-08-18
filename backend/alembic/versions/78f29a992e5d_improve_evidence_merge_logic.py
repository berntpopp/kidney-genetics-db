"""improve_evidence_merge_logic

Revision ID: 78f29a992e5d
Revises: 1913be50fe24
Create Date: 2025-08-18 23:09:30.859283

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '78f29a992e5d'
down_revision: str | Sequence[str] | None = '1913be50fe24'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Improve evidence deduplication by intelligently merging JSONB data
    instead of simply keeping the newest record.

    This migration:
    1. Creates a function to merge evidence JSONB data intelligently
    2. Identifies and merges existing duplicate evidence records
    3. Adds merge history tracking to preserve data lineage
    """

    # Create the intelligent merge function
    op.execute("""
        CREATE OR REPLACE FUNCTION merge_evidence_jsonb(existing jsonb, new_data jsonb)
        RETURNS jsonb AS $$
        DECLARE
            result jsonb;
            key text;
            existing_value jsonb;
            new_value jsonb;
        BEGIN
            -- Start with existing data as base
            result := existing;

            -- Iterate through new_data keys and merge intelligently
            FOR key IN SELECT jsonb_object_keys(new_data)
            LOOP
                existing_value := existing->key;
                new_value := new_data->key;

                -- Merge logic based on value types
                IF existing_value IS NULL THEN
                    -- New key, add it
                    result := jsonb_set(result, ARRAY[key], new_value);

                ELSIF jsonb_typeof(existing_value) = 'array' AND jsonb_typeof(new_value) = 'array' THEN
                    -- Merge arrays by combining unique elements
                    result := jsonb_set(result, ARRAY[key],
                        (SELECT jsonb_agg(DISTINCT value)
                         FROM (
                             SELECT jsonb_array_elements(existing_value) AS value
                             UNION
                             SELECT jsonb_array_elements(new_value) AS value
                         ) AS combined)
                    );

                ELSIF jsonb_typeof(existing_value) = 'object' AND jsonb_typeof(new_value) = 'object' THEN
                    -- Recursively merge objects
                    result := jsonb_set(result, ARRAY[key], existing_value || new_value);

                ELSIF key = 'evidence_score' OR key = 'confidence_score' THEN
                    -- For scores, keep the higher value
                    IF (new_value::text)::numeric > (existing_value::text)::numeric THEN
                        result := jsonb_set(result, ARRAY[key], new_value);
                    END IF;

                ELSIF key = 'date' OR key = 'updated_at' OR key = 'last_updated' THEN
                    -- For dates, keep the more recent
                    IF new_value::text > existing_value::text THEN
                        result := jsonb_set(result, ARRAY[key], new_value);
                    END IF;

                ELSIF new_value IS NOT NULL AND (existing_value IS NULL OR existing_value = 'null'::jsonb) THEN
                    -- Replace null with non-null value
                    result := jsonb_set(result, ARRAY[key], new_value);

                END IF;
            END LOOP;

            -- Add merge history
            result := jsonb_set(result,
                ARRAY['merge_history'],
                COALESCE(result->'merge_history', '[]'::jsonb) ||
                    jsonb_build_array(jsonb_build_object(
                        'merged_at', NOW(),
                        'source_data_keys', array_to_json(ARRAY(SELECT jsonb_object_keys(new_data)))
                    ))
            );

            RETURN result;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Find and merge existing duplicates intelligently
    op.execute("""
        -- Create temporary table to track merge operations
        CREATE TEMP TABLE evidence_merge_plan AS
        WITH duplicate_groups AS (
            -- Find all duplicate evidence (same gene_id and source_name)
            SELECT
                gene_id,
                source_name,
                COUNT(*) as duplicate_count,
                MIN(id) as keep_id,
                array_agg(id ORDER BY evidence_date DESC, updated_at DESC, id DESC) as all_ids
            FROM gene_evidence
            GROUP BY gene_id, source_name
            HAVING COUNT(*) > 1
        )
        SELECT * FROM duplicate_groups;

        -- Merge evidence data for each duplicate group
        UPDATE gene_evidence ge
        SET evidence_data = merged.merged_data,
            source_detail = merged.combined_detail,
            updated_at = NOW()
        FROM (
            SELECT
                emp.keep_id,
                -- Combine all source details with semicolon separator
                string_agg(DISTINCT ge2.source_detail, '; ' ORDER BY ge2.source_detail) as combined_detail,
                -- Merge all evidence data using our intelligent function
                CASE
                    WHEN emp.duplicate_count = 1 THEN
                        (SELECT evidence_data FROM gene_evidence WHERE id = emp.keep_id)
                    ELSE
                        -- Apply merge function iteratively
                        merge_evidence_jsonb(
                            merge_evidence_jsonb(
                                COALESCE((SELECT evidence_data FROM gene_evidence WHERE id = emp.keep_id), '{}'::jsonb),
                                COALESCE((SELECT jsonb_agg(evidence_data) FROM gene_evidence WHERE id = ANY(emp.all_ids) AND id != emp.keep_id), '{}'::jsonb)
                            ),
                            jsonb_build_object(
                                'duplicate_ids_merged', emp.all_ids,
                                'merge_date', NOW()
                            )
                        )
                END as merged_data
            FROM evidence_merge_plan emp
            JOIN gene_evidence ge2 ON ge2.id = ANY(emp.all_ids)
            GROUP BY emp.keep_id, emp.all_ids, emp.duplicate_count
        ) AS merged
        WHERE ge.id = merged.keep_id;

        -- Delete the duplicate records (keeping only the merged one)
        DELETE FROM gene_evidence
        WHERE id IN (
            SELECT unnest(all_ids[2:])  -- All IDs except the first (keep_id)
            FROM evidence_merge_plan
        );

        -- Log merge statistics
        DO $$
        DECLARE
            merge_count INTEGER;
            records_removed INTEGER;
        BEGIN
            SELECT COUNT(*) INTO merge_count FROM evidence_merge_plan;
            SELECT SUM(duplicate_count - 1) INTO records_removed FROM evidence_merge_plan;

            IF merge_count > 0 THEN
                RAISE NOTICE '✅ Merged % duplicate groups, removed % redundant records', merge_count, records_removed;
            ELSE
                RAISE NOTICE '✅ No duplicate evidence records found to merge';
            END IF;
        END $$;

        -- Drop the temporary table
        DROP TABLE IF EXISTS evidence_merge_plan;
    """)

    # Add an index on merge_history for faster queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_evidence_merge_history
        ON gene_evidence ((evidence_data->'merge_history'))
        WHERE evidence_data ? 'merge_history';
    """)

    print("✅ Improved evidence deduplication with intelligent JSONB merging")


def downgrade() -> None:
    """
    Remove the intelligent merge function and index.
    Note: This won't restore the original duplicate records.
    """

    # Drop the merge history index
    op.execute("""
        DROP INDEX IF EXISTS idx_evidence_merge_history;
    """)

    # Drop the merge function
    op.execute("""
        DROP FUNCTION IF EXISTS merge_evidence_jsonb(jsonb, jsonb);
    """)

    print("✅ Removed intelligent evidence merge function")
