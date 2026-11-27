ALTER TABLE ticket_records
    ADD COLUMN IF NOT EXISTS classification_summary TEXT;
