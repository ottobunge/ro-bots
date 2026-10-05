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
    Html(index_page_html(&state.feed.roster()))
}

/// `GET /config` — configurator page (ADR-008 #1).
async fn config_page(State(state): State<AppState>) -> Html<String> {
    Html(configurator_html(state.feed.roster().seed))
}

/// `GET /feed` — live feed page (chat styled as MMO chat).
async fn feed_page(State(state): State<AppState>) -> Html<String> {
    let recent = state.feed.recent_chat(25);
    Html(feed_page_html(&recent))
}

/// `GET /agent/:id` — inspector page.
async fn agent_page(State(state): State<AppState>, Path(persona_id): Path<String>) -> Response {
    match state.feed.agent_detail(&persona_id) {
        Some(detail) => Html(agent_page_html(&detail)).into_response(),
        None => (StatusCode::NOT_FOUND, format!("unknown agent {persona_id}")).into_response(),
    }
}

/// `GET /api/roster` — roster snapshot JSON.
async fn api_roster(State(state): State<AppState>) -> Json<world_feed::RosterSnapshot> {
    Json(state.feed.roster())
}

/// `GET /api/agent/:id` — agent detail JSON.
async fn api_agent(State(state): State<AppState>, Path(persona_id): Path<String>) -> Response {
    match state.feed.agent_detail(&persona_id) {
        Some(detail) => Json(detail).into_response(),
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

/// `POST /commands` — write path (ADR-008): apply + ack the command.
async fn api_commands(State(state): State<AppState>, Json(cmd): Json<Command>) -> Response {
    match state.feed.apply_command(cmd) {
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
async fn liveview_page() -> Html<String> {
    Html(liveview::liveview_shell_html())
}

/// Build the full router.
pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/", get(index_page))
        .route("/config", get(config_page))
        .route("/feed", get(feed_page))
        .route("/agent/{id}", get(agent_page))
        .route("/api/roster", get(api_roster))
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

/// Bind `127.0.0.1:8400` and serve until stopped.
///
/// # Errors
///
/// Returns the underlying `std::io::Error` when the listener cannot be bound
/// or the accept loop fails.
pub async fn serve(state: AppState) -> std::io::Result<()> {
    let addr = std::net::SocketAddr::from(([127, 0, 0, 1], 8400));
    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("dashboard listening on http://{addr}");
    axum::serve(listener, build_router(state)).await
}

/// Entry point: mock feed + background ticker + axum server.
#[tokio::main]
async fn main() {
    let seed = std::env::var("ROBOTS_SEED")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(42);
    let feed = Arc::new(world_feed::MockWorldFeed::new(seed));
    let state = AppState::new(feed.clone());
    let _ticker = feed.clone().spawn_ticker(std::time::Duration::from_secs(2));
    if let Err(err) = serve(state).await {
        eprintln!("server error: {err}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests;
