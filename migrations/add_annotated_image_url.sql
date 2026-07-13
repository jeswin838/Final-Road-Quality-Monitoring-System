-- ================================================================
-- Migration: Add annotated_image_url + review_required to potholes
-- Run this once against your Supabase database.
-- ================================================================

-- 1. Add annotated_image_url (stores the YOLO-annotated version)
ALTER TABLE public.potholes
    ADD COLUMN IF NOT EXISTS annotated_image_url TEXT;

-- 2. Add review_required flag used by the admin pending-reports page
ALTER TABLE public.potholes
    ADD COLUMN IF NOT EXISTS review_required BOOLEAN DEFAULT FALSE;

-- 3. Backfill: mark existing approved rows as not requiring review
UPDATE public.potholes
    SET review_required = FALSE
    WHERE review_required IS NULL;

-- Verify the schema looks correct after migration:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'potholes'
-- ORDER BY ordinal_position;
