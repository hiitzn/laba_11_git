//! Функциональные (end-to-end) тесты REST API.
//!
//! Каждый тест поднимает изолированный роутер с in-memory БД
//! и отправляет через него реальные HTTP-запросы.

use axum::{
    body::Body,
    http::{self, Request, StatusCode},
};
use coffee_shop::{db::Db, models::Visitor, router::build_router};
use http_body_util::BodyExt;
use std::sync::Arc;
use tower::ServiceExt;

// ── Вспомогательные функции ───────────────────────────────────────────────────

fn app() -> axum::Router {
    build_router(Arc::new(Db::open_in_memory().unwrap()))
}

async fn parse_json<T: serde::de::DeserializeOwned>(body: Body) -> T {
    let bytes = body.collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).expect("response body is valid JSON")
}

fn post_req(json: &str) -> Request<Body> {
    Request::builder()
        .method(http::Method::POST)
        .uri("/visitors")
        .header(http::header::CONTENT_TYPE, "application/json")
        .body(Body::from(json.to_owned()))
        .unwrap()
}

fn get_req() -> Request<Body> {
    Request::builder()
        .method(http::Method::GET)
        .uri("/visitors")
        .body(Body::empty())
        .unwrap()
}

// ── POST /visitors ────────────────────────────────────────────────────────────

#[tokio::test]
async fn post_returns_201_and_visitor_body() {
    let res = app()
        .oneshot(post_req(r#"{"name":"Анна","drink":"Латте"}"#))
        .await
        .unwrap();

    assert_eq!(res.status(), StatusCode::CREATED);
    let v: Visitor = parse_json(res.into_body()).await;
    assert_eq!(v.id, 1);
    assert_eq!(v.name, "Анна");
    assert_eq!(v.drink, "Латте");
}

#[tokio::test]
async fn post_response_contains_all_required_fields() {
    let res = app()
        .oneshot(post_req(r#"{"name":"Лена","drink":"Моккo"}"#))
        .await
        .unwrap();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let obj: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert!(obj.get("id").is_some(),    "отсутствует поле id");
    assert!(obj.get("name").is_some(),  "отсутствует поле name");
    assert!(obj.get("drink").is_some(), "отсутствует поле drink");
}

#[tokio::test]
async fn post_empty_name_returns_422() {
    let res = app()
        .oneshot(post_req(r#"{"name":"","drink":"Латте"}"#))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn post_whitespace_name_returns_422() {
    let res = app()
        .oneshot(post_req(r#"{"name":"   ","drink":"Латте"}"#))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn post_empty_drink_returns_422() {
    let res = app()
        .oneshot(post_req(r#"{"name":"Иван","drink":""}"#))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn post_missing_drink_field_returns_422() {
    let res = app()
        .oneshot(post_req(r#"{"name":"Иван"}"#))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn post_missing_name_field_returns_422() {
    let res = app()
        .oneshot(post_req(r#"{"drink":"Латте"}"#))
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn post_invalid_json_returns_4xx() {
    let res = app().oneshot(post_req("not-json")).await.unwrap();
    assert!(
        res.status().is_client_error(),
        "ожидался 4xx, получен {}",
        res.status()
    );
}

#[tokio::test]
async fn post_empty_body_returns_4xx() {
    let res = app()
        .oneshot(
            Request::builder()
                .method(http::Method::POST)
                .uri("/visitors")
                .header(http::header::CONTENT_TYPE, "application/json")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert!(res.status().is_client_error());
}

// ── GET /visitors ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn get_empty_db_returns_empty_array() {
    let res = app().oneshot(get_req()).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let list: Vec<Visitor> = parse_json(res.into_body()).await;
    assert!(list.is_empty());
}

#[tokio::test]
async fn get_returns_all_visitors_in_insertion_order() {
    use coffee_shop::models::NewVisitor;

    let db = Arc::new(Db::open_in_memory().unwrap());
    db.insert(&NewVisitor { name: "Анна".into(), drink: "Латте".into() }).unwrap();
    db.insert(&NewVisitor { name: "Пётр".into(), drink: "Эспрессо".into() }).unwrap();

    let res = build_router(db).oneshot(get_req()).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);

    let list: Vec<Visitor> = parse_json(res.into_body()).await;
    assert_eq!(list.len(), 2);
    assert_eq!(list[0].name, "Анна");
    assert_eq!(list[0].drink, "Латте");
    assert_eq!(list[1].name, "Пётр");
    assert_eq!(list[1].drink, "Эспрессо");
}

#[tokio::test]
async fn get_response_contains_all_required_fields() {
    use coffee_shop::models::NewVisitor;

    let db = Arc::new(Db::open_in_memory().unwrap());
    db.insert(&NewVisitor { name: "Лена".into(), drink: "Моккo".into() }).unwrap();

    let res = build_router(db).oneshot(get_req()).await.unwrap();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    let list: serde_json::Value = serde_json::from_slice(&bytes).unwrap();

    let obj = &list[0];
    assert!(obj.get("id").is_some(),    "отсутствует поле id");
    assert!(obj.get("name").is_some(),  "отсутствует поле name");
    assert!(obj.get("drink").is_some(), "отсутствует поле drink");
}

#[tokio::test]
async fn ids_increment_across_multiple_posts() {
    use coffee_shop::models::NewVisitor;

    let db = Arc::new(Db::open_in_memory().unwrap());
    for (name, drink) in [("А", "Латте"), ("Б", "Эспрессо"), ("В", "Моккo")] {
        db.insert(&NewVisitor { name: name.into(), drink: drink.into() }).unwrap();
    }
    let list: Vec<Visitor> = parse_json(
        build_router(db).oneshot(get_req()).await.unwrap().into_body(),
    )
    .await;
    assert_eq!(list.iter().map(|v| v.id).collect::<Vec<_>>(), vec![1, 2, 3]);
}