//! Server-rendered HTML for the static pages (roster, configurator, feed,
//! agent inspector). The `LiveView` at `/live` is the auto-updating surface;
//! these pages poll `/api/roster` / `/api/events` via a tiny inline script.

use std::fmt::Write as _;

use world_feed::{AgentDetail, ChatLine, RosterSnapshot};

/// Escape text for safe HTML interpolation.
pub fn esc(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn attitude_label(attitude: &str) -> String {
    attitude.replace('_', " ")
}

fn online_badge(online: bool) -> &'static str {
    if online {
        "<span class=\"badge on\">online</span>"
    } else {
        "<span class=\"badge off\">offline</span>"
    }
}

/// Roster page: agent cards grouped by friend group.
#[must_use]
pub fn index_page_html(roster: &RosterSnapshot) -> String {
    let mut out = String::new();
    let _ = write!(
        out,
        "<h1>ro-bots roster</h1><p class=\"seed\">seed: {} \
         (<a href=\"/config\">configurator</a>)</p>",
        roster.seed
    );
    for group in &roster.groups {
        let _ = write!(
            out,
            "<section class=\"group\"><h2>{} <span class=\"attitude\">{}</span></h2>",
            esc(&group.group_id),
            attitude_label(&group.attitude)
        );
        for agent in &roster.agents {
            if agent.group_id != group.group_id {
                continue;
            }
            let _ = write!(
                out,
                "<a class=\"card\" href=\"/agent/{}\">{} <b>{}</b> <i>{}</i> {}</a>",
                esc(&agent.persona_id),
                online_badge(agent.online),
                esc(&agent.name),
                esc(&agent.playstyle),
                format_args!(
                    "<span class=\"attitude\">{}</span>",
                    attitude_label(&agent.attitude)
                ),
            );
        }
        out.push_str("</section>");
    }
    out.push_str(
        "<p><a href=\"/feed\">live feed</a> | <a href=\"/live\">liveview</a> | \
         <a href=\"/api/roster\">/api/roster</a> | <a href=\"/api/events\">/api/events (SSE)</a></p>",
    );
    shell("roster", &out)
}

/// Configurator page (ADR-008): roster generation form.
#[must_use]
pub fn configurator_html(current_seed: u64) -> String {
    let body = format!(
        "<h1>configurator</h1>\
         <p class=\"seed\">current seed: <b id=\"seed\">{current_seed}</b></p>\
         <form id=\"gen-form\">\
         <label>agent seed <input type=\"number\" name=\"seed\" id=\"f-seed\" value=\"{current_seed}\" min=\"0\"></label>\
         <label>friend groups <input type=\"number\" name=\"friend_groups\" id=\"f-groups\" value=\"3\" min=\"0\"></label>\
         <label>solos <input type=\"number\" name=\"solos\" id=\"f-solos\" value=\"1\" min=\"0\"></label>\
         <label>friends per group min <input type=\"number\" name=\"friends_per_group_min\" id=\"f-min\" value=\"2\" min=\"1\"></label>\
         <label>friends per group max <input type=\"number\" name=\"friends_per_group_max\" id=\"f-max\" value=\"4\" min=\"1\"></label>\
         <button type=\"submit\">Generate</button>\
         </form>\
         <pre id=\"gen-result\"></pre>\
         <script>\
         document.getElementById('gen-form').addEventListener('submit', async (e) => {{\
           e.preventDefault();\
           const body = {{type: 'regenerate_roster',\
             seed: Number(document.getElementById('f-seed').value),\
             friend_groups: Number(document.getElementById('f-groups').value),\
             solos: Number(document.getElementById('f-solos').value),\
             friends_per_group_min: Number(document.getElementById('f-min').value),\
             friends_per_group_max: Number(document.getElementById('f-max').value)}};\
           const r = await fetch('/commands', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body)}});\
           document.getElementById('gen-result').textContent = await r.text();\
           if (r.ok) {{ document.getElementById('seed').textContent = body.seed; }}\
         }});\
         </script>\
         <p><a href=\"/\">back to roster</a> (regenerate, then reload it)</p>"
    );
    shell("configurator", &body)
}

/// Live feed page: recent chat + SSE event stream, MMO-chat styled.
#[must_use]
pub fn feed_page_html(recent: &[ChatLine]) -> String {
    let mut out = String::from("<h1>live feed</h1><ul id=\"chat\" class=\"chat\">");
    for line in recent {
        let _ = write!(
            out,
            "<li><span class=\"at\">[{}</span>] &lt;<b>{}</b>&gt; {}</li>",
            format_args!("{:.0}", line.at),
            esc(&line.sender),
            esc(&line.text)
        );
    }
    out.push_str("</ul><ul id=\"events\"></ul><script>");
    out.push_str(
        "const es = new EventSource('/api/events');\n\
         const chat = document.getElementById('chat');\n\
         const evl = document.getElementById('events');\n\
         es.onmessage = (m) => {\n\
         const ev = JSON.parse(m.data);\n\
         if (ev.kind === 'chat') {\n\
         const li = document.createElement('li');\n\
         const l = ev.payload.line;\n\
         li.innerHTML = `<span class=\"at\">[${Math.floor(l.at)}]</span> &lt;<b>${l.sender}</b>&gt; ${l.text}`;\n\
         chat.appendChild(li); if (chat.children.length > 100) chat.firstChild.remove();\n\
         } else {\n\
         const li = document.createElement('li');\n\
         li.className = ev.operator_forced ? 'forced' : (ev.severity === 'alarm' ? 'alarm' : '');\n\
         li.textContent = `[${Math.floor(ev.ts)}] ${ev.kind} ${ev.operator_forced ? '(operator-forced)' : ''} ${JSON.stringify(ev.payload)}`;\n\
         evl.prepend(li); if (evl.children.length > 100) evl.lastChild.remove();\n\
         }\n\
         };",
    );
    out.push_str("</script><p><a href=\"/\">back to roster</a></p>");
    shell("live feed", &out)
}

/// Agent inspector page: persona, goals, memory view (`OptChat` L-level
/// prefixes), reputation ledger, characters, schedule, edit form, force
/// buttons, related events.
#[must_use]
#[allow(clippy::too_many_lines)] // one section per inspector block; splitting scatters the HTML
pub fn agent_page_html(detail: &AgentDetail) -> String {
    let mut out = String::new();
    let _ = write!(
        out,
        "<h1>{} {} <span class=\"attitude\">{}</span></h1>\
         <p>group <a href=\"/\">{}</a> | chattiness {:.2} | level band {}..{}</p>",
        online_badge(detail.online),
        esc(&detail.name),
        attitude_label(&detail.attitude),
        esc(&detail.group_id),
        detail.chattiness,
        detail.level_band.0,
        detail.level_band.1
    );

    let _ = write!(
        out,
        "<h2>current</h2><ul>\
         <li><b>goal:</b> {}</li><li><b>script:</b> {}</li><li><b>plan:</b> {}</li>\
         <li><b>personal goal:</b> {}</li><li><b>group goal:</b> {}</li><li><b>guild goal:</b> {}</li></ul>",
        esc(&detail.current_goal),
        esc(&detail.current_script),
        esc(&detail.current_plan),
        esc(&detail.personal_goal),
        esc(&detail.group_goal),
        if detail.guild_goal.is_empty() { "<i>none</i>" } else { &detail.guild_goal }
    );

    out.push_str("<h2>memory view (OptChat)</h2><ul class=\"memory\">");
    for line in &detail.memory_view {
        let _ = write!(
            out,
            "<li class=\"l{}\"><b>L{}:{}</b> {}</li>",
            line.level,
            line.level,
            line.index,
            esc(&line.summary)
        );
    }
    out.push_str("</ul>");

    out.push_str("<h2>reputation ledger</h2><table><tr><th>human</th><th>score</th><th>last reason</th></tr>");
    for entry in &detail.reputation {
        // score is in -1..=1, so the percentage is in 0..=100 and rounds to
        // an exact i32; no truncation possible.
        #[allow(clippy::cast_possible_truncation)]
        let pct = f64::midpoint(entry.score, 1.0).mul_add(100.0, 0.0).round() as i32;
        let _ = write!(
            out,
            "<tr><td>{}</td><td><div class=\"bar\"><div class=\"fill\" style=\"width:{}%\"></div></div> {:.2}</td><td>{}</td></tr>",
            esc(&entry.human),
            pct,
            entry.score,
            esc(&entry.last_reason)
        );
    }
    out.push_str("</table>");

    out.push_str("<h2>characters</h2><ul>");
    for c in &detail.characters {
        let _ = write!(
            out,
            "<li><b>{}</b> (lvl {}) — {} <br><small>{}</small></li>",
            esc(&c.name),
            c.level,
            esc(&c.class_path),
            esc(&c.build_summary)
        );
    }
    out.push_str("</ul>");

    out.push_str("<h2>schedule</h2><ul class=\"schedule\">");
    // Named constant here keeps the weekday table next to its only user.
    #[allow(clippy::items_after_statements)]
    const DAYS: [&str; 7] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    for w in &detail.schedule {
        // `w.day` is a 0..7 weekday (ScheduleWindow invariant); `.min(6)`
        // clamps any stray value, so the index is always in bounds.
        #[allow(clippy::indexing_slicing)]
        let day_name = DAYS[usize::from(w.day.min(6))];
        let _ = write!(
            out,
            "<li>{} {:05.2}:00–{:05.2}:00</li>",
            day_name, w.start, w.end
        );
    }
    out.push_str("</ul>");

    // Related events for this agent (filter the shared stream by persona
    // mention in the payload — the MVP has no per-agent stream).
    out.push_str("<h2>related events</h2><ul id=\"agent-events\"></ul><script>");
    let _ = write!(out, "const pid = '{}';", esc(&detail.persona_id));
    out.push_str(
        "const ul = document.getElementById('agent-events');\n\
         const es = new EventSource('/api/events');\n\
         es.onmessage = (m) => { const ev = JSON.parse(m.data);\n\
         const s = JSON.stringify(ev.payload);\n\
         if (s.includes(pid)) { const li = document.createElement('li');\n\
         li.textContent = `[${Math.floor(ev.ts)}] ${ev.kind}${ev.operator_forced ? ' (operator-forced)' : ''} ${s}`;\n\
         ul.prepend(li); if (ul.children.length > 30) ul.lastChild.remove(); } };",
    );
    out.push_str("</script>");

    // Persona edit form (ADR-008 #2).
    let schedule_json = serde_json::to_string(&detail.schedule).unwrap_or_else(|_| "[]".into());
    let _ = write!(
        out,
        "<h2>edit persona</h2>\
         <form id=\"edit-form\">\
         <label>name <input id=\"e-name\" value=\"{}\"></label>\
         <label>playstyle <select id=\"e-style\">{}</select></label>\
         <label>attitude <select id=\"e-attitude\">{}</select></label>\
         <label>chattiness <input type=\"number\" id=\"e-chat\" min=\"0\" max=\"1\" step=\"0.05\" value=\"{:.2}\"></label>\
         <label>schedule windows (JSON) <textarea id=\"e-sched\" rows=\"3\">{}</textarea></label>\
         <button type=\"submit\">Save</button> <span id=\"edit-result\"></span>\
         </form>",
        esc(&detail.name),
        options(&["tank", "healer", "mage", "hunter", "support", "melee"], &detail.playstyle),
        options(
            &["helpful_newbie", "clique", "event_focused", "grinder", "solo"],
            &detail.attitude
        ),
        detail.chattiness,
        esc(&schedule_json)
    );
    out.push_str(
        "<script>\
         document.getElementById('edit-form').addEventListener('submit', async (e) => {\
         e.preventDefault();\
         let sched;\n\
         try { sched = JSON.parse(document.getElementById('e-sched').value); }\
         catch { document.getElementById('edit-result').textContent = 'bad schedule JSON'; return; }\
         const body = {type: 'edit_persona', persona_id: pid, edit: {\
         name: document.getElementById('e-name').value,\
         playstyle: document.getElementById('e-style').value,\
         attitude: document.getElementById('e-attitude').value,\
         chattiness: Number(document.getElementById('e-chat').value),\
         schedule: sched}};\
         const r = await fetch('/commands', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});\
         document.getElementById('edit-result').textContent = r.ok ? 'saved' : await r.text(); });\
         </script>",
    );

    // Force-action buttons (ADR-008 #3).
    out.push_str("<h2>force actions</h2><div class=\"force\">");
    for (action, label) in [
        ("goal_change", "force goal change"),
        ("chat", "force chat"),
        ("party_invite", "force party invite"),
        ("disconnect", "force disconnect"),
        ("reconnect", "force reconnect"),
    ] {
        let _ = write!(out, "<button data-action=\"{action}\">{label}</button>");
    }
    let _ = write!(
        out,
        "</div><input id=\"force-arg\" placeholder=\"arg (chat text / target)\"><script>\
         document.querySelectorAll('.force button').forEach(b => b.addEventListener('click', async () => {{\
         const body = {{type: 'force_action', persona_id: pid, action: b.dataset.action, arg: document.getElementById('force-arg').value}};\
         const r = await fetch('/commands', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body)}});\
         document.getElementById('edit-result').textContent = r.ok ? 'forced' : await r.text(); }}));\
         </script><p><a href=\"/\">back to roster</a></p>"
    );
    shell(&detail.name, &out)
}

fn options(values: &[&str], selected: &str) -> String {
    values
        .iter()
        .map(|v| {
            if *v == selected {
                format!("<option selected>{v}</option>")
            } else {
                format!("<option>{v}</option>")
            }
        })
        .collect()
}

/// Wrap page body in the shared HTML shell.
fn shell(title: &str, body: &str) -> String {
    format!(
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">\
         <title>ro-bots · {title}</title>\
         <link rel=\"stylesheet\" href=\"/static/style.css\"></head>\
         <body><nav><a href=\"/\">roster</a> <a href=\"/config\">config</a> \
         <a href=\"/feed\">feed</a> <a href=\"/live\">liveview</a></nav>\
         <main>{body}</main></body></html>"
    )
}
