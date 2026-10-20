//! Offline validation probes; extreme inputs are never posted or generated.
#![allow(clippy::unwrap_used)]
use world_feed::{live::command_payload, Command, CommandError, WorldFeed};

#[test]
fn public_mock_generator_rejects_invalid_shape() {
    // Small over-limit shape reproduces the public bypass without a huge allocation.
    for (groups, solos, min, max) in [
        (1, 0, 17, 17),
        (u32::MAX, 1, 2, 2),
        (1, 0, 2, u32::MAX),
        (0, 0, 2, 2),
    ] {
        assert!(matches!(
            world_feed::MockWorldFeed::with_shape(1, groups, solos, min, max),
            Err(CommandError::Invalid(_))
        ));
    }
    let feed = world_feed::MockWorldFeed::with_shape(1, 1, 3, 7, 7).unwrap();
    let before = feed.roster();
    assert_eq!(before.agents.len(), 10);
    let cmd = Command::RegenerateRoster {
        seed: 2,
        friend_groups: 1,
        solos: 0,
        friends_per_group_min: 17,
        friends_per_group_max: 17,
    };
    assert!(matches!(
        feed.apply_command(cmd),
        Err(CommandError::Invalid(_))
    ));
    assert_eq!(feed.roster(), before);
}

#[tokio::test]
async fn oversized_rosters_reject_before_network() {
    use std::sync::{
        atomic::{AtomicUsize, Ordering},
        Arc,
    };
    let requests = Arc::new(AtomicUsize::new(0));
    let seen = requests.clone();
    let app = axum::Router::new().fallback(move || {
        let seen = seen.clone();
        async move {
            seen.fetch_add(1, Ordering::SeqCst);
            axum::http::StatusCode::INTERNAL_SERVER_ERROR
        }
    });
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let feed = world_feed::live::HttpWorldFeed::new(
        &format!("http://{}", listener.local_addr().unwrap()),
        world_feed::live::LiveConfig::default(),
    )
    .unwrap();
    let server = tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });
    // Validation only for the million-group probe: never generate/post it.
    for (groups, solos, min, max) in [
        (1_000_000, 0, 2, 2),
        (0, 4097, 2, 2),
        (1, 0, 17, 17),
        (2048, 1, 2, 2),
        (u32::MAX, 0, 2, 2),
        (1, 0, 2, u32::MAX),
    ] {
        let cmd = Command::RegenerateRoster {
            seed: 1,
            friend_groups: groups,
            solos,
            friends_per_group_min: min,
            friends_per_group_max: max,
        };
        assert!(matches!(
            command_payload(&cmd),
            Err(CommandError::Invalid(_))
        ));
        assert!(matches!(
            feed.send_command(cmd).await,
            Err(CommandError::Invalid(_))
        ));
    }
    assert_eq!(requests.load(Ordering::SeqCst), 0);
    server.abort();
    let _ = server.await;
    for (groups, solos, min, max) in [(1, 0, 7, 7), (0, 4096, 2, 2), (256, 0, 16, 16)] {
        let cmd = Command::RegenerateRoster {
            seed: 1,
            friend_groups: groups,
            solos,
            friends_per_group_min: min,
            friends_per_group_max: max,
        };
        assert!(command_payload(&cmd).is_ok());
    }
}

#[test]
fn json_u32_extrema_reject_without_panic() {
    for (groups, solos) in [(u32::MAX, 1), (1, u32::MAX), (u32::MAX, u32::MAX)] {
        let cmd: Command = serde_json::from_value(serde_json::json!({
            "type":"regenerate_roster", "seed":1, "friend_groups":groups,
            "solos":solos, "friends_per_group_min":2, "friends_per_group_max":2,
        }))
        .unwrap();
        let result = std::panic::catch_unwind(|| command_payload(&cmd));
        assert!(
            result.is_ok(),
            "validation must not panic for legal JSON u32 values"
        );
        assert!(matches!(result.unwrap(), Err(CommandError::Invalid(_))));
    }
}
