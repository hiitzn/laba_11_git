use axum::{http::StatusCode, response::{IntoResponse, Response}};

/// Централизованный тип ошибок приложения.
pub enum AppError {
    Db(rusqlite::Error),
    Validation(&'static str),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        match self {
            AppError::Db(e) => {
                eprintln!("[ERROR] database: {e}");
                StatusCode::INTERNAL_SERVER_ERROR.into_response()
            }
            AppError::Validation(msg) => {
                (StatusCode::UNPROCESSABLE_ENTITY, msg).into_response()
            }
        }
    }
}

impl From<rusqlite::Error> for AppError {
    fn from(e: rusqlite::Error) -> Self {
        AppError::Db(e)
    }
}