//! `MockWorldFeed` — a seeded, deterministic fake world implementing the
//! full [`WorldFeed`] contract (read + write, ADR-007/008).
//!
//! Determinism: the world state is a pure function of `(seed, tick, command
//! history)`. Two `MockWorldFeed`s started with the same seed and fed the
//! same commands produce identical snapshots and event sequences. Wall-clock
//! time is *not* used for the schedule clock — a virtual clock advances one
//! simulated hour per tick so tests don't sleep and the online/offline
//! rhythm is reproducible.

use std::sync::Mutex;

use rand::rngs::SmallRng;
use rand::{RngExt, SeedableRng};
use rand_pcg::Pcg64;
use tokio_stream::wrappers::BroadcastStream;

use crate::{
    AgentDetail, AgentStatus, CharacterSummary, ChatLine, Command, CommandError, EventKind,
    GroupInfo, MemoryViewLine, ReputationEntry, RosterSnapshot, ScheduleWindow, Severity,
    WorldEvent, WorldFeed,
};

/// Simulated epoch seconds at world creation (2026-01-05, a Monday, 00:00).
pub const EPOCH_START: f64 = 1_767_580_800.0;
/// Simulated seconds per tick (one simulated hour per tick).
pub const SECONDS_PER_TICK: f64 = 3600.0;
const CHANNEL_CAP: usize = 512;
/// Memory-view depth per agent (5..=10 lines, ADR-007).
const MEMORY_LINES: usize = 8;

const PLAYSTYLES: [&str; 6] = ["tank", "healer", "mage", "hunter", "support", "melee"];
const ATTITUDES: [&str; 4] = ["helpful_newbie", "clique", "event_focused", "grinder"];
const SOLO_ATTITUDE: &str = "solo";
const NAMES: [&str; 20] = [
    "Mika", "Doramir", "Sable", "Fenris", "Yuni", "Kaede", "Bramble", "Toma", "Elka", "Rook",
    "Silvie", "Nari", "Garrick", "Perrin", "Ash", "Lumi", "Odric", "Wren", "Talia", "Bex",
];
const GROUP_ADJ: [&str; 8] = [
    "Silver",
    "Grim",
    "Wandering",
    "Azure",
    "Iron",
    "Quiet",
    "Amber",
    "Restless",
];
const GROUP_NOUN: [&str; 8] = [
    "Wolves", "Lanterns", "Blades", "Owls", "Bells", "Foxes", "Pilgrims", "Ash",
];
const CHAT_LINES: [&str; 10] = [
    "LFP at the fountain, need 1 more",
    "buffs plz",
    "anyone seen my mace drop?",
    "wts +4 chain mail 2k",
    "woe practice at 21:00, be there",
    "gtg dinner, back in 30",
    "that knight KS'd me again",
    "nice drop grats",
    "portal up in 2 min",
    "who pulled?!",
];
const GOALS: [&str; 6] = [
    "grind to job level 40",
    "farm --z for equipment fund",
    "level in culverts",
    "complete knight quest chain",
    "stock up on blue gems",
    "find a steady party for eden dailies",
];
const SCRIPTS: [&str; 4] = [
    "grind_map(map=orcs, loop_until=hp<30%)",
    "town_idle(npc_square, chat_watch=true)",
    "quest_run(eden_board, step=3)",
    "party_follow(leader=auto, range=6)",
];
const REASONS_UP: [&str; 4] = [
    "shared loot from orc grind",
    "healed me during a wipe",
    "gave free fly wings",
    "buffed the whole party",
];
const REASONS_DOWN: [&str; 4] = [
    "kill-stealing in culverts",
    "dead weight, went AFK mid-mob",
    "rude in party chat",
    "looted and left",
];
const CLASS_PATHS: [&str; 6] = [
    "Swordsman -> Knight",
    "Acolyte -> Priest",
    "Mage -> Wizard",
    "Archer -> Hunter",
    "Acolyte -> Monk",
    "Merchant -> Blacksmith",
];

/// Pick from one of the module's non-empty `const` string tables.
///
/// The tables are never empty, so `idx % len` is always in bounds and the
/// direct index cannot panic.
#[allow(clippy::indexing_slicing)] // table.len() > 0, idx is reduced modulo it
fn pick<'a>(table: &[&'a str], idx: usize) -> &'a str {
    table[idx % table.len()]
}

#[derive(Debug, Clone)]
struct MockCharacter {
    name: String,
    class_path: String,
    build: String,
    level: u32,
}

#[derive(Debug, Clone)]
struct MockAgent {
    persona_id: String,
    name: String,
    playstyle: String,
    attitude: String,
    chattiness: f64,
    level_band: (u32, u32),
    group_id: String,
    online: bool,
    online_override: Option<bool>,
    goal: String,
    script: String,
    plan: String,
    personal_goal: String,
    group_goal: String,
    guild_goal: String,
    memory: Vec<(u32, u64, String)>,
    reputation: Vec<ReputationEntry>,
    characters: Vec<MockCharacter>,
    schedule: Vec<ScheduleWindow>,
}

#[derive(Debug, Clone)]
struct MockGroup {
    group_id: String,
    attitude: String,
    member_ids: Vec<String>,
    schedule: Vec<ScheduleWindow>,
}

#[derive(Debug)]
struct World {
    seed: u64,
    tick: f64,
    groups: Vec<MockGroup>,
    agents: Vec<MockAgent>,
}

impl World {
    /// Online status of one agent at a given tick: override first, then the
    /// union of the agent's own windows and its group's shared windows.
    #[allow(dead_code)] // schedule logic exercised via tests + inlined at the tick loop
    fn is_online_at(&self, agent: &MockAgent, tick: f64) -> bool {
        if let Some(forced) = agent.online_override {
            return forced;
        }
        let (day, hour) = day_hour(tick);
        agent
            .schedule
            .iter()
            .chain(self.schedule_extra(&agent.group_id))
            .any(|w| in_window(w, day, hour))
    }

    /// The group's shared schedule windows for a group id.
    #[allow(dead_code)]
    fn schedule_extra(&self, group_id: &str) -> &[ScheduleWindow] {
        self.groups
            .iter()
            .find(|g| g.group_id == group_id)
            .map_or(&[], |g| g.schedule.as_slice())
    }
}

fn day_hour(tick: f64) -> (u8, f64) {
    let total_hours = (tick - EPOCH_START) / 3600.0;
    // day is non-negative for all reachable ticks (EPOCH_START or later) and
    // small enough for `u8`; the cast cannot truncate or lose sign in practice.
    #[allow(clippy::cast_sign_loss, clippy::cast_possible_truncation)]
    let day = (total_hours / 24.0).floor() as u8;
    let hour = total_hours - f64::from(u16::from(day) * 24);
    (day % 7, hour)
}

fn in_window(w: &ScheduleWindow, day: u8, hour: f64) -> bool {
    if w.start <= w.end {
        w.day == day && w.start <= hour && hour < w.end
    } else {
        (w.day == day && hour >= w.start)
            || ((u16::from(w.day) + 1) % 7 == u16::from(day) && hour < w.end)
    }
}

fn clamp1(v: f64) -> f64 {
    v.clamp(-1.0, 1.0)
}

/// Build the deterministic roster for one seed. `friend_groups` groups of
/// `friends_per_group` members plus `solos` single-person groups.
#[allow(clippy::too_many_lines)] // linear, table-driven builder; splitting hides the shape
fn build_roster(
    seed: u64,
    friend_groups: u32,
    solos: u32,
    fpg_min: u32,
    fpg_max: u32,
) -> (Vec<MockGroup>, Vec<MockAgent>) {
    let mut rng = Pcg64::new(u128::from(seed), 0xA0F1_5AFE_1234_5678_9ABC_DEF0_1357_2468);
    let mut groups = Vec::new();
    let mut agents = Vec::new();
    let mut name_i = 0usize;

    // Build the world with a plain helper fn (closure borrow rules get hairy
    // when the closure both pushes to `agents` and the caller mutates it).
    #[allow(clippy::items_after_statements)] // helper must live where the borrows it needs are
    fn make_agent(
        agents: &mut Vec<MockAgent>,
        rng: &mut Pcg64,
        name_i: &mut usize,
        attitude: &str,
        group_id: String,
    ) -> String {
        let base = pick(&NAMES, *name_i % NAMES.len());
        let id = format!("{}-{:02}", base.to_lowercase(), *name_i + 1);
        *name_i += 1;
        let schedule_len = rng.random_range(1..=3);
        let mut schedule = Vec::with_capacity(schedule_len);
        for _ in 0..schedule_len {
            let day = rng.random_range(0..7u8);
            let start = rng.random_range(16.0..22.0);
            let dur = rng.random_range(2.0..4.0);
            schedule.push(ScheduleWindow {
                day,
                start,
                end: (start + dur) % 24.0,
            });
        }
        let characters = (0..rng.random_range(1..=2))
            .map(|_| MockCharacter {
                name: format!(
                    "{base}'s {}",
                    pick(&["Alt1", "Main"], rng.random_range(0..2))
                ),
                class_path: pick(&CLASS_PATHS, rng.random_range(0..CLASS_PATHS.len())).to_string(),
                build: format!(
                    "{} / {} focus, target lvl {}",
                    pick(
                        &["full STR", "full INT", "AGI dodge", "VIT tank"],
                        rng.random_range(0..4)
                    ),
                    pick(
                        &["melee dps", "support line", "nuker", "trapper"],
                        rng.random_range(0..4)
                    ),
                    rng.random_range(40..=99)
                ),
                level: rng.random_range(10..=99),
            })
            .collect::<Vec<_>>();
        agents.push(MockAgent {
            persona_id: id.clone(),
            name: id.clone(),
            playstyle: pick(&PLAYSTYLES, rng.random_range(0..PLAYSTYLES.len())).to_string(),
            attitude: attitude.to_string(),
            chattiness: rng.random_range(0.1..0.9),
            level_band: (rng.random_range(1..70), rng.random_range(70..99)),
            group_id,
            online: false,
            online_override: None,
            goal: format!(
                "{} (target lvl {})",
                pick(&GOALS, rng.random_range(0..GOALS.len())),
                rng.random_range(30..99)
            ),
            script: pick(&SCRIPTS, rng.random_range(0..SCRIPTS.len())).to_string(),
            plan: "1. move to map 2. kill loop 3. vend loot".to_string(),
            personal_goal: format!("reach lvl {}", rng.random_range(50..99)),
            group_goal: "keep party slots full, split drops fairly".to_string(),
            guild_goal: if rng.random_bool(0.5) {
                "win WoE defense next Saturday".to_string()
            } else {
                String::new()
            },
            memory: Vec::new(),
            reputation: Vec::new(),
            characters,
            schedule,
        });
        id
    }

    for _ in 0..friend_groups {
        let size = rng.random_range(fpg_min..=fpg_max.max(fpg_min));
        let attitude = pick(&ATTITUDES, rng.random_range(0..ATTITUDES.len()));
        let group_id = format!(
            "{} {}",
            pick(&GROUP_ADJ, rng.random_range(0..GROUP_ADJ.len())),
            pick(&GROUP_NOUN, rng.random_range(0..GROUP_NOUN.len()))
        );
        let shared_schedule_len = rng.random_range(1..=2);
        let mut shared_schedule = Vec::with_capacity(shared_schedule_len);
        for _ in 0..shared_schedule_len {
            let day = rng.random_range(0..7u8);
            let start = rng.random_range(17.0..21.0);
            shared_schedule.push(ScheduleWindow {
                day,
                start,
                end: (start + rng.random_range(2.0..4.0)) % 24.0,
            });
        }
        let mut member_ids = Vec::with_capacity(size as usize);
        for _ in 0..size {
            let id = make_agent(
                &mut agents,
                &mut rng,
                &mut name_i,
                attitude,
                group_id.clone(),
            );
            let agent = agents.last_mut().unwrap_or_else(|| unreachable_no_agent());
            agent.schedule.extend(shared_schedule.iter().copied());
            member_ids.push(id);
        }
        groups.push(MockGroup {
            group_id,
            attitude: attitude.to_string(),
            member_ids,
            schedule: shared_schedule,
        });
    }
    for s in 0..solos {
        let id = make_agent(
            &mut agents,
            &mut rng,
            &mut name_i,
            SOLO_ATTITUDE,
            format!("solo-out-{s}"),
        );
        let agent = agents.last_mut().unwrap_or_else(|| unreachable_no_agent());
        let group_id = agent.group_id.clone();
        groups.push(MockGroup {
            group_id,
            attitude: SOLO_ATTITUDE.to_string(),
            member_ids: vec![id],
            schedule: Vec::new(),
        });
    }

    // Seed memory views + reputation ledgers deterministically.
    let mut chat_rng = SmallRng::seed_from_u64(seed ^ 0xBEEF);
    for (i, agent) in agents.iter_mut().enumerate() {
        for lvl in 0..MEMORY_LINES {
            let text = match lvl {
                0 => format!(
                    "chat: {}",
                    pick(&CHAT_LINES, chat_rng.random_range(0..CHAT_LINES.len()))
                ),
                1 => format!(
                    "combat: killed {} orcs, looted {}z",
                    chat_rng.random_range(10..80),
                    chat_rng.random_range(200..2000)
                ),
                2 => format!(
                    "party: partied with {} for {}h",
                    pick(&NAMES, chat_rng.random_range(0..NAMES.len())),
                    chat_rng.random_range(1..4)
                ),
                _ => format!(
                    "session: played {}h, {} events, net {}z",
                    chat_rng.random_range(1..6),
                    chat_rng.random_range(20..200),
                    chat_rng.random_range(-500..2000)
                ),
            };
            agent.memory.push((
                u32::try_from(lvl).unwrap_or_default(),
                i as u64 * 10 + lvl as u64,
                text,
            ));
        }
        let humans = ["0tt0", "Nova", "Kazuma", "milktea", "Rurutia"];
        for h in humans.iter().take(chat_rng.random_range(2..=4)) {
            let up = chat_rng.random_bool(0.6);
            // `i` is a small loop index; the f64 cast is exact.
            #[allow(clippy::cast_precision_loss)]
            let last_at = EPOCH_START + (i as f64 + 1.0) * 600.0;
            agent.reputation.push(ReputationEntry {
                human: (*h).to_string(),
                score: clamp1(chat_rng.random_range(-0.8..0.9)),
                last_reason: if up {
                    pick(&REASONS_UP, chat_rng.random_range(0..REASONS_UP.len())).to_string()
                } else {
                    pick(&REASONS_DOWN, chat_rng.random_range(0..REASONS_DOWN.len())).to_string()
                },
                last_at,
            });
        }
    }
    (groups, agents)
}

/// Unreachable: `last_mut` after a push in the same block.
#[cold]
#[inline(never)]
fn unreachable_no_agent() -> &'static mut MockAgent {
    unreachable!("agent was just pushed")
}

/// Seeded mock implementation of the whole `WorldFeed` contract.
pub struct MockWorldFeed {
    inner: Mutex<World>,
    tx: tokio::sync::broadcast::Sender<WorldEvent>,
}

impl MockWorldFeed {
    /// Create a mock world with default shape: 3 friend groups of 2..4 plus
    /// 1 solo outsider, seed 42.
    #[must_use]
    pub fn new(seed: u64) -> Self {
        Self::with_shape(seed, 3, 1, 2, 4)
    }

    /// Create a mock world with an explicit shape.
    #[must_use]
    pub fn with_shape(
        seed: u64,
        friend_groups: u32,
        solos: u32,
        fpg_min: u32,
        fpg_max: u32,
    ) -> Self {
        let (tx, _rx) = tokio::sync::broadcast::channel(CHANNEL_CAP);
        let (groups, agents) = build_roster(seed, friend_groups, solos, fpg_min, fpg_max);
        let mut world = World {
            seed,
            tick: EPOCH_START,
            groups,
            agents,
        };
        let initial = mock_tick_events(&mut world, seed);
        let feed = Self {
            inner: Mutex::new(world),
            tx,
        };
        for ev in initial {
            let _ = feed.tx.send(ev);
        }
        feed
    }

    /// Advance the world one tick: schedule ticking, a burst of chat and
    /// world events. Returns the emitted events.
    #[must_use]
    pub fn tick(&self) -> Vec<WorldEvent> {
        let mut world = match self.inner.lock() {
            Ok(w) => w,
            Err(e) => e.into_inner(),
        };
        let seed = world.seed;
        world.tick += SECONDS_PER_TICK;
        let events = mock_tick_events(&mut world, seed);
        for ev in &events {
            let _ = self.tx.send(ev.clone());
        }
        events
    }

    /// Spawn a background ticker emitting a batch of events every `period`.
    #[must_use]
    pub fn spawn_ticker(
        self: std::sync::Arc<Self>,
        period: std::time::Duration,
    ) -> tokio::task::JoinHandle<()> {
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(period);
            interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
            loop {
                interval.tick().await;
                let _ = self.tick();
            }
        })
    }

    /// Most recent chat lines across the world (for the live feed page).
    fn recent_chat_impl(&self, limit: usize) -> Vec<ChatLine> {
        let world = match self.inner.lock() {
            Ok(w) => w,
            Err(e) => e.into_inner(),
        };
        let mut lines: Vec<ChatLine> = Vec::new();
        for agent in &world.agents {
            for (lvl, idx, text) in agent.memory.iter().rev() {
                if *lvl == 0 && lines.len() < limit * 2 {
                    // `idx` is a small per-agent line index; the cast is exact.
                    #[allow(clippy::cast_precision_loss)]
                    let at = EPOCH_START + *idx as f64 * 60.0;
                    lines.push(ChatLine {
                        at,
                        channel: "map".to_string(),
                        sender: agent.name.clone(),
                        text: text.trim_start_matches("chat: ").to_string(),
                    });
                }
            }
        }
        lines.sort_by(|a, b| a.at.total_cmp(&b.at));
        lines.into_iter().rev().take(limit).collect()
    }
}

#[allow(clippy::too_many_lines)] // one seeded branch per event kind; splitting obscures the odds
#[allow(clippy::indexing_slicing)] // every index is random_range(0..len) behind an is_empty guard
fn mock_tick_events(world: &mut World, seed: u64) -> Vec<WorldEvent> {
    // The tick is a non-negative f64 in practice; negative values seed 0 and
    // huge values truncate at u64::MAX — either is fine for an RNG seed.
    #[allow(clippy::cast_sign_loss, clippy::cast_possible_truncation)]
    let tick_u64 = world.tick as u64;
    let mut rng = SmallRng::seed_from_u64(seed ^ tick_u64);
    let mut events = Vec::new();
    let now = world.tick;

    // Schedule ticking: online/offline transitions.
    for agent in &mut world.agents {
        let online = if let Some(forced) = agent.online_override {
            forced
        } else {
            let mut windows: Vec<ScheduleWindow> = agent.schedule.clone();
            if let Some(group) = world.groups.iter().find(|g| g.group_id == agent.group_id) {
                windows.extend(group.schedule.iter().copied());
            }
            let (day, hour) = day_hour(now);
            windows.iter().any(|w| in_window(w, day, hour))
        };
        if online != agent.online {
            agent.online = online;
            events.push(WorldEvent {
                ts: now,
                kind: if online {
                    EventKind::Online
                } else {
                    EventKind::Offline
                },
                payload: serde_json::json!({
                    "persona_id": agent.persona_id,
                    "name": agent.name,
                    "group_id": agent.group_id,
                }),
                severity: Severity::Info,
                operator_forced: false,
            });
        }
    }

    // Chat lines from online, chatty agents.
    for agent in world.agents.iter().filter(|a| a.online) {
        if rng.random::<f64>() < agent.chattiness * 0.5 {
            let line = pick(&CHAT_LINES, rng.random_range(0..CHAT_LINES.len()));
            events.push(WorldEvent {
                ts: now,
                kind: EventKind::Chat,
                payload: serde_json::json!({
                    "line": ChatLine {
                        at: now,
                        channel: "map".to_string(),
                        sender: agent.name.clone(),
                        text: line.to_string(),
                    }
                }),
                severity: Severity::Info,
                operator_forced: false,
            });
        }
    }

    // Occasional goal changes / party invites / reputation / wipes.
    if !world.agents.is_empty() {
        if rng.random_bool(0.4) {
            let i = rng.random_range(0..world.agents.len());
            let new_goal = pick(&GOALS, rng.random_range(0..GOALS.len()));
            let agent = &mut world.agents[i];
            agent.goal = format!("{new_goal} (target lvl {})", rng.random_range(30..99));
            let id = agent.persona_id.clone();
            let goal = agent.goal.clone();
            events.push(WorldEvent {
                ts: now,
                kind: EventKind::GoalChange,
                payload: serde_json::json!({ "persona_id": id, "goal": goal }),
                severity: Severity::Notable,
                operator_forced: false,
            });
        }
        if rng.random_bool(0.3) {
            let i = rng.random_range(0..world.agents.len());
            let j = rng.random_range(0..world.agents.len());
            let from = world.agents[i].name.clone();
            let to = world.agents[j].name.clone();
            events.push(WorldEvent {
                ts: now,
                kind: EventKind::PartyInvite,
                payload: serde_json::json!({
                    "from": from,
                    "to": to,
                    "accepted": rng.random_bool(0.7),
                }),
                severity: Severity::Notable,
                operator_forced: false,
            });
        }
        if rng.random_bool(0.25) {
            let i = rng.random_range(0..world.agents.len());
            let up = rng.random_bool(0.6);
            let human = pick(
                &["0tt0", "Nova", "Kazuma", "milktea", "Rurutia"],
                rng.random_range(0..5),
            );
            let reason = if up {
                pick(&REASONS_UP, rng.random_range(0..REASONS_UP.len()))
            } else {
                pick(&REASONS_DOWN, rng.random_range(0..REASONS_DOWN.len()))
            };
            let delta = clamp1((if up { 0.1 } else { -0.15 }) * rng.random_range(0.5..1.5));
            let entry = {
                let agent = &world.agents[i];
                ReputationEntry {
                    human: human.to_string(),
                    score: clamp1(
                        agent
                            .reputation
                            .iter()
                            .find(|r| r.human == human)
                            .map_or(delta, |r| r.score + delta),
                    ),
                    last_reason: reason.to_string(),
                    last_at: now,
                }
            };
            {
                let agent = &mut world.agents[i];
                if let Some(slot) = agent.reputation.iter_mut().find(|r| r.human == human) {
                    *slot = entry.clone();
                } else {
                    agent.reputation.push(entry.clone());
                }
            }
            let id = world.agents[i].persona_id.clone();
            events.push(WorldEvent {
                ts: now,
                kind: EventKind::Reputation,
                payload: serde_json::json!({
                    "persona_id": id,
                    "human": human,
                    "delta": delta,
                    "reason": reason,
                }),
                severity: Severity::Notable,
                operator_forced: false,
            });
        }
        if rng.random_bool(0.12) {
            let i = rng.random_range(0..world.agents.len());
            let party = world.agents[i].group_id.clone();
            events.push(WorldEvent {
                ts: now,
                kind: EventKind::Wipe,
                payload: serde_json::json!({
                    "party": party,
                    "where": serde_json::json!(pick(&["Orc Dungeon", "Culverts", "Glast Heim"], rng.random_range(0..3))),
                    "losses_z": rng.random_range(100..5000),
                }),
                severity: Severity::Alarm,
                operator_forced: false,
            });
        }
    }
    events
}

impl WorldFeed for MockWorldFeed {
    fn roster(&self) -> RosterSnapshot {
        let world = match self.inner.lock() {
            Ok(w) => w,
            Err(e) => e.into_inner(),
        };
        RosterSnapshot {
            seed: world.seed,
            groups: world
                .groups
                .iter()
                .map(|g| GroupInfo {
                    group_id: g.group_id.clone(),
                    attitude: g.attitude.clone(),
                    member_ids: g.member_ids.clone(),
                    schedule: g.schedule.clone(),
                })
                .collect(),
            agents: world
                .agents
                .iter()
                .map(|a| AgentStatus {
                    persona_id: a.persona_id.clone(),
                    name: a.name.clone(),
                    playstyle: a.playstyle.clone(),
                    attitude: a.attitude.clone(),
                    group_id: a.group_id.clone(),
                    online: a.online,
                    chattiness: a.chattiness,
                })
                .collect(),
        }
    }

    fn recent_chat(&self, limit: usize) -> Vec<ChatLine> {
        self.recent_chat_impl(limit)
    }

    fn agent_detail(&self, persona_id: &str) -> Option<AgentDetail> {
        let world = match self.inner.lock() {
            Ok(w) => w,
            Err(e) => e.into_inner(),
        };
        world
            .agents
            .iter()
            .find(|a| a.persona_id == persona_id)
            .map(|a| AgentDetail {
                persona_id: a.persona_id.clone(),
                name: a.name.clone(),
                playstyle: a.playstyle.clone(),
                attitude: a.attitude.clone(),
                group_id: a.group_id.clone(),
                online: a.online,
                chattiness: a.chattiness,
                level_band: a.level_band,
                current_goal: a.goal.clone(),
                current_script: a.script.clone(),
                current_plan: a.plan.clone(),
                memory_view: a
                    .memory
                    .iter()
                    .map(|(lvl, idx, text)| MemoryViewLine {
                        level: *lvl,
                        index: *idx,
                        summary: text.clone(),
                    })
                    .collect(),
                reputation: a.reputation.clone(),
                characters: a
                    .characters
                    .iter()
                    .map(|c| CharacterSummary {
                        name: c.name.clone(),
                        class_path: c.class_path.clone(),
                        build_summary: c.build.clone(),
                        level: c.level,
                    })
                    .collect(),
                personal_goal: a.personal_goal.clone(),
                group_goal: a.group_goal.clone(),
                guild_goal: a.guild_goal.clone(),
                schedule: a.schedule.clone(),
            })
    }

    fn subscribe(&self) -> BroadcastStream<WorldEvent> {
        BroadcastStream::new(self.tx.subscribe())
    }

    #[allow(clippy::too_many_lines)] // one match arm per command; each is a self-contained ack
    fn apply_command(&self, cmd: Command) -> Result<WorldEvent, CommandError> {
        cmd.validate()?;
        let mut world = match self.inner.lock() {
            Ok(w) => w,
            Err(e) => e.into_inner(),
        };
        let now = world.tick;
        match cmd {
            Command::RegenerateRoster {
                seed,
                friend_groups,
                solos,
                friends_per_group_min,
                friends_per_group_max,
            } => {
                let (groups, agents) = build_roster(
                    seed,
                    friend_groups,
                    solos,
                    friends_per_group_min,
                    friends_per_group_max,
                );
                world.seed = seed;
                world.groups = groups;
                world.agents = agents;
                Ok(WorldEvent {
                    ts: now,
                    kind: EventKind::CommandAck,
                    payload: serde_json::json!({
                        "command": "regenerate_roster",
                        "seed": seed,
                        "groups": friend_groups,
                        "solos": solos,
                        "friends_per_group": [friends_per_group_min, friends_per_group_max],
                    }),
                    severity: Severity::Notable,
                    operator_forced: true,
                })
            }
            Command::EditPersona { persona_id, edit } => {
                let agent = world
                    .agents
                    .iter_mut()
                    .find(|a| a.persona_id == persona_id)
                    .ok_or_else(|| CommandError::UnknownPersona(persona_id.clone()))?;
                agent.name.clone_from(&edit.name);
                agent.playstyle.clone_from(&edit.playstyle);
                agent.attitude.clone_from(&edit.attitude);
                agent.chattiness = edit.chattiness;
                agent.schedule.clone_from(&edit.schedule);
                Ok(WorldEvent {
                    ts: now,
                    kind: EventKind::CommandAck,
                    payload: serde_json::json!({
                        "command": "edit_persona",
                        "persona_id": persona_id,
                        "name": edit.name,
                    }),
                    severity: Severity::Notable,
                    operator_forced: true,
                })
            }
            Command::ForceAction {
                persona_id,
                action,
                arg,
            } => {
                let agent = world
                    .agents
                    .iter_mut()
                    .find(|a| a.persona_id == persona_id)
                    .ok_or_else(|| CommandError::UnknownPersona(persona_id.clone()))?;
                let extra: serde_json::Value = match action.as_str() {
                    "goal_change" => {
                        let goal = if arg.is_empty() {
                            GOALS[0].to_string()
                        } else {
                            arg.clone()
                        };
                        agent.goal.clone_from(&goal);
                        serde_json::json!({ "goal": goal })
                    }
                    "chat" => {
                        let text = if arg.is_empty() {
                            "hello world (forced)"
                        } else {
                            arg.as_str()
                        };
                        serde_json::json!({
                            "line": ChatLine {
                                at: now,
                                channel: "map".to_string(),
                                sender: agent.name.clone(),
                                text: text.to_string(),
                            }
                        })
                    }
                    "party_invite" => serde_json::json!({ "invite_target": arg, "accepted": true }),
                    "disconnect" => {
                        agent.online_override = Some(false);
                        agent.online = false;
                        serde_json::json!({ "override": "offline" })
                    }
                    "reconnect" => {
                        agent.online_override = Some(true);
                        agent.online = true;
                        serde_json::json!({ "override": "online" })
                    }
                    other => return Err(CommandError::Invalid(format!("unknown action: {other}"))),
                };
                let mut payload = serde_json::json!({
                    "command": "force_action",
                    "persona_id": persona_id,
                    "action": action,
                });
                if let (Some(obj), Some(extra_obj)) = (payload.as_object_mut(), extra.as_object()) {
                    for (k, v) in extra_obj {
                        obj.insert(k.clone(), v.clone());
                    }
                }
                Ok(WorldEvent {
                    ts: now,
                    kind: EventKind::CommandAck,
                    payload,
                    severity: Severity::Alarm,
                    operator_forced: true,
                })
            }
        }
    }
}

impl std::fmt::Debug for MockWorldFeed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MockWorldFeed").finish_non_exhaustive()
    }
}

#[cfg(test)]
mod tests;
