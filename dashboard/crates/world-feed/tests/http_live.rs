//! Loopback HTTP fixture evidence only; not native game acceptance.
#![allow(clippy::unwrap_used, clippy::indexing_slicing)]
use axum::{
    http::{HeaderMap, StatusCode},
    routing::{get, post},
    Json, Router,
};
use futures_util::StreamExt;
use std::{
    sync::{Arc, Mutex},
    time::Duration,
};
use world_feed::{
    live::{HttpWorldFeed, LiveConfig},
    Command, PersonaEdit, WorldFeed,
};

#[tokio::test]
#[allow(clippy::too_many_lines)] // one end-to-end loopback fixture lifecycle
async fn loopback_snapshots_reconnect_cursor_errors_and_commands() {
    let cursors = Arc::new(Mutex::new(Vec::<Option<String>>::new()));
    let seen = cursors.clone();
    let posted = Arc::new(Mutex::new(Vec::new()));
    let saved = posted.clone();
    let app = Router::new()
        .route(
            "/feed/roster",
            get(|| async { include_str!("../../../fixtures/roster.json") }),
        )
        .route(
            "/feed/agent/{id}",
            get(|| async { include_str!("../../../fixtures/agent.json") }),
        )
        .route(
            "/feed/events",
            get(move |headers: HeaderMap| {
                let seen = seen.clone();
                async move {
                    seen.lock().unwrap().push(
                        headers
                            .get("last-event-id")
                            .map(|s| s.to_str().unwrap().into()),
                    );
                    (
                        [("content-type", "text/event-stream")],
                        axum::body::Body::from_stream(tokio_stream::iter(
                            include_bytes!("../../../fixtures/events.sse")
                                .chunks(7)
                                .map(|c| Ok::<_, std::io::Error>(c.to_vec()))
                                .collect::<Vec<_>>(),
                        )),
                    )
                }
            }),
        )
        .route(
            "/commands",
            post(move |Json(body): Json<serde_json::Value>| {
                let saved = saved.clone();
                async move {
                    saved.lock().unwrap().push(body);
                    include_str!("../../../fixtures/event.json")
                }
            }),
        );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let url = format!("http://{}", listener.local_addr().unwrap());
    let server = tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });
    let feed = HttpWorldFeed::new(&url, LiveConfig::default()).unwrap();
    assert_eq!(feed.health().status, "unavailable");
    feed.refresh().await.unwrap();
    assert_eq!(feed.roster().seed, None);
    let id = feed.roster().agents[0].persona_id.clone();
    let detail = feed.fetch_agent(&id).await.unwrap().unwrap();
    assert_eq!(detail.current_goal, "grind");
    let mut stream = feed.subscribe();
    feed.consume_events_once().await.unwrap();
    feed.consume_events_once().await.unwrap();
    assert_eq!(feed.health().last_event_id, Some(1));
    assert!(feed
        .health()
        .events_error
        .as_deref()
        .is_some_and(|e| e.contains("replayed")));
    assert_eq!(*cursors.lock().unwrap(), vec![None, Some("1".into())]);

    assert_eq!(stream.next().await.unwrap().unwrap().payload["sequence"], 0);
    assert_eq!(stream.next().await.unwrap().unwrap().payload["sequence"], 1);
    assert!(
        tokio::time::timeout(Duration::from_millis(30), stream.next())
            .await
            .is_err()
    );
    let cmd = Command::EditPersona {
        persona_id: id.clone(),
        edit: PersonaEdit {
            name: "Fixture edit".into(),
            playstyle: "mage".into(),
            attitude: "clique".into(),
            chattiness: 0.5,
            schedule: vec![],
        },
    };
    let ack = feed.send_command(cmd).await.unwrap();
    assert_eq!(ack.payload["execution"], "not verified; WorldState only");
    let body = posted.lock().unwrap()[0].clone();
    assert_eq!(body["name"], "Fixture edit");
    assert!(body.get("edit").is_none());
    assert!(feed
        .send_command(Command::ForceAction {
            persona_id: id,
            action: "chat".into(),
            arg: "hello".into()
        })
        .await
        .is_err());
    assert_eq!(posted.lock().unwrap().len(), 1);
    server.abort();
    let _ = server.await;
    assert!(feed.refresh().await.is_err());
    assert_eq!(feed.health().status, "stale");
    assert!(!feed.roster().agents.is_empty());
}
#[tokio::test]
async fn feed_integrity_survives_transport_reconnects() {
    use std::sync::atomic::{AtomicUsize, Ordering};
    let count = Arc::new(AtomicUsize::new(0));
    let calls = count.clone();
    let app = Router::new()
        .route(
            "/feed/roster",
            get(|| async { include_str!("../../../fixtures/roster.json") }),
        )
        .route(
            "/feed/events",
            get(move || {
                let calls = calls.clone();
                async move {
                    let n = calls.fetch_add(1, Ordering::SeqCst);
                    if n == 1 {
                        return (
                            StatusCode::SERVICE_UNAVAILABLE,
                            axum::http::HeaderMap::new(),
                            axum::body::Body::empty(),
                        );
                    }
                    let event = serde_json::to_string(
                        &serde_json::from_str::<serde_json::Value>(include_str!(
                            "../../../fixtures/event.json"
                        ))
                        .unwrap(),
                    )
                    .unwrap();
                    let text = match n {
                        0 => format!("id: 0\ndata: {event}\n\nid: 3\ndata: {event}\n\n"),
                        2 => ": connected\n\n".into(),
                        3 => String::new(),
                        4 => format!("id: 0\ndata: {event}\n\n"),
                        5 => format!("id: 4\ndata: {event}\n\n"),
                        _ => ": still connected\n\n".into(),
                    };
                    let body = if n >= 6 {
                        axum::body::Body::from_stream(
                            futures_util::stream::once(
                                async move { Ok::<_, std::io::Error>(text) },
                            )
                            .chain(futures_util::stream::pending()),
                        )
                    } else {
                        axum::body::Body::from(text)
                    };
                    let mut headers = axum::http::HeaderMap::new();
                    headers.insert("content-type", "text/event-stream".parse().unwrap());
                    (StatusCode::OK, headers, body)
                }
            }),
        );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let feed = Arc::new(
        HttpWorldFeed::new(
            &format!("http://{}", listener.local_addr().unwrap()),
            LiveConfig::default(),
        )
        .unwrap(),
    );
    let server = tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });
    feed.refresh().await.unwrap();
    feed.consume_events_once().await.unwrap();
    assert!(feed.health().events_error.unwrap().contains("replay gap"));
    assert!(feed.consume_events_once().await.is_err());
    let warning = feed.health().events_error.unwrap();
    assert!(warning.contains("replay gap"));
    assert!(warning.contains("503"));
    for _ in 2..=5 {
        feed.consume_events_once().await.unwrap();
    }
    let warning = feed.health().events_error.unwrap();
    assert!(warning.contains("replay gap"));
    assert!(warning.contains("restart"));
    assert!(!warning.contains("503"));
    assert_eq!(feed.health().last_event_id, Some(4));
    let reader_feed = feed.clone();
    let reader = tokio::spawn(async move { reader_feed.consume_events_once().await });
    tokio::time::timeout(Duration::from_secs(1), async {
        while feed.health().events_status != "connected" {
            tokio::task::yield_now().await;
        }
    })
    .await
    .unwrap();
    assert_eq!(
        feed.health().status,
        "stale",
        "healthy transport cannot restore missing history"
    );
    assert!(feed.health().events_error.unwrap().contains("replay gap"));
    reader.abort();
    let _ = reader.await;
    server.abort();
    let _ = server.await;
}

#[tokio::test]
async fn http_error_and_timeout_never_become_mock() {
    let app = Router::new().route(
        "/feed/roster",
        get(|| async { (StatusCode::SERVICE_UNAVAILABLE, "offline") }),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let feed = HttpWorldFeed::new(
        &format!("http://{}", listener.local_addr().unwrap()),
        LiveConfig::default(),
    )
    .unwrap();
    let server = tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });
    assert!(feed.refresh().await.unwrap_err().contains("503"));
    assert_eq!(feed.health().mode, "live");
    assert_eq!(feed.health().status, "unavailable");
    assert!(feed.roster().agents.is_empty());
    server.abort();
}

#[tokio::test]
async fn timeout_is_bounded_without_mock_fallback() {
    let slow = Router::new().route(
        "/feed/roster",
        get(|| async {
            tokio::time::sleep(Duration::from_secs(2)).await;
            include_str!("../../../fixtures/roster.json")
        }),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let config = LiveConfig {
        request_timeout: Duration::from_millis(50),
        ..LiveConfig::default()
    };
    let feed = HttpWorldFeed::new(
        &format!("http://{}", listener.local_addr().unwrap()),
        config,
    )
    .unwrap();
    let server = tokio::spawn(async move {
        axum::serve(listener, slow).await.unwrap();
    });
    let started = std::time::Instant::now();
    assert!(feed.refresh().await.is_err());
    assert!(started.elapsed() < Duration::from_secs(1));
    assert_eq!(feed.health().status, "unavailable");
    server.abort();
}
