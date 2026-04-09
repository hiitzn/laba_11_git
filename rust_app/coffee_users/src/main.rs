use std::sync::Arc;
use coffee_shop::{db::Db, router::build_router};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "coffee_shop.db".to_string());

    let db = Arc::new(Db::open(&db_path).expect("Failed to open SQLite database"));
    let app = build_router(db);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("☕  Coffee Shop API listening on http://0.0.0.0:3000");
    println!("🗄️  Database: {db_path}");
    axum::serve(listener, app).await.unwrap();
}