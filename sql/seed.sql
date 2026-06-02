-- Clear out any existing data in the table (optional but helpful for clean seeds)
TRUNCATE TABLE books RESTART IDENTITY;

-- Insert sample data into the books table
INSERT INTO books (title, author, year, rating) VALUES
('The Hobbit', 'J.R.R. Tolkien', 1937, 4.8),
('To Kill a Mockingbird', 'Harper Lee', 1960, 4.9),
('1984', 'George Orwell', 1949, 4.7),
('The Great Gatsby', 'F. Scott Fitzgerald', 1925, 4.2),
(' Pride and Prejudice', 'Jane Austen', 1813, 4.6);
