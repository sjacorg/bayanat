-- Create ID Number Types table
CREATE TABLE id_number_types (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    title_tr VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- Add index on title columns for better search performance
CREATE INDEX idx_id_number_types_title ON id_number_types(title);
CREATE INDEX idx_id_number_types_title_tr ON id_number_types(title_tr);

-- Insert some default ID number types
INSERT INTO id_number_types (title, title_tr) VALUES 
    ('National ID', ''),
    ('Passport', ''),
    ('Driver License', ''),
    ('Social Security Number', ''),
    ('Tax ID', ''),
    ('Military ID', ''),
    ('Birth Certificate', ''),
    ('Student ID', ''); 