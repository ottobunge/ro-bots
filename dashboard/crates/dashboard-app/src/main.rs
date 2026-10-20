//! Axum server: static routes + JSON API + SSE feed + one `LiveView` route.
//!
//! Contract: all state comes from the `WorldFeed` implementation; there is
//! no database. The `LiveView` at `/live` gets the feed stream via a Dioxus
//! signal; the JSON API mirrors the same contract for tests and tooling.

#![forbid(unsafe_code)]

mod liveview;
mod render;

use std::sync::Arc;

use axum::extract::ws::WebSocketUpgrade;
use axum::extract::{Path, State};
use axum::http::{header, StatusCode};
use axum::response::sse::{Event as SseEvent, KeepAlive, Sse};
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use futures_util::StreamExt;
use world_feed::{Command, CommandError, WorldFeed};

use crate::render::{agent_page_html, configurator_html, feed_page_html, index_page_html};

/// Shared app state: the (mock) feed backend. Identity equality on the Arc.
#[derive(Clone)]
pub struct AppState {
    feed: Arc<dyn WorldFeed>,
}

impl PartialEq for AppState {
    fn eq(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.feed, &other.feed)
    }
}

impl AppState {
    /// Build state from any `WorldFeed` implementation.
    pub fn new(feed: Arc<dyn WorldFeed>) -> Self {
        Self { feed }
    }
}

fn error_response(err: &CommandError) -> Response {
    let status = match err {
        CommandError::UnknownPersona(_) | CommandError::Invalid(_) => {
            StatusCode::UNPROCESSABLE_ENTITY
        }
        CommandError::Unavailable => StatusCode::SERVICE_UNAVAILABLE,
    };
    (status, err.to_string()).into_response()
}

/// `GET /` — roster page.
async fn index_page(State(state): State<AppState>) -> Html<String> {
    Html(mark_page(index_page_html(&state.feed.roster()), &state))
}

/// `GET /config` — configurator page (ADR-008 #1).
async fn config_page(State(state): State<AppState>) -> Html<String> {
    Html(mark_page(
        configurator_html(state.feed.roster().seed),
        &state,
    ))
}

/// `GET /feed` — live feed page (chat styled as MMO chat).
async fn feed_page(State(state): State<AppState>) -> Html<String> {
    let recent = state.feed.recent_chat(25);
    Html(mark_page(feed_page_html(&recent), &state))
}

/// `GET /agent/:id` — inspector page.
async fn agent_page(State(state): State<AppState>, Path(persona_id): Path<String>) -> Response {
    match state.feed.fetch_agent(&persona_id).await {
        Ok(Some(detail)) => Html(mark_page(agent_page_html(&detail), &state)).into_response(),
        Ok(None) => (StatusCode::NOT_FOUND, format!("unknown agent {persona_id}")).into_response(),
        Err(e) => (
            StatusCode::SERVICE_UNAVAILABLE,
            format!("live detail unavailable: {e}"),
        )
            .into_response(),
    }
}

/// `GET /api/roster` — roster snapshot JSON.
async fn api_roster(State(state): State<AppState>) -> Response {
    let health = state.feed.health();
    if health.status == "unavailable" {
        return (StatusCode::SERVICE_UNAVAILABLE, Json(health)).into_response();
    }
    (
        [("x-worldfeed-status", health.status)],
        Json(state.feed.roster()),
    )
        .into_response()
}

/// `GET /api/agent/:id` — agent detail JSON.
async fn api_agent(State(state): State<AppState>, Path(persona_id): Path<String>) -> Response {
    match state.feed.fetch_agent(&persona_id).await {
        Ok(Some(detail)) => Json(detail).into_response(),
        Ok(None) => StatusCode::NOT_FOUND.into_response(),
        Err(e) => (StatusCode::SERVICE_UNAVAILABLE, e).into_response(),
    }
}

/// `POST /commands` — write path (ADR-008): apply + ack the command.
async fn api_commands(State(state): State<AppState>, Json(cmd): Json<Command>) -> Response {
    match state.feed.send_command(cmd).await {
        Ok(ack) => Json(ack).into_response(),
        Err(err) => error_response(&err),
    }
}

/// `GET /api/events` — SSE stream of world events.
async fn api_events_sse(
    State(state): State<AppState>,
) -> Sse<impl futures_util::Stream<Item = Result<SseEvent, std::convert::Infallible>>> {
    let stream = state.feed.subscribe().filter_map(|item| async move {
        match item {
            Ok(ev) => Some(Ok(SseEvent::default()
                .data(serde_json::to_string(&ev).unwrap_or_else(|_| "{}".into())))),
            // Lagged receivers simply skip missed events.
            Err(_) => None,
        }
    });
    Sse::new(stream).keep_alive(KeepAlive::default())
}

/// `GET /live/ws` — `LiveView` websocket upgrade.
async fn liveview_ws(State(state): State<AppState>, ws: WebSocketUpgrade) -> Response {
    ws.on_upgrade(move |socket| liveview::launch_socket(socket, state.clone()))
}

/// `GET /live` — `LiveView` shell page.
async fn liveview_page(State(state): State<AppState>) -> Html<String> {
    Html(mark_page(liveview::liveview_shell_html(), &state))
}

async fn api_health(State(state): State<AppState>) -> Json<world_feed::FeedHealth> {
    Json(state.feed.health())
}

#[allow(clippy::needless_pass_by_value)] // owns generated HTML; call sites remain readable.
fn mark_page(html: String, state: &AppState) -> String {
    let h = state.feed.health();
    let label = if h.mode == "mock" {
        "MOCK DEMO — synthetic activity"
    } else {
        "LIVE — Python WorldFeed; not gameplay verification"
    };
    let banner=format!("<aside id=\"feed-health\"><b>{label}</b> {} <a href=\"/api/health\">transport health</a></aside><script>setInterval(async()=>{{try{{const r=await fetch('/api/health');const h=await r.json();document.getElementById('feed-health').textContent=(h.mode==='mock'?'MOCK DEMO — synthetic activity':'LIVE — Python WorldFeed; not gameplay verification')+' | '+h.status+' | events: '+h.events_status+' | '+(h.error||h.events_error||'');}}catch{{document.getElementById('feed-health').textContent='dashboard unavailable';}}}},2000);</script>",render::esc(&h.status));
    html.replacen("<body>", &format!("<body>{banner}"), 1)
}

/// Build the full router.
pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/", get(index_page))
        .route("/config", get(config_page))
        .route("/feed", get(feed_page))
        .route("/agent/{id}", get(agent_page))
        .route("/api/roster", get(api_roster))
        .route("/api/health", get(api_health))
        .route("/api/agent/{id}", get(api_agent))
        .route("/commands", post(api_commands))
        .route("/api/events", get(api_events_sse))
        .route("/live", get(liveview_page))
        .route("/live/ws", get(liveview_ws))
        .route(
            "/static/style.css",
            get(|| async {
                (
                    [(header::CONTENT_TYPE, "text/css")],
                    include_str!("../assets/style.css"),
                )
            }),
        )
        .with_state(state)
}

/// Bind and serve until stopped.
///
/// The bind address defaults to `127.0.0.1:8401` for native runs; in
/// containers (docker-compose.worlds.yml) `DASHBOARD_BIND=0.0.0.0:8400` is
/// set because rootless docker's rootlessport proxy cannot reach a
/// 127.0.0.1-bound service — the host-side publish stays 127.0.0.1-bound.
///
/// # Errors
///
/// Returns the underlying `std::io::Error` when the listener cannot be bound
/// or the accept loop fails.
pub async fn serve(state: AppState) -> std::io::Result<()> {
    let addr = std::env::var("DASHBOARD_BIND").unwrap_or_else(|_| "127.0.0.1:8401".into());
    let listener = tokio::net::TcpListener::bind(addr.as_str()).await?;
    println!("dashboard listening on http://{addr}");
    axum::serve(listener, build_router(state)).await
}

/// Explicit backend choice; absence means live, never demo fallback.
#[derive(Debug, PartialEq)]
enum BackendMode {
    Live,
    Mock,
}
impl BackendMode {
    fn parse(value: Option<&str>) -> Result<Self, String> {
        match value.unwrap_or("live") {
            "live" => Ok(Self::Live),
            "mock" => Ok(Self::Mock),
            other => Err(format!(
                "invalid WORLDFEED_BACKEND {other:?}; choose live or mock"
            )),
        }
    }
}

#[tokio::main]
async fn main() {
    let mode = match BackendMode::parse(std::env::var("WORLDFEED_BACKEND").ok().as_deref()) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    let (feed, tasks): (Arc<dyn WorldFeed>, Vec<tokio::task::JoinHandle<()>>) = match mode {
        BackendMode::Mock => {
            let seed = std::env::var("ROBOTS_SEED")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(42);
            let feed = Arc::new(world_feed::MockWorldFeed::new(seed));
            let tasks = vec![feed.clone().spawn_ticker(std::time::Duration::from_secs(2))];
            (feed, tasks)
        }
        BackendMode::Live => {
            let url =
                std::env::var("WORLDFEED_URL").unwrap_or_else(|_| "http://127.0.0.1:8400".into());
            let feed = match world_feed::live::HttpWorldFeed::new(
                &url,
                world_feed::live::LiveConfig::default(),
            ) {
                Ok(f) => Arc::new(f),
                Err(e) => {
                    eprintln!("live backend configuration: {e}");
                    std::process::exit(2);
                }
            };
            let tasks = feed.spawn();
            (feed, tasks)
        }
    };
    let result = serve(AppState::new(feed)).await;
    for task in tasks {
        task.abort();
    }
    if let Err(err) = result {
        eprintln!("server error: {err}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests;
