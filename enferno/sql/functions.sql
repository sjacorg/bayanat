-- SQL functions required before db.create_all().
-- Loaded automatically by enferno.utils.db_utils.ensure_sql_functions().
-- Add new functions here as needed.

-- Arabic text normalization for search indexing.
-- Normalizes: alef variants, taa marbuta, alef maksura, eastern numerals.
-- Strips: diacritics/tashkeel, tatweel/kashida.
-- Non-Arabic text passes through unchanged.
CREATE OR REPLACE FUNCTION normalize_arabic_text(input text) RETURNS text AS $$
BEGIN
    IF input IS NULL THEN RETURN NULL; END IF;
    RETURN translate(
        input,
        E'\u0623\u0625\u0622\u0671\u0649\u0629\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0640',
        E'\u0627\u0627\u0627\u0627\u064A\u06470123456789'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;
