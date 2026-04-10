//! Loyalty micro-service — HTTP layer only.
//!
//! Business logic lives in [`loyalty`]; this file wires it to actix-web.

mod loyalty;

use actix_web::{web, App, HttpResponse, HttpServer};
use serde::{Deserialize, Serialize};

// ── Wire-format types ────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct PointsRequest {
    // `item` is part of the API contract and must be deserialised, but point
    // calculation is identical for every drink so we don't use it here.
    #[allow(dead_code)]
    item: String,
    loyalty_card: bool,
}

#[derive(Serialize, Deserialize)]
struct PointsResponse {
    points: u32,
}

// ── HTTP handler ─────────────────────────────────────────────────────────────

async fn post_points(req: web::Json<PointsRequest>) -> HttpResponse {
    let points = loyalty::calculate_points(req.loyalty_card);
    HttpResponse::Ok().json(PointsResponse { points })
}

/// Register all routes onto `cfg`.
/// Called from both `main` and integration tests — single source of truth.
pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.route("/points", web::post().to(post_points));
}

// ── Entry point ──────────────────────────────────────────────────────────────

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));

    // Read port from environment so docker-compose can override without rebuild.
    let port = std::env::var("PORT").unwrap_or_else(|_| "8081".to_string());
    let addr = format!("0.0.0.0:{port}");

    log::info!("loyalty service listening on :{port}");

    HttpServer::new(|| App::new().configure(configure))
        .bind(&addr)?
        .run()
        .await
}

// ── Integration tests ────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::{test, App};

    macro_rules! app {
        () => {
            test::init_service(App::new().configure(configure)).await
        };
    }

    macro_rules! points_req {
        ($item:expr, $card:expr) => {
            test::TestRequest::post()
                .uri("/points")
                .set_json(serde_json::json!({ "item": $item, "loyalty_card": $card }))
                .to_request()
        };
    }

    #[actix_web::test]
    async fn post_points_returns_200() {
        let app = app!();
        let resp = test::call_service(&app, points_req!("espresso", false)).await;
        assert!(resp.status().is_success());
    }

    #[actix_web::test]
    async fn no_loyalty_card_returns_base_points() {
        let app = app!();
        let resp: PointsResponse =
            test::call_and_read_body_json(&app, points_req!("espresso", false)).await;
        assert_eq!(resp.points, loyalty::BASE_POINTS);
    }

    #[actix_web::test]
    async fn loyalty_card_returns_base_plus_bonus() {
        let app = app!();
        let resp: PointsResponse =
            test::call_and_read_body_json(&app, points_req!("latte", true)).await;
        assert_eq!(resp.points, loyalty::BASE_POINTS + loyalty::LOYALTY_BONUS);
    }

    /// Every menu item earns the same base points — `item` is structural only.
    #[actix_web::test]
    async fn all_menu_items_earn_same_base_points() {
        let app = app!();
        for drink in ["espresso", "latte", "cappuccino"] {
            let resp: PointsResponse =
                test::call_and_read_body_json(&app, points_req!(drink, false)).await;
            assert_eq!(
                resp.points,
                loyalty::BASE_POINTS,
                "drink '{drink}' should earn BASE_POINTS"
            );
        }
    }
}