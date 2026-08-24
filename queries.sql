-- ===========================================================================
-- DATABASE CONFIGURATION QUERIES
-- Modify these queries directly to target different exams, packages, or chapters.
-- Do not modify the headers -- [PENDING_QUERY] and -- [STATUS_QUERY].
-- ===========================================================================

-- [PENDING_QUERY]
-- Must return 'id' (MySQL ID) and 'content' (PDF filename) columns
-- Keep 'htmltopdfstatus = 0' so it only processes pending documents.
SELECT id, content FROM tbl_studymaterial_lang_map
WHERE content_id IN (
    SELECT content_id FROM tbl_studymaterial_mapping_with_esc
    WHERE esc_id IN (
        SELECT id FROM tbl_studymaterial_esc_s
        WHERE exam_id = 39 AND package_id = 841 AND status = 1
    )
)
AND type_order = 2 AND status = 1 AND htmltopdfstatus = 0
ORDER BY id ASC;

-- [STATUS_QUERY]
-- Calculates total, pending, completed, and failed status counts
SELECT SUM(htmltopdfstatus=0) AS pending, SUM(htmltopdfstatus=1) AS done,
       SUM(htmltopdfstatus=2) AS failed, COUNT(*) AS total
FROM tbl_studymaterial_lang_map
WHERE content_id IN (
    SELECT content_id FROM tbl_studymaterial_mapping_with_esc
    WHERE esc_id IN (
        SELECT id FROM tbl_studymaterial_esc_s
        WHERE exam_id = 39 AND package_id = 841 AND status = 1
    )
) AND type_order = 2 AND status = 1;
