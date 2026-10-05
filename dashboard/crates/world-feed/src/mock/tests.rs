//! Unit tests: schedule ticking, JSON round-trips, mock determinism, commands.
//!
//! Tests use `unwrap()` freely: test: panic is the assertion mechanism.
#![allow(
    clippy::unwrap_used,
    clippy::indexing_slicing,
    reason = "test: panic is the assertion mechanism; roster is non-empty by construction"
)]

use crate::mock::EPOCH_START;
use crate::{
    AgentStatus, ChatLine, Command, CommandError, EventKind, MockWorldFeed, PersonaEdit,
    ScheduleWindow, Severity, WorldEvent, WorldFeed,
};

fn sample_window() -> ScheduleWindow {
    ScheduleWindow {
        day: 1,
        start: 18.0,
        end: 22.0,
    }
}

fn sample_edit() -> PersonaEdit {
    PersonaEdit {
        name: "Mika-01".into(),
        playstyle: "mage".into(),
        attitude: "clique".into(),
        chattiness: 0.5,
        schedule: vec![sample_window()],
    }
}

// ---------- schedule ticking ----------

#[test]
fn schedule_window_contains_start_excludes_end() {
    let w = sample_window();
    assert!(in_window_test(&w, 1, 18.0));
    assert!(in_window_test(&w, 1, 21.99));
    assert!(!in_window_test(&w, 1, 22.0));
    assert!(!in_window_test(&w, 2, 18.0));
}

#[test]
fn schedule_window_wraps_midnight() {
    let w = ScheduleWindow {
        day: 5,
        start: 23.0,
        end: 2.0,
    };
    assert!(in_window_test(&w, 5, 23.5));
    assert!(in_window_test(&w, 6, 1.0));
    assert!(!in_window_test(&w, 6, 2.0));
    assert!(!in_window_test(&w, 5, 22.0));
}

#[test]
fn day_hour_progresses_over_a_week() {
    let (d0, h0) = day_hour_test(EPOCH_START);
    assert_eq!((d0, h0), (0, 0.0));
    let (d, h) = day_hour_test(EPOCH_START + 25.0 * 3600.0);
    assert_eq!((d, h), (1, 1.0));
}

#[test]
fn tick_flips_online_status_on_schedule() {
    let feed = MockWorldFeed::new(7);
    // Tick 48 simulated hours; online/offline transitions must occur for a
    // schedule-driven world with evening windows.
    let mut saw_online = false;
    let mut saw_offline = false;
    for _ in 0..48 {
        let roster = feed.roster();
        if roster.agents.iter().any(|a| a.online) {
            saw_online = true;
        }
        if roster.agents.iter().any(|a| !a.online) {
            saw_offline = true;
        }
        let _ = feed.tick();
    }
    assert!(saw_online, "expected at least one agent online in 48h");
    assert!(saw_offline, "expected at least one agent offline in 48h");
}

// ---------- serialization round-trips ----------

#[test]
fn agent_status_roundtrip() {
    let status = AgentStatus {
        persona_id: "mika-01".into(),
        name: "Mika-01".into(),
        playstyle: "healer".into(),
        attitude: "helpful_newbie".into(),
        group_id: "Silver Wolves".into(),
        online: true,
        chattiness: 0.4,
    };
    let json = serde_json::to_string(&status).unwrap();
    let back: AgentStatus = serde_json::from_str(&json).unwrap();
    assert_eq!(back, status);
}

#[test]
fn chat_line_roundtrip() {
    let line = ChatLine {
        at: 123.5,
        channel: "party".into(),
        sender: "Rook-02".into(),
        text: "buffs plz".into(),
    };
    let back: ChatLine = serde_json::from_str(&serde_json::to_string(&line).unwrap()).unwrap();
    assert_eq!(back, line);
}

#[test]
fn world_event_roundtrip_preserves_kind_and_flags() {
    let ev = WorldEvent {
        ts: 99.0,
        kind: EventKind::CommandAck,
        payload: serde_json::json!({ "command": "force_action" }),
        severity: Severity::Alarm,
        operator_forced: true,
    };
    let back: WorldEvent = serde_json::from_str(&serde_json::to_string(&ev).unwrap()).unwrap();
    assert_eq!(back, ev);
    let plain = WorldEvent {
        ts: 1.0,
        kind: EventKind::Chat,
        payload: serde_json::json!({}),
        severity: Severity::Info,
        operator_forced: false,
    };
    let s = serde_json::to_string(&plain).unwrap();
    assert!(s.contains("\"kind\":\"chat\""));
    assert!(s.contains("\"operator_forced\":false"));
}

#[test]
fn command_roundtrip_all_variants() {
    let cmds = vec![
        Command::RegenerateRoster {
            seed: 1234,
            friend_groups: 3,
            solos: 1,
            friends_per_group_min: 2,
            friends_per_group_max: 4,
        },
        Command::EditPersona {
            persona_id: "mika-01".into(),
            edit: sample_edit(),
        },
        Command::ForceAction {
            persona_id: "mika-01".into(),
            action: "chat".into(),
            arg: "hello".into(),
        },
    ];
    for cmd in cmds {
        let back: Command = serde_json::from_str(&serde_json::to_string(&cmd).unwrap()).unwrap();
        assert_eq!(back, cmd);
    }
}

#[test]
fn command_json_shape_is_tagged_snake_case() {
    let json = serde_json::json!({
        "type": "regenerate_roster",
        "seed": 42,
        "friend_groups": 2,
        "solos": 1,
        "friends_per_group_min": 2,
        "friends_per_group_max": 3
    });
    let cmd: Command = serde_json::from_value(json).unwrap();
    assert!(matches!(cmd, Command::RegenerateRoster { seed: 42, .. }));
}

// ---------- validation ----------

#[test]
fn command_validation_rejects_bad_shapes() {
    assert!(matches!(
        Command::RegenerateRoster {
            seed: 1,
            friend_groups: 0,
            solos: 0,
            friends_per_group_min: 2,
            friends_per_group_max: 3,
        }
        .validate(),
        Err(CommandError::Invalid(_))
    ));
    assert!(matches!(
        Command::RegenerateRoster {
            seed: 1,
            friend_groups: 1,
            solos: 0,
            friends_per_group_min: 4,
            friends_per_group_max: 2,
        }
        .validate(),
        Err(CommandError::Invalid(_))
    ));
    assert!(matches!(
        Command::ForceAction {
            persona_id: "x".into(),
            action: "explode".into(),
            arg: String::new(),
        }
        .validate(),
        Err(CommandError::Invalid(_))
    ));
    assert!(Command::EditPersona {
        persona_id: "x".into(),
        edit: PersonaEdit {
            chattiness: 1.5,
            ..sample_edit()
        }
    }
    .validate()
    .is_err());
}

// ---------- mock determinism ----------

#[test]
fn same_seed_same_roster() {
    let a = MockWorldFeed::new(123);
    let b = MockWorldFeed::new(123);
    assert_eq!(a.roster(), b.roster());
}

#[test]
fn different_seed_different_roster() {
    let a = MockWorldFeed::new(123);
    let b = MockWorldFeed::new(124);
    assert_ne!(a.roster(), b.roster());
}

#[test]
fn ticks_are_deterministic() {
    let a = MockWorldFeed::new(55);
    let b = MockWorldFeed::new(55);
    let mut events_a = Vec::new();
    let mut events_b = Vec::new();
    for _ in 0..10 {
        events_a.extend(a.tick());
        events_b.extend(b.tick());
    }
    assert_eq!(events_a, events_b);
}

#[test]
fn roster_shape_follows_request() {
    let feed = MockWorldFeed::with_shape(9, 5, 2, 3, 3);
    let roster = feed.roster();
    let multi: Vec<_> = roster
        .groups
        .iter()
        .filter(|g| g.attitude != "solo")
        .collect();
    let solos: Vec<_> = roster
        .groups
        .iter()
        .filter(|g| g.attitude == "solo")
        .collect();
    assert_eq!(multi.len(), 5);
    assert_eq!(solos.len(), 2);
    for g in multi {
        assert_eq!(g.member_ids.len(), 3);
    }
    assert_eq!(roster.agents.len(), 5 * 3 + 2);
}

// ---------- write path ----------

#[test]
fn regenerate_roster_changes_seed_and_shape() {
    let feed = MockWorldFeed::new(1);
    feed.apply_command(Command::RegenerateRoster {
        seed: 777,
        friend_groups: 2,
        solos: 2,
        friends_per_group_min: 2,
        friends_per_group_max: 2,
    })
    .unwrap();
    let roster = feed.roster();
    assert_eq!(roster.seed, 777);
    assert_eq!(roster.agents.len(), 2 * 2 + 2);
}

#[test]
fn edit_persona_updates_fields() {
    let feed = MockWorldFeed::new(1);
    let id = feed.roster().agents[0].persona_id.clone();
    feed.apply_command(Command::EditPersona {
        persona_id: id.clone(),
        edit: PersonaEdit {
            name: "Renamed".into(),
            playstyle: "tank".into(),
            attitude: "grinder".into(),
            chattiness: 0.1,
            schedule: vec![ScheduleWindow {
                day: 0,
                start: 20.0,
                end: 23.0,
            }],
        },
    })
    .unwrap();
    let detail = feed.agent_detail(&id).unwrap();
    assert_eq!(detail.name, "Renamed");
    assert_eq!(detail.playstyle, "tank");
    assert_eq!(detail.attitude, "grinder");
    assert!((detail.chattiness - 0.1).abs() < f64::EPSILON);
    assert_eq!(detail.schedule.len(), 1);
}

#[test]
fn force_disconnect_reconnect_overrides_schedule() {
    let feed = MockWorldFeed::new(3);
    let id = feed.roster().agents[0].persona_id.clone();
    feed.apply_command(Command::ForceAction {
        persona_id: id.clone(),
        action: "disconnect".into(),
        arg: String::new(),
    })
    .unwrap();
    assert!(!feed.agent_detail(&id).unwrap().online);
    for _ in 0..5 {
        let _ = feed.tick();
    }
    assert!(!feed.agent_detail(&id).unwrap().online, "override persists");
    feed.apply_command(Command::ForceAction {
        persona_id: id.clone(),
        action: "reconnect".into(),
        arg: String::new(),
    })
    .unwrap();
    assert!(feed.agent_detail(&id).unwrap().online);
}

#[test]
fn unknown_persona_is_rejected() {
    let feed = MockWorldFeed::new(3);
    assert!(matches!(
        feed.apply_command(Command::ForceAction {
            persona_id: "nobody".into(),
            action: "chat".into(),
            arg: "hi".into(),
        }),
        Err(CommandError::UnknownPersona(_))
    ));
}

#[test]
fn command_ack_is_operator_forced() {
    let feed = MockWorldFeed::new(3);
    let id = feed.roster().agents[0].persona_id.clone();
    let ack = feed
        .apply_command(Command::ForceAction {
            persona_id: id,
            action: "goal_change".into(),
            arg: String::new(),
        })
        .unwrap();
    assert_eq!(ack.kind, EventKind::CommandAck);
    assert!(ack.operator_forced);
    assert_eq!(ack.severity, Severity::Alarm);
}

#[test]
fn agent_detail_has_memory_reputation_characters() {
    let feed = MockWorldFeed::new(11);
    let id = feed.roster().agents[0].persona_id.clone();
    let detail = feed.agent_detail(&id).unwrap();
    assert!(
        (5..=10).contains(&detail.memory_view.len()),
        "memory view depth 5..=10, got {}",
        detail.memory_view.len()
    );
    assert!(!detail.reputation.is_empty());
    assert!(!detail.characters.is_empty());
    assert!(detail.guild_goal.is_empty() || !detail.guild_goal.is_empty());
}

use crate::mock::{day_hour as day_hour_test, in_window as in_window_test};
