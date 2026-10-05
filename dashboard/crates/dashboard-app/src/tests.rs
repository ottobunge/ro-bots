//! HTTP-level tests over the axum router with the `MockWorldFeed` backend.
//!
//! Tests use `unwrap()` freely: test: panic is the assertion mechanism.
#![allow(
    clippy::unwrap_used,
    clippy::indexing_slicing,
    reason = "test: panic is the assertion mechanism; roster is non-empty by construction"
)]

use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use serde_json::{json, Value};
use tower::ServiceExt;

use crate::{build_router, AppState};

fn test_state() -> AppState {
    AppState::new(Arc::new(world_feed::MockWorldFeed::new(42)))
}

#[tokio::test]
async fn roster_page_lists_groups_and_agents() {
    let app = build_router(test_state());
    let res = app
        .oneshot(Request::get("/").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body = axum::body::to_bytes(res.into_body(), usize::MAX)
        .await
        .unwrap();
    let html = String::from_utf8(body.to_vec()).unwrap();
    assert!(html.contains("ro-bots roster"));
    assert!(html.contains("seed: 42"));
    assert!(html.contains("/agent/"));
}

#[tokio::test]
async fn roster_api_returns_snapshot_json() {
    let app = build_router(test_state());
    let res = app
        .oneshot(Request::get("/api/roster").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body = axum::body::to_bytes(res.into_body(), usize::MAX)
        .await
        .unwrap();
    let v: Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(v["seed"], 42);
    assert!(v["groups"].as_array().unwrap().len() >= 3);
    assert!(v["agents"].as_array().unwrap().len() >= 6);
}

#[tokio::test]
async fn agent_page_renders_memory_and_reputation() {
    let state = test_state();
    let id = state.feed.roster().agents[0].persona_id.clone();
    let app = build_router(state);
    let res = app
        .oneshot(
            Request::get(format!("/agent/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body = axum::body::to_bytes(res.into_body(), usize::MAX)
        .await
        .unwrap();
    let html = String::from_utf8(body.to_vec()).unwrap();
    assert!(html.contains("memory view"));
    assert!(html.contains("reputation ledger"));
    assert!(html.contains("force actions"));
    assert!(html.contains("edit persona"));
}

#[tokio::test]
async fn agent_page_unknown_id_is_404() {
    let app = build_router(test_state());
    let res = app
        .oneshot(
            Request::get("/agent/does-not-exist")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn commands_endpoint_applies_force_action() {
    let state = test_state();
    let id = state.feed.roster().agents[0].persona_id.clone();
    let app = build_router(state.clone());
    let res = app
        .oneshot(
            Request::post("/commands")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "type": "force_action",
                        "persona_id": id,
                        "action": "disconnect",
                        "arg": ""
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body = axum::body::to_bytes(res.into_body(), usize::MAX)
        .await
        .unwrap();
    let ack: Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(ack["kind"], "command_ack");
    assert_eq!(ack["operator_forced"], true);
    let id = state.feed.roster().agents[0].persona_id.clone();
    assert!(!state.feed.agent_detail(&id).unwrap().online);
}

#[tokio::test]
async fn commands_endpoint_rejects_unknown_persona() {
    let app = build_router(test_state());
    let res = app
        .oneshot(
            Request::post("/commands")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "type": "force_action",
                        "persona_id": "ghost",
                        "action": "chat",
                        "arg": "hi"
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn commands_endpoint_regenerates_roster() {
    let state = test_state();
    let app = build_router(state.clone());
    let res = app
        .oneshot(
            Request::post("/commands")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "type": "regenerate_roster",
                        "seed": 777,
                        "friend_groups": 2,
                        "solos": 1,
                        "friends_per_group_min": 2,
                        "friends_per_group_max": 2
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let roster = state.feed.roster();
    assert_eq!(roster.seed, 777);
    assert_eq!(roster.agents.len(), 2 * 2 + 1);
}

#[tokio::test]
async fn configurator_and_feed_pages_render() {
    let app = build_router(test_state());
    for path in ["/config", "/feed"] {
        let res = app
            .clone()
            .oneshot(Request::get(path).body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::OK, "{path} must render");
    }
}

#[tokio::test]
async fn liveview_ws_route_is_wired() {
    let app = build_router(test_state());
    let res = app
        .oneshot(
            Request::get("/live/ws")
                .header("connection", "upgrade")
                .header("upgrade", "websocket")
                .header("sec-websocket-version", "13")
                .header("sec-websocket-key", "dGhlIHNhbXBsZSBub25jZQ==")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    // The route must exist and attempt an upgrade. Without a live TCP peer
    // axum may answer 426 instead of 101 in the oneshot harness; both prove
    // the WS route is wired (a 404/405 would mean it is not).
    assert!(
        res.status() == StatusCode::SWITCHING_PROTOCOLS
            || res.status() == StatusCode::UPGRADE_REQUIRED,
        "unexpected status {}",
        res.status()
    );
}
