//! DTOs for the current Python serializer, not the mock dashboard schema.
#![allow(missing_docs)] // DTO field names mirror the Python serializer exactly.
use crate::{
    AgentDetail, AgentStatus, CharacterSummary, EventKind, GroupInfo, MemoryViewLine,
    ReputationEntry, RosterSnapshot, Severity, WorldEvent,
};
use serde::{Deserialize, Serialize};

pub const MISSING: &str = "not supplied";
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Status {
    pub persona_id: String,
    pub name: String,
    pub playstyle: String,
    pub attitude: String,
    pub chattiness: f64,
    pub level_band: (u32, u32),
    pub group_id: Option<String>,
    pub online: bool,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Roster {
    pub agents: Vec<Status>,
}
impl Roster {
    #[must_use]
    pub fn translate(&self) -> RosterSnapshot {
        let agents: Vec<_> = self
            .agents
            .iter()
            .map(|a| AgentStatus {
                persona_id: a.persona_id.clone(),
                name: a.name.clone(),
                playstyle: a.playstyle.clone(),
                attitude: a.attitude.clone(),
                chattiness: a.chattiness,
                online: a.online,
                group_id: a.group_id.clone().unwrap_or_else(|| MISSING.into()),
            })
            .collect();
        let mut groups: Vec<GroupInfo> = Vec::new();
        for a in &agents {
            if let Some(g) = groups.iter_mut().find(|g| g.group_id == a.group_id) {
                g.member_ids.push(a.persona_id.clone());
            } else {
                groups.push(GroupInfo {
                    group_id: a.group_id.clone(),
                    attitude: MISSING.into(),
                    member_ids: vec![a.persona_id.clone()],
                    schedule: Vec::new(),
                });
            }
        }
        RosterSnapshot {
            seed: None,
            groups,
            agents,
        }
    }
}
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Reputation {
    pub human: String,
    pub agent_score: Option<f64>,
    pub group_score: Option<f64>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Agent {
    pub persona_id: String,
    pub name: String,
    pub playstyle: String,
    pub attitude: String,
    pub chattiness: f64,
    pub level_band: (u32, u32),
    pub online: bool,
    pub goal: Option<String>,
    pub script: Option<String>,
    pub plan: Option<String>,
    pub memory_view: Vec<String>,
    pub reputation: Vec<Reputation>,
    pub characters: Vec<String>,
}
impl Agent {
    #[must_use]
    pub fn translate(&self, group: Option<&str>) -> AgentDetail {
        AgentDetail {
            persona_id: self.persona_id.clone(),
            name: self.name.clone(),
            playstyle: self.playstyle.clone(),
            attitude: self.attitude.clone(),
            chattiness: self.chattiness,
            level_band: self.level_band,
            online: self.online,
            group_id: group.unwrap_or(MISSING).into(),
            current_goal: self.goal.clone().unwrap_or_else(|| MISSING.into()),
            current_script: self.script.clone().unwrap_or_else(|| MISSING.into()),
            current_plan: self.plan.clone().unwrap_or_else(|| MISSING.into()),
            memory_view: self
                .memory_view
                .iter()
                .map(|s| MemoryViewLine {
                    level: None,
                    index: None,
                    summary: s.clone(),
                })
                .collect(),
            reputation: self
                .reputation
                .iter()
                .map(|r| ReputationEntry {
                    human: r.human.clone(),
                    score: None,
                    agent_score: r.agent_score,
                    group_score: r.group_score,
                    last_reason: MISSING.into(),
                    last_at: None,
                })
                .collect(),
            characters: self
                .characters
                .iter()
                .map(|n| CharacterSummary {
                    name: n.clone(),
                    class_path: MISSING.into(),
                    build_summary: MISSING.into(),
                    level: None,
                })
                .collect(),
            personal_goal: MISSING.into(),
            group_goal: MISSING.into(),
            guild_goal: MISSING.into(),
            schedule: Vec::new(),
        }
    }
}
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Event {
    pub ts: f64,
    pub kind: String,
    pub summary: String,
    pub operator_forced: bool,
}
impl Event {
    #[must_use]
    pub fn translate(&self, id: Option<u64>) -> WorldEvent {
        WorldEvent {
            ts: self.ts,
            kind: EventKind::Source,
            payload: serde_json::json!({"source_kind":self.kind,"summary":self.summary,"sequence":id,"provenance":"Python WorldFeed; execution not verified"}),
            severity: Severity::Info,
            operator_forced: self.operator_forced,
        }
    }
}
