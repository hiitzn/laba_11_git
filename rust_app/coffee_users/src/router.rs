use axum::{routing::{get, post}, Router};
use std::sync::Arc;

use crate::{
    db::Db,
    handlers::{add_visitor, list_visitors},
};

pub fn build_router(db: Arc<Db>) -> Router {
    Router::new()
        .route("/visitors", post(add_visitor))
        .route("/visitors", get(list_visitors))
        .with_state(db)
}