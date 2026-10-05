//! # `world-feed` — the `WorldFeed` contract (ADR-007/ADR-008)
//!
//! The dashboard is a consumer adapter: it never touches the simulation.
//! The boundary is this contract, split in two halves:
//!
//! - **Read path** ([`WorldFeed`]): a broadcast stream of [`WorldEvent`]s
//!   (SSE/WS-ready JSON) plus a small snapshot query API (`roster`,
//!   [`AgentDetail`]).
//! - **Write path** ([`Command`], ADR-008): operator commands
//!   (`regenerate_roster`, `edit_persona`, `force_action`) sent by the
//!   dashboard and consumed by the runtime. All command outcomes re-enter
//!   the read path as events tagged [`EventKind::CommandAck`].
//!
//! [`MockWorldFeed`] implements both sides over a seeded, deterministic fake
//! world so the dashboard is demoable and testable offline. The Python
//! runtime will implement the same types over the real sim.

use serde::{Deserialize, Serialize};

pub mod mock;
pub use mock::MockWorldFeed;

/// Severity of one world event, used by the UI for row tinting.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    /// Routine chatter, arrivals, departures.
    Info,
    /// Reputation shifts, party changes, notable kills.
    Notable,
    /// Wipes, operator-forced injections, emergencies.
    Alarm,
}

/// Discriminant of a [`WorldEvent`] payload summary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EventKind {
    /// A chat line was emitted in some channel.
    Chat,
    /// An agent connected (schedule or forced).
    Online,
    /// An agent disconnected (schedule or forced).
    Offline,
    /// An agent finished / switched its current goal.
    GoalChange,
    /// A party invite was extended or accepted.
    PartyInvite,
    /// A reputation event moved scores.
    Reputation,
    /// A wipe happened to a party or group.
    Wipe,
    /// Operator command acknowledged (ADR-008 audit trail).
    CommandAck,
}

/// One chat line, wherever it appeared.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ChatLine {
    /// Server-time epoch seconds.
    pub at: f64,
    /// Channel: `map`, `party`, `guild`, `whisper:<name>`.
    pub channel: String,
    /// Display name of the sender.
    pub sender: String,
    /// Verbatim text.
    pub text: String,
}

/// A persona as the roster view sees it (ADR-005).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AgentStatus {
    /// Stable persona id.
    pub persona_id: String,
    /// Display name.
    pub name: String,
    /// Combat role (tank/healer/mage/hunter/support/melee).
    pub playstyle: String,
    /// Group attitude (`helpful_newbie`/`clique`/`event_focused`/`grinder`/`solo`).
    pub attitude: String,
    /// Friend-group this persona belongs to.
    pub group_id: String,
    /// Online right now, per schedule + overrides.
    pub online: bool,
    /// Persona chattiness 0..1.
    pub chattiness: f64,
}

/// One reputation ledger row for one human, as seen by one agent.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ReputationEntry {
    /// Human player display name.
    pub human: String,
    /// Score in [-1, 1].
    pub score: f64,
    /// Last reason the score moved.
    pub last_reason: String,
    /// When the score last moved (epoch seconds).
    pub last_at: f64,
}

/// One OptChat-style memory view line, `L<level>:<index> <summary>` (ADR-004).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MemoryViewLine {
    /// Tree level (0 = verbatim note).
    pub level: u32,
    /// Node index at that level.
    pub index: u64,
    /// Node summary text (without the `Lx:y` prefix).
    pub summary: String,
}

/// A character the agent created, per ADR-009.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CharacterSummary {
    /// In-game character name.
    pub name: String,
    /// Class/job path, e.g. `Acolyte -> Priest`.
    pub class_path: String,
    /// One-line build plan summary.
    pub build_summary: String,
    /// Current level of this character.
    pub level: u32,
}

/// One weekly schedule window: `(weekday 0-6 Mon..Sun, start_hour, end_hour)`.
/// Windows may wrap midnight (`start > end`).
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct ScheduleWindow {
    /// Day of week, Monday = 0.
    pub day: u8,
    /// Start hour in `[0, 24)`.
    pub start: f64,
    /// End hour (may be < start when wrapping midnight).
    pub end: f64,
}

/// Persona fields the operator may edit (ADR-008).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PersonaEdit {
    /// Display name.
    pub name: String,
    /// Combat role.
    pub playstyle: String,
    /// Group attitude.
    pub attitude: String,
    /// Chattiness 0..1.
    pub chattiness: f64,
    /// Weekly online windows.
    pub schedule: Vec<ScheduleWindow>,
}

/// Full per-agent detail for the inspector page.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AgentDetail {
    /// Stable persona id.
    pub persona_id: String,
    /// Display name.
    pub name: String,
    /// Combat role.
    pub playstyle: String,
    /// Group attitude.
    pub attitude: String,
    /// Friend-group id.
    pub group_id: String,
    /// Online right now.
    pub online: bool,
    /// Chattiness 0..1.
    pub chattiness: f64,
    /// Level band `(min, max)`.
    pub level_band: (u32, u32),
    /// Current goal, one line.
    pub current_goal: String,
    /// Current behavior script, one line.
    pub current_script: String,
    /// Current plan steps, one line.
    pub current_plan: String,
    /// OptChat-style memory view (newest last).
    pub memory_view: Vec<MemoryViewLine>,
    /// Reputation ledger: per-human scores with last reason.
    pub reputation: Vec<ReputationEntry>,
    /// Characters this agent created (ADR-009).
    pub characters: Vec<CharacterSummary>,
    /// Personal goal line.
    pub personal_goal: String,
    /// Friend-group goal line.
    pub group_goal: String,
    /// Guild goal line (empty when unguilded).
    pub guild_goal: String,
    /// Weekly schedule.
    pub schedule: Vec<ScheduleWindow>,
}

/// One friend-group summary for the roster view.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GroupInfo {
    /// Group id.
    pub group_id: String,
    /// Shared attitude label.
    pub attitude: String,
    /// Member persona ids.
    pub member_ids: Vec<String>,
    /// Weekly schedule (shared by members).
    pub schedule: Vec<ScheduleWindow>,
}

/// Snapshot of the whole society: groups + agents + seed.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RosterSnapshot {
    /// Seed the active world was generated from (reproducibility, ADR-008).
    pub seed: u64,
    /// Friend groups incl. solo outsiders.
    pub groups: Vec<GroupInfo>,
    /// One status per agent.
    pub agents: Vec<AgentStatus>,
}

/// A streamed world event: ts + kind + payload summary.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorldEvent {
    /// Server-time epoch seconds.
    pub ts: f64,
    /// Discriminant.
    pub kind: EventKind,
    /// Free-form payload summary (JSON object fields vary by kind).
    pub payload: serde_json::Value,
    /// Severity hint for the UI.
    pub severity: Severity,
    /// True when this event was injected by an operator command (ADR-008).
    pub operator_forced: bool,
}

/// Operator commands (ADR-008 write path).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Command {
    /// Regenerate the mock roster from a seed.
    RegenerateRoster {
        /// Seed for the roster builder.
        seed: u64,
        /// Number of friend groups (>= 0).
        friend_groups: u32,
        /// Number of solo outsiders (>= 0).
        solos: u32,
        /// Min friends per group.
        friends_per_group_min: u32,
        /// Max friends per group.
        friends_per_group_max: u32,
    },
    /// Edit persona fields.
    EditPersona {
        /// Target persona.
        persona_id: String,
        /// New field values.
        edit: PersonaEdit,
    },
    /// Inject a forced action (audited as operator-forced).
    ForceAction {
        /// Target persona.
        persona_id: String,
        /// `goal_change` | `chat` | `party_invite` | `disconnect` | `reconnect`.
        action: String,
        /// Optional argument (e.g. chat text).
        arg: String,
    },
}

/// Errors the write path can return; the dashboard maps these to HTTP 4xx/5xx.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum CommandError {
    /// Unknown persona id.
    #[error("unknown persona: {0}")]
    UnknownPersona(String),
    /// Malformed command (bad action name, min > max, out-of-range value...).
    #[error("invalid command: {0}")]
    Invalid(String),
    /// The feed backend is gone (e.g. runtime disconnected).
    #[error("feed unavailable")]
    Unavailable,
}

impl Command {
    /// Validate shape-only invariants (ranges, action names).
    ///
    /// # Errors
    ///
    /// Returns [`CommandError`] when a command is malformed: out-of-range
    /// roster parameters or an unknown `force_action` action name.
    pub fn validate(&self) -> Result<(), CommandError> {
        match self {
            Command::RegenerateRoster {
                seed: _,
                friend_groups,
                solos,
                friends_per_group_min,
                friends_per_group_max,
            } => {
                if *friends_per_group_min == 0 {
                    return Err(CommandError::Invalid(
                        "friends_per_group_min must be >= 1".into(),
                    ));
                }
                if friends_per_group_min > friends_per_group_max {
                    return Err(CommandError::Invalid(
                        "friends_per_group_min > friends_per_group_max".into(),
                    ));
                }
                if *friend_groups + *solos == 0 {
                    return Err(CommandError::Invalid(
                        "at least one group or solo required".into(),
                    ));
                }
                Ok(())
            }
            Command::EditPersona { edit, .. } => {
                if !(0.0..=1.0).contains(&edit.chattiness) {
                    return Err(CommandError::Invalid("chattiness must be in [0, 1]".into()));
                }
                if edit.name.trim().is_empty() {
                    return Err(CommandError::Invalid("name must not be empty".into()));
                }
                for w in &edit.schedule {
                    if w.day > 6 || !(0.0..24.0).contains(&w.start) {
                        return Err(CommandError::Invalid(
                            "schedule window day must be 0..6, start in [0, 24)".into(),
                        ));
                    }
                }
                Ok(())
            }
            Command::ForceAction { action, .. } => {
                const ACTIONS: [&str; 5] = [
                    "goal_change",
                    "chat",
                    "party_invite",
                    "disconnect",
                    "reconnect",
                ];
                if ACTIONS.contains(&action.as_str()) {
                    Ok(())
                } else {
                    Err(CommandError::Invalid(format!(
                        "action must be one of {ACTIONS:?}"
                    )))
                }
            }
        }
    }
}

/// Read half of the contract: snapshot queries + a broadcast event stream.
///
/// Implementors must be cheap to clone / share behind an `Arc`; the stream is
/// a `tokio::sync::broadcast` receiver re-emitted as JSON lines (SSE-ready).
pub trait WorldFeed: Send + Sync + 'static {
    /// Current roster snapshot (groups, agents, seed).
    fn roster(&self) -> RosterSnapshot;

    /// Full detail for one persona, or `None` if unknown.
    fn agent_detail(&self, persona_id: &str) -> Option<AgentDetail>;

    /// Subscribe to the live event stream (JSON lines).
    fn subscribe(&self) -> tokio_stream::wrappers::BroadcastStream<WorldEvent>;

    /// Most recent chat lines (for the live feed page); empty by default.
    fn recent_chat(&self, limit: usize) -> Vec<ChatLine> {
        let _ = limit;
        Vec::new()
    }

    /// Apply an operator command; returns the acknowledgement event.
    ///
    /// # Errors
    /// [`CommandError`] variants map to 4xx/503 responses.
    fn apply_command(&self, cmd: Command) -> Result<WorldEvent, CommandError>;
}
