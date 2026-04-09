use rusqlite::{Connection, Result as SqlResult};
use std::sync::Mutex;

use crate::models::{NewVisitor, Visitor};

/// Потокобезопасная обёртка над синхронным SQLite-соединением.
pub struct Db(Mutex<Connection>);

impl Db {
    /// Открыть файловую базу данных (создаёт файл если не существует).
    pub fn open(path: &str) -> SqlResult<Self> {
        let conn = Connection::open(path)?;
        Self::migrate(&conn)?;
        Ok(Self(Mutex::new(conn)))
    }

    /// Открыть базу данных в памяти — удобно для тестов.
    pub fn open_in_memory() -> SqlResult<Self> {
        let conn = Connection::open_in_memory()?;
        Self::migrate(&conn)?;
        Ok(Self(Mutex::new(conn)))
    }

    /// Создать схему при первом запуске.
    fn migrate(conn: &Connection) -> SqlResult<()> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS visitors (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT    NOT NULL,
                drink TEXT    NOT NULL
            );",
        )
    }

    pub fn insert(&self, v: &NewVisitor) -> SqlResult<Visitor> {
        let conn = self.0.lock().unwrap();
        conn.execute(
            "INSERT INTO visitors (name, drink) VALUES (?1, ?2)",
            (&v.name, &v.drink),
        )?;
        Ok(Visitor {
            id: conn.last_insert_rowid(),
            name: v.name.clone(),
            drink: v.drink.clone(),
        })
    }

    pub fn list(&self) -> SqlResult<Vec<Visitor>> {
        let conn = self.0.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, name, drink FROM visitors ORDER BY id")?;
        let rows = stmt.query_map([], |row| {
            Ok(Visitor {
                id: row.get(0)?,
                name: row.get(1)?,
                drink: row.get(2)?,
            })
        })?;
        rows.collect()
    }
}

// ── Юнит-тесты ───────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn db() -> Db {
        Db::open_in_memory().unwrap()
    }

    fn visitor(name: &str, drink: &str) -> NewVisitor {
        NewVisitor { name: name.into(), drink: drink.into() }
    }

    #[test]
    fn insert_returns_correct_visitor() {
        let v = db().insert(&visitor("Анна", "Латте")).unwrap();
        assert_eq!(v.id, 1);
        assert_eq!(v.name, "Анна");
        assert_eq!(v.drink, "Латте");
    }

    #[test]
    fn list_empty_db_returns_empty_vec() {
        assert!(db().list().unwrap().is_empty());
    }

    #[test]
    fn list_preserves_insertion_order() {
        let db = db();
        db.insert(&visitor("Bob", "Espresso")).unwrap();
        db.insert(&visitor("Alice", "Cappuccino")).unwrap();
        let list = db.list().unwrap();
        assert_eq!(list[0].name, "Bob");
        assert_eq!(list[1].name, "Alice");
    }

    #[test]
    fn ids_are_sequential() {
        let db = db();
        for name in ["A", "B", "C"] {
            db.insert(&visitor(name, "Tea")).unwrap();
        }
        let ids: Vec<i64> = db.list().unwrap().iter().map(|v| v.id).collect();
        assert_eq!(ids, vec![1, 2, 3]);
    }
}