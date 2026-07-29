-- Supabase Migration: Add Worker Role and Fields to Users Table
-- Run this script in your Supabase SQL Editor

-- 1. Drop the existing check constraint on the role column
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;

-- 2. Add the new check constraint supporting 'worker'
ALTER TABLE public.users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'user', 'worker'));

-- 3. Add worker-specific columns
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS team_name TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS designation TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS worker_status TEXT DEFAULT 'Available'::text;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now());

-- Optional: Create a trigger to automatically update the updated_at column
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_modtime ON public.users;
CREATE TRIGGER update_users_modtime
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();
