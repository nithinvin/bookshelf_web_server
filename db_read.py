import psycopg2

# Connect to the database
conn = psycopg2.connect(
    host="localhost",
    database="bk_db",
    user="bk_user",
    password="bookshelf"
)

print(type(conn))
cur = conn.cursor()


# Retrieve all records
cur.execute("SELECT id, title, author, year, rating FROM books;")
print(type(cur))
print(cur.rowcount)
rows = cur.fetchall()

# Print records
print(f"{'ID':<5} {'Title':<30} {'Author':<25} {'Year':<6} {'Rating'}")
print("-" * 75)

for row in rows:
    id, title, author, year, rating = row
    print(f"{id:<5} {title:<30} {author:<25} {year:<6} {rating}")

cur.close()
conn.close()
