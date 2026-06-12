# BROKEN: user input is interpolated directly into the SQL string.
import sqlite3

_conn = sqlite3.connect(":memory:", check_same_thread=False)


def seed_database() -> None:
    _conn.executescript(
        """
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS users;
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT);
        INSERT INTO products (name, price) VALUES
            ('Gaming Laptop', 1299.0),
            ('Laptop Stand', 49.0),
            ('O''Briens Hot Sauce', 9.5),
            ('Mechanical Keyboard', 129.0);
        INSERT INTO users (username, password) VALUES ('admin', 'TopSecretHunter2');
        """
    )


def search_products(name: str) -> list[dict]:
    cursor = _conn.execute(
        f"SELECT id, name, price FROM products WHERE name LIKE '%{name}%'"
    )
    return [{"id": r[0], "name": r[1], "price": r[2]} for r in cursor.fetchall()]
