-- Drop the table if it already exists to allow for clean resets
DROP TABLE IF EXISTS books;

-- Create the books table
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL,
    rating NUMERIC(3, 1) CHECK (rating >= 0.0 AND rating <= 5.0)
);
