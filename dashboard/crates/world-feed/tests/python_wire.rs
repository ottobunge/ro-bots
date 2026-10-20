//! Offline cross-language snapshots.
#![allow(clippy::unwrap_used, clippy::indexing_slicing)]
use world_feed::wire::{Agent, Roster};

#[test]
fn python_snapshots_preserve_supplied_data_without_inventing_builds() {
    let roster: Roster =
        serde_json::from_str(include_str!("../../../fixtures/roster.json")).unwrap();
    let translated = roster.translate();
    assert_eq!(translated.seed, None);
    assert_eq!(translated.agents.len(), roster.agents.len());
    let wire: Agent = serde_json::from_str(include_str!("../../../fixtures/agent.json")).unwrap();
    let detail = wire.translate(None);
    assert_eq!(detail.current_goal, "grind");
    assert_eq!(detail.memory_view[0].summary, wire.memory_view[0]);
    assert_eq!(detail.memory_view[0].level, None);
    assert_eq!(detail.characters[0].name, "Fixture Character");
    assert_eq!(detail.characters[0].level, None);
    assert_eq!(detail.characters[0].build_summary, "not supplied");
    assert_eq!(detail.personal_goal, "not supplied");
    assert_eq!(detail.guild_goal, "not supplied");
    assert_eq!(detail.reputation[0].agent_score, Some(0.4));
    assert!(detail.reputation[0].group_score.is_some());
    assert_eq!(detail.reputation[0].last_at, None);
}
