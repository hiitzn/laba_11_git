use serde::{Deserialize, Serialize};

/// Полная запись посетителя — возвращается клиенту.
#[derive(Debug, Serialize, Deserialize)]
pub struct Visitor {
    pub id: i64,
    pub name: String,
    pub drink: String,
}

/// Входящий JSON при POST /visitors.
#[derive(Debug, Deserialize)]
pub struct NewVisitor {
    pub name: String,
    pub drink: String,
}