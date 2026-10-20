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

#[test]
fn backend_default_is_live_and_mock_requires_explicit_selection() {
    assert_eq!(
        crate::BackendMode::parse(None).unwrap(),
        crate::BackendMode::Live
    );
    assert_eq!(
        crate::BackendMode::parse(Some("mock")).unwrap(),
        crate::BackendMode::Mock
    );
    assert!(crate::BackendMode::parse(Some("auto")).is_err());
}

#[tokio::test]
async fn unavailable_live_router_is_labeled_and_never_returns_fake_agents() {
    let feed = world_feed::live::HttpWorldFeed::new(
        "http://127.0.0.1:1",
        world_feed::live::LiveConfig::default(),
    )
    .unwrap();
    let app = build_router(AppState::new(Arc::new(feed)));
    let res = app
        .clone()
        .oneshot(Request::get("/api/roster").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::SERVICE_UNAVAILABLE);
    let res = app
        .clone()
        .oneshot(Request::get("/").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let html = String::from_utf8(
        axum::body::to_bytes(res.into_body(), usize::MAX)
            .await
            .unwrap()
            .to_vec(),
    )
    .unwrap();
    assert!(html.contains("LIVE"));
    assert!(html.contains("unavailable"));
    assert!(html.contains("not supplied"));
    let res = app
        .oneshot(Request::get("/api/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let health: Value = serde_json::from_slice(
        &axum::body::to_bytes(res.into_body(), usize::MAX)
            .await
            .unwrap(),
    )
    .unwrap();
    assert_eq!(health["mode"], "live");
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
async fn inspector_http_escapes_editable_title() {
    use world_feed::{Command, PersonaEdit};
    let state = test_state();
    let id = state.feed.roster().agents[0].persona_id.clone();
    let name = "</title><script>window.__review_xss=1</script><title>";
    state
        .feed
        .apply_command(Command::EditPersona {
            persona_id: id.clone(),
            edit: PersonaEdit {
                name: name.into(),
                playstyle: "mage".into(),
                attitude: "clique".into(),
                chattiness: 0.5,
                schedule: vec![],
            },
        })
        .unwrap();
    let res = build_router(state)
        .oneshot(
            Request::get(format!("/agent/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let html = String::from_utf8(
        axum::body::to_bytes(res.into_body(), usize::MAX)
            .await
            .unwrap()
            .to_vec(),
    )
    .unwrap();
    assert!(html.contains(&format!(
        "<title>ro-bots · {}</title>",
        crate::render::esc(name)
    )));
    assert!(!html.contains(name));
}

#[test]
fn upstream_strings_are_safe_in_remaining_render_contexts() {
    let state = test_state();
    let id = &state.feed.roster().agents[0].persona_id;
    let mut detail = state.feed.agent_detail(id).unwrap();
    detail.attitude = "<img src=x onerror=alert(1)>".into();
    detail.guild_goal = "<script>alert(2)</script>".into();
    detail.persona_id = "';alert(3);//</script>".into();
    let html = crate::render::agent_page_html(&detail);
    assert!(html.contains(&crate::render::esc(&detail.attitude)));
    assert!(!html.contains(&detail.attitude));
    assert!(html.contains(&crate::render::esc(&detail.guild_goal)));
    assert!(!html.contains(&detail.guild_goal));
    assert!(html.contains("const pid = \"';alert(3);//\\u003c/script>\";"));
    let mut roster = state.feed.roster();
    roster.groups[0].attitude.clone_from(&detail.attitude);
    roster.agents[0].attitude.clone_from(&detail.attitude);
    assert!(!crate::render::index_page_html(&roster).contains(&detail.attitude));
    let feed = crate::render::feed_page_html(&[]);
    assert!(!feed.contains("innerHTML"));
    assert!(feed.contains("li.textContent = `[${Math.floor(l.at)}] <${l.sender}> ${l.text}`"));
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
    assert_eq!(roster.seed, Some(777));
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
