//! Dioxus `LiveView` component: auto-updating roster + live event stream.
//!
//! The component subscribes to the `WorldFeed` broadcast channel and updates
//! its signals per event, so the page refreshes without hand-written JS.

use dioxus::prelude::*;
use futures_util::StreamExt;
use world_feed::{EventKind, WorldEvent};

use crate::AppState;

/// Per-connection `LiveView` root: provides the app state and renders the feed.
#[component]
fn LiveViewRoot(state: AppState) -> Element {
    let mut roster = use_signal(|| state.feed.roster());
    let mut events: Signal<Vec<WorldEvent>> = use_signal(Vec::new);

    use_future(move || {
        let feed = state.feed.clone();
        async move {
            let mut stream = feed.subscribe();
            loop {
                match stream.next().await {
                    Some(Ok(ev)) => {
                        events.with_mut(|v: &mut Vec<WorldEvent>| {
                            v.insert(0, ev.clone());
                            v.truncate(80);
                        });
                        if matches!(
                            ev.kind,
                            EventKind::Online | EventKind::Offline | EventKind::CommandAck
                        ) {
                            roster.set(feed.roster());
                        }
                    }
                    // Lagged receivers simply skip missed events.
                    Some(Err(
                        tokio_stream::wrappers::errors::BroadcastStreamRecvError::Lagged(_),
                    )) => {}
                    None => break,
                }
            }
        }
    });

    let snapshot = roster();
    let event_rows: Vec<(String, String, String)> = events()
        .iter()
        .take(40)
        .map(|ev| {
            (
                format!("{:.0}-{:?}", ev.ts, ev.kind),
                event_class(ev).to_string(),
                format!(
                    "[{:.0}] {}{} {}",
                    ev.ts,
                    kind_label(ev.kind),
                    if ev.operator_forced {
                        " (operator-forced)"
                    } else {
                        ""
                    },
                    ev.payload
                ),
            )
        })
        .collect();
    rsx! {
        h1 { "ro-bots liveview" }
        p { class: "seed", "seed: {snapshot.seed}" }
        div {
            for group in snapshot.groups.iter() {
                section {
                    key: "{group.group_id}",
                    class: "group",
                    h2 { "{group.group_id} " span { class: "attitude", "{group.attitude}" } }
                    div {
                        for agent in snapshot.agents.iter().filter(|a| a.group_id == group.group_id) {
                            div {
                                key: "{agent.persona_id}",
                                class: "card",
                                span {
                                    class: if agent.online { "badge on" } else { "badge off" },
                                    if agent.online { "online" } else { "offline" }
                                }
                                b { "{agent.name}" }
                                i { "{agent.playstyle}" }
                            }
                        }
                    }
                }
            }
        }
        h2 { "events" }
        ul {
            class: "chat",
            for (ev_key, ev_class, display_text) in event_rows.iter() {
                li {
                    key: "{ev_key}",
                    class: "{ev_class}",
                    "{display_text}",
                }
            }
        }
    }
}

fn event_class(ev: &WorldEvent) -> &'static str {
    if ev.operator_forced {
        "forced"
    } else {
        match ev.severity {
            world_feed::Severity::Alarm => "alarm",
            world_feed::Severity::Notable => "notable",
            world_feed::Severity::Info => "",
        }
    }
}

fn kind_label(kind: EventKind) -> &'static str {
    match kind {
        EventKind::Chat => "chat",
        EventKind::Online => "online",
        EventKind::Offline => "offline",
        EventKind::GoalChange => "goal-change",
        EventKind::PartyInvite => "party-invite",
        EventKind::Reputation => "reputation",
        EventKind::Wipe => "wipe",
        EventKind::CommandAck => "command",
    }
}

/// HTML shell for `/live`: loads the Dioxus interpreter and connects the
/// websocket to `/live/ws`.
///
/// NOTE: we deliberately do NOT use `LiveviewRouter::with_virtual_dom` here:
/// it panics at router-construction time for nested routes (it builds a
/// `ws_path` without a leading slash), and panics are forbidden. Manual
/// wiring over `LiveViewPool` uses the identical wire protocol.
#[must_use]
pub fn liveview_shell_html() -> String {
    format!(
        "<!DOCTYPE html><html><head><title>ro-bots liveview</title>\
         <link rel=\"stylesheet\" href=\"/static/style.css\"></head>\
         <body><nav><a href=\"/\">roster</a> <a href=\"/config\">config</a> \
         <a href=\"/feed\">feed</a></nav><div id=\"main\"></div>{}</body></html>",
        dioxus_liveview::interpreter_glue("/live/ws")
    )
}

/// Per-connection upgrade handler: run the `LiveView` `VirtualDom` on the socket.
///
/// NOTE: `dioxus_liveview`'s `LiveviewRouter::with_virtual_dom` panics on
/// route construction ("Paths must start with a /" for the generated catch-all
/// `"{*route}"`), so we wire the websocket manually via `LiveViewPool` —
/// same wire protocol, no panic risk in `build_router`.
pub async fn launch_socket(socket: axum::extract::ws::WebSocket, state: AppState) {
    let view = dioxus_liveview::LiveViewPool::new();
    let _ = view
        .launch_virtualdom(dioxus_liveview::axum_socket(socket), move || {
            dioxus::prelude::VirtualDom::new_with_props(
                LiveViewRoot,
                LiveViewRootProps {
                    state: state.clone(),
                },
            )
        })
        .await;
}
