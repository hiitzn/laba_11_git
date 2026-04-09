use axum::{extract::State, http::StatusCode, response::Json};
use std::sync::Arc;

use crate::{
    db::Db,
    error::AppError,
    models::{NewVisitor, Visitor},
};

/// POST /visitors — добавить посетителя.
pub async fn add_visitor(
    State(db): State<Arc<Db>>,
    Json(payload): Json<NewVisitor>,
) -> Result<(StatusCode, Json<Visitor>), AppError> {
    if payload.name.trim().is_empty() {
        return Err(AppError::Validation("name не может быть пустым"));
    }
    if payload.drink.trim().is_empty() {
        return Err(AppError::Validation("drink не может быть пустым"));
    }
    let visitor = db.insert(&payload)?;
    Ok((StatusCode::CREATED, Json(visitor)))
}

/// GET /visitors — список всех посетителей.
pub async fn list_visitors(
    State(db): State<Arc<Db>>,
) -> Result<Json<Vec<Visitor>>, AppError> {
    Ok(Json(db.list()?))
}