//! Bounded incremental parser for Python's numeric-ID SSE feed.
#![allow(missing_docs)]
use crate::wire;
use crate::{
    AgentDetail, Command, CommandError, FeedHealth, RosterSnapshot, WorldEvent, WorldFeed,
};
use serde::de::DeserializeOwned;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

/// All timeouts and cache retention are bounded; live never constructs mock state.
#[derive(Clone)]
pub struct LiveConfig {
    pub request_timeout: Duration,
    pub cache_ttl: Duration,
    pub poll_interval: Duration,
    pub reconnect_delay: Duration,
}
impl Default for LiveConfig {
    fn default() -> Self {
        Self {
            request_timeout: Duration::from_secs(3),
            cache_ttl: Duration::from_secs(10),
            poll_interval: Duration::from_secs(2),
            reconnect_delay: Duration::from_secs(1),
        }
    }
}
#[derive(Default)]
struct Cache {
    roster: Option<(Instant, RosterSnapshot)>,
    details: HashMap<String, (Instant, AgentDetail)>,
    error: Option<String>,
    cursor: Option<u64>,
    events_status: String,
    // Transport errors clear on reconnect; integrity flags are adapter-lifetime
    // facts and only an explicit adapter restart resets them with the cursor.
    events_error: Option<String>,
    replay_gap: bool,
    possible_restart: bool,
}

pub struct HttpWorldFeed {
    base: reqwest::Url,
    client: reqwest::Client,
    config: LiveConfig,
    cache: Mutex<Cache>,
    tx: tokio::sync::broadcast::Sender<WorldEvent>,
    event_lock: tokio::sync::Mutex<()>,
}
impl HttpWorldFeed {
    /// Construct a live-only adapter. HTTP URLs cannot contain credentials/query/fragment.
    /// # Errors
    /// Rejects invalid URLs and unbounded/zero configuration values.
    pub fn new(base: &str, config: LiveConfig) -> Result<Self, String> {
        let mut base = reqwest::Url::parse(base).map_err(|e| e.to_string())?;
        if !matches!(base.scheme(), "http" | "https")
            || !base.username().is_empty()
            || base.password().is_some()
            || base.query().is_some()
            || base.fragment().is_some()
        {
            return Err("invalid WorldFeed URL".into());
        }
        if [
            config.request_timeout,
            config.cache_ttl,
            config.poll_interval,
            config.reconnect_delay,
        ]
        .iter()
        .any(|d| d.is_zero() || *d > Duration::from_secs(60))
        {
            return Err("live durations must be >0 and <=60 seconds".into());
        }
        if !base.path().ends_with('/') {
            base.set_path(&format!("{}/", base.path()));
        }
        let client = reqwest::Client::builder()
            .connect_timeout(config.request_timeout)
            .read_timeout(Duration::from_secs(10))
            .redirect(reqwest::redirect::Policy::none())
            .no_proxy()
            .pool_max_idle_per_host(2)
            .build()
            .map_err(|e| e.to_string())?;
        let (tx, _) = tokio::sync::broadcast::channel(512);
        Ok(Self {
            base,
            client,
            config,
            cache: Mutex::new(Cache::default()),
            tx,
            event_lock: tokio::sync::Mutex::new(()),
        })
    }
    fn cache(&self) -> std::sync::MutexGuard<'_, Cache> {
        self.cache
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
    fn url(&self, path: &str) -> Result<reqwest::Url, String> {
        self.base.join(path).map_err(|e| e.to_string())
    }
    async fn decode<T: DeserializeOwned>(mut response: reqwest::Response) -> Result<T, String> {
        let status = response.status();
        if !status.is_success() {
            return Err(format!("upstream HTTP {status}"));
        }
        let mut body = Vec::new();
        while let Some(chunk) = response.chunk().await.map_err(|e| e.to_string())? {
            if body.len() + chunk.len() > 2_097_152 {
                return Err("HTTP body exceeds 2 MiB".into());
            }
            body.extend_from_slice(&chunk);
        }
        serde_json::from_slice(&body).map_err(|e| e.to_string())
    }
    async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T, String> {
        let response = self
            .client
            .get(self.url(path)?)
            .timeout(self.config.request_timeout)
            .send()
            .await
            .map_err(|e| e.to_string())?;
        Self::decode(response).await
    }
    /// Refresh the roster, retaining a stale last-good snapshot on error.
    /// # Errors
    /// Network, HTTP, size, JSON or roster-bound validation failure.
    pub async fn refresh(&self) -> Result<(), String> {
        let result = self.get::<wire::Roster>("feed/roster").await.and_then(|r| {
            if r.agents.len() > crate::MAX_ROSTER_AGENTS as usize {
                Err("roster exceeds 4096 agents".into())
            } else {
                Ok(r.translate())
            }
        });
        let mut cache = self.cache();
        match result {
            Ok(roster) => {
                cache
                    .details
                    .retain(|id, _| roster.agents.iter().any(|a| &a.persona_id == id));
                cache.roster = Some((Instant::now(), roster));
                cache.error = None;
                Ok(())
            }
            Err(e) => {
                cache.error = Some(e.clone());
                Err(e)
            }
        }
    }
    async fn detail(&self, id: &str) -> Result<Option<AgentDetail>, String> {
        {
            let cache = self.cache();
            if let Some((at, detail)) = cache.details.get(id) {
                if at.elapsed() < self.config.cache_ttl && cache.error.is_none() {
                    return Ok(Some(detail.clone()));
                }
            }
        }
        let mut url = self.url("feed/agent/")?;
        url.path_segments_mut()
            .map_err(|()| "invalid base URL")?
            .pop_if_empty()
            .push(id);
        let response = self
            .client
            .get(url)
            .timeout(self.config.request_timeout)
            .send()
            .await
            .map_err(|e| e.to_string())?;
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            self.cache().details.remove(id);
            return Ok(None);
        }
        let wire: wire::Agent = Self::decode(response).await?;
        if wire.persona_id != id {
            return Err("detail identity mismatch".into());
        }
        let mut cache = self.cache();
        let group = cache
            .roster
            .as_ref()
            .and_then(|(_, r)| r.agents.iter().find(|a| a.persona_id == id))
            .map(|a| a.group_id.as_str());
        let detail = wire.translate(group);
        if cache.details.len() >= 128 {
            if let Some(old) = cache
                .details
                .iter()
                .min_by_key(|(_, (at, _))| *at)
                .map(|(k, _)| k.clone())
            {
                cache.details.remove(&old);
            }
        }
        cache
            .details
            .insert(id.into(), (Instant::now(), detail.clone()));
        Ok(Some(detail))
    }
    /// Read one SSE connection and deliver only strictly newer IDs.
    /// # Errors
    /// Network, HTTP/content-type, timeout, framing, JSON failure.
    pub async fn consume_events_once(&self) -> Result<(), String> {
        let _guard = self.event_lock.lock().await;
        let result = self.consume().await;
        let mut cache = self.cache();
        cache.events_status = "disconnected".into();
        if let Err(e) = &result {
            cache.events_error = Some(e.clone());
        }
        result
    }
    async fn consume(&self) -> Result<(), String> {
        let mut request = self
            .client
            .get(self.url("feed/events")?)
            .header("accept", "text/event-stream")
            .timeout(Duration::from_secs(30));
        if let Some(id) = self.cache().cursor {
            request = request.header("last-event-id", id.to_string());
        }
        let mut response = request.send().await.map_err(|e| e.to_string())?;
        if !response.status().is_success() {
            return Err(format!("SSE HTTP {}", response.status()));
        }
        if response
            .headers()
            .get("content-type")
            .and_then(|h| h.to_str().ok())
            .is_none_or(|v| v.split(';').next() != Some("text/event-stream"))
        {
            return Err("expected text/event-stream".into());
        }
        {
            let mut c = self.cache();
            c.events_status = "connected".into();
            c.events_error = None;
        }
        let mut decoder = SseDecoder::default();
        while let Some(chunk) = response.chunk().await.map_err(|e| e.to_string())? {
            for (id, event) in decoder.push(&chunk)? {
                let mut cache = self.cache();
                if cache.cursor.is_some_and(|last| id <= last) {
                    cache.possible_restart = true;
                    continue;
                }
                if cache.cursor.is_some_and(|last| id > last.saturating_add(1)) {
                    cache.replay_gap = true;
                }
                let _ = self.tx.send(event.translate(Some(id)));
                cache.cursor = Some(id);
            }
        }
        Ok(())
    }
    /// Spawn bounded polling and reconnect loops. Caller owns abort handles.
    #[must_use]
    pub fn spawn(self: &Arc<Self>) -> Vec<tokio::task::JoinHandle<()>> {
        let poll = Arc::downgrade(self);
        let events = Arc::downgrade(self);
        vec![
            tokio::spawn(async move {
                while let Some(feed) = poll.upgrade() {
                    let _ = feed.refresh().await;
                    let delay = feed.config.poll_interval;
                    drop(feed);
                    tokio::time::sleep(delay).await;
                }
            }),
            tokio::spawn(async move {
                while let Some(feed) = events.upgrade() {
                    let _ = feed.consume_events_once().await;
                    let delay = feed.config.reconnect_delay;
                    drop(feed);
                    tokio::time::sleep(delay).await;
                }
            }),
        ]
    }
    async fn post_command(&self, cmd: Command) -> Result<WorldEvent, CommandError> {
        let payload = command_payload(&cmd)?;
        let url = self
            .url("commands")
            .map_err(|_| CommandError::Unavailable)?;
        let response = self
            .client
            .post(url)
            .json(&payload)
            .timeout(self.config.request_timeout)
            .send()
            .await
            .map_err(|_| CommandError::Unavailable)?;
        let status = response.status();
        if status == reqwest::StatusCode::NOT_FOUND {
            return Err(CommandError::UnknownPersona(
                payload
                    .get("persona_id")
                    .and_then(serde_json::Value::as_str)
                    .unwrap_or("not supplied")
                    .into(),
            ));
        }
        if status.is_client_error() {
            return Err(CommandError::Invalid(format!(
                "Python rejected command: HTTP {status}"
            )));
        }
        let wire: wire::Event = Self::decode(response)
            .await
            .map_err(|_| CommandError::Unavailable)?;
        let mut event = wire.translate(None);
        if let Some(payload) = event.payload.as_object_mut() {
            payload.insert(
                "execution".into(),
                serde_json::json!("not verified; WorldState only"),
            );
        }
        {
            self.cache().details.clear();
        }
        let _ = self.refresh().await;
        Ok(event)
    }
}
/// Translate supported commands without silently dropping requested schedule edits.
/// # Errors
/// Force actions have no host executor; schedule-bearing edits cannot be atomic.
pub fn command_payload(cmd: &Command) -> Result<serde_json::Value, CommandError> {
    cmd.validate()?;
    match cmd {
        Command::RegenerateRoster {
            seed,
            friend_groups,
            solos,
            friends_per_group_min,
            friends_per_group_max,
        } => Ok(
            serde_json::json!({"type":"regenerate_roster","seed":seed,"groups":friend_groups,"solos":solos,"friends_min":friends_per_group_min,"friends_max":friends_per_group_max}),
        ),
        Command::EditPersona { persona_id, edit } => {
            if !edit.schedule.is_empty() {
                return Err(CommandError::Invalid(
                    "schedule edits not supported by atomic Python edit_persona".into(),
                ));
            }
            Ok(
                serde_json::json!({"type":"edit_persona","persona_id":persona_id,"name":edit.name,"playstyle":edit.playstyle,"attitude":edit.attitude,"chattiness":edit.chattiness}),
            )
        }
        Command::ForceAction { .. } => Err(CommandError::Invalid(
            "force_action is unsupported: Python records notes only; no host execution".into(),
        )),
    }
}
impl WorldFeed for HttpWorldFeed {
    fn health(&self) -> FeedHealth {
        let c = self.cache();
        let age = c.roster.as_ref().map(|(t, _)| t.elapsed());
        // Preserve the existing health JSON warning field without letting a
        // transient error overwrite either independently retained integrity fact.
        let mut warnings = Vec::new();
        if c.replay_gap {
            warnings.push("upstream replay gap; evicted events cannot be recovered");
        }
        if c.possible_restart {
            warnings.push("upstream replayed old IDs; possible process restart; cursor not reset automatically");
        }
        if let Some(error) = &c.events_error {
            warnings.push(error);
        }
        FeedHealth {
            mode: "live".into(),
            status: if age.is_none() {
                "unavailable"
            } else if c.error.is_some()
                || age.is_some_and(|a| a > self.config.cache_ttl)
                || c.events_status != "connected"
                || c.events_error.is_some()
                || c.replay_gap
                || c.possible_restart
            {
                "stale"
            } else {
                "available"
            }
            .into(),
            error: c.error.clone(),
            snapshot_age_secs: age.map(|a| a.as_secs()),
            last_event_id: c.cursor,
            events_status: if c.events_status.is_empty() {
                "not connected".into()
            } else {
                c.events_status.clone()
            },
            events_error: (!warnings.is_empty()).then(|| warnings.join("; ")),
        }
    }
    fn roster(&self) -> RosterSnapshot {
        self.cache().roster.as_ref().map_or_else(
            || RosterSnapshot {
                seed: None,
                groups: Vec::new(),
                agents: Vec::new(),
            },
            |(_, r)| r.clone(),
        )
    }
    fn agent_detail(&self, id: &str) -> Option<AgentDetail> {
        self.cache()
            .details
            .get(id)
            .filter(|(t, _)| t.elapsed() < self.config.cache_ttl)
            .map(|(_, d)| d.clone())
    }
    fn fetch_agent<'a>(
        &'a self,
        id: &'a str,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<Option<AgentDetail>, String>> + Send + 'a>,
    > {
        Box::pin(self.detail(id))
    }
    fn subscribe(&self) -> tokio_stream::wrappers::BroadcastStream<WorldEvent> {
        tokio_stream::wrappers::BroadcastStream::new(self.tx.subscribe())
    }
    fn apply_command(&self, _: Command) -> Result<WorldEvent, CommandError> {
        Err(CommandError::Unavailable)
    }
    fn send_command(
        &self,
        cmd: Command,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<WorldEvent, CommandError>> + Send + '_>,
    > {
        Box::pin(self.post_command(cmd))
    }
}

/// Framing survives arbitrary TCP chunks; incomplete frames are never delivered.
#[derive(Default)]
pub struct SseDecoder {
    buffer: Vec<u8>,
    id: Option<u64>,
    data: String,
    frame_size: usize,
}
impl SseDecoder {
    /// Decode complete events; reject oversized frames, invalid UTF-8/JSON/IDs.
    /// # Errors
    /// Returns a descriptive protocol error without advancing a cursor.
    pub fn push(&mut self, bytes: &[u8]) -> Result<Vec<(u64, wire::Event)>, String> {
        let mut events = Vec::new();
        for byte in bytes {
            self.frame_size += 1;
            if self.frame_size > 131_072 {
                return Err("SSE frame exceeds 128 KiB".into());
            }
            if *byte != b'\n' {
                self.buffer.push(*byte);
                continue;
            }
            let line =
                String::from_utf8(std::mem::take(&mut self.buffer)).map_err(|e| e.to_string())?;
            let line = line.strip_suffix('\r').unwrap_or(&line);
            if line.is_empty() {
                if !self.data.is_empty() {
                    let id = self.id.ok_or("SSE event missing numeric id")?;
                    let event = serde_json::from_str(&self.data).map_err(|e| e.to_string())?;
                    events.push((id, event));
                }
                self.id = None;
                self.data.clear();
                self.frame_size = 0;
            } else if let Some((field, value)) = line.split_once(':') {
                let value = value.strip_prefix(' ').unwrap_or(value);
                match field {
                    "id" => self.id = Some(value.parse().map_err(|_| "invalid SSE id")?),
                    "data" => {
                        if !self.data.is_empty() {
                            self.data.push('\n');
                        }
                        self.data.push_str(value);
                    }
                    _ => {}
                }
            }
        }
        Ok(events)
    }
}
