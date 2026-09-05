from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from civilizations import Civilization

app = FastAPI(title="AEON — Emergent AI Civilization")
civilization = Civilization(size=100, seed=42)

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEON — Emergent AI Civilization</title>
<style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% 0,#102a42 0,#050a12 42%,#02050a 100%);color:#e8f7ff}main{max-width:1250px;margin:auto;padding:28px}.hero{padding:34px;border:1px solid #2a7896;border-radius:28px;background:linear-gradient(135deg,#102536cc,#07111bcc);box-shadow:0 0 60px #008ac733}.eyebrow{letter-spacing:.2em;font-size:12px;color:#6ee7ff}.hero h1{font-size:clamp(40px,8vw,82px);margin:8px 0;background:linear-gradient(90deg,#dffaff,#63dcff,#9e8cff);-webkit-background-clip:text;color:transparent}.hero p{max-width:760px;color:#a9c5d4;font-size:18px;line-height:1.6}.actions{display:flex;gap:12px;flex-wrap:wrap}.button{cursor:pointer;border:1px solid #3eb8d8;background:#0b2332cc;color:#dffaff;border-radius:14px;padding:12px 18px;font-weight:700}.button:hover{box-shadow:0 0 25px #16b9e944}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:18px}.card{border:1px solid #24526a;border-radius:20px;background:#081521cc;padding:18px;backdrop-filter:blur(12px)}.label{color:#7898aa;font-size:12px;text-transform:uppercase;letter-spacing:.12em}.value{font-size:30px;font-weight:800;margin-top:6px}.wide{margin-top:18px}.columns{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}.list{display:grid;gap:9px;margin-top:12px}.row{padding:12px;border:1px solid #18384a;border-radius:13px;background:#06111a}.muted{color:#86a5b5;font-size:13px}.pulse{display:inline-block;width:9px;height:9px;border-radius:50%;background:#6ee7ff;box-shadow:0 0 14px #6ee7ff;margin-right:8px}pre{white-space:pre-wrap;overflow:auto;color:#9fdcf0;font-size:12px;max-height:400px}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.columns{grid-template-columns:1fr}}@media(max-width:520px){main{padding:14px}.grid{grid-template-columns:1fr 1fr}.value{font-size:22px}}
</style>
</head>
<body><main>
<section class="hero"><div class="eyebrow">AEON / ARTIFICIAL EVOLUTIONARY ORGANIZATIONAL NETWORK</div><h1>Don't build agents.<br>Build the world.</h1><p>100 specialized market intelligences form organizations, exchange bounded strategy memes, challenge evidence, accumulate social capital and evolve inside a controlled digital civilization.</p><div class="actions"><button class="button" onclick="step()">▶ Advance civilization</button><button class="button" onclick="run(5)">⚡ Run 5 generations</button></div></section>
<div class="grid" id="metrics"></div>
<section class="columns wide"><div class="card"><div class="label">Emergent strategy memes</div><div id="memes" class="list"></div></div><div class="card"><div class="label">Organizations</div><div id="orgs" class="list"></div></div></section>
<section class="card wide"><div class="label">Civilization event stream</div><div id="events" class="list"></div></section>
<section class="card wide"><div class="label">Raw state / API</div><pre id="state">Loading...</pre></section>
</main>
<script>
async function refresh(){const r=await fetch('/state');const s=await r.json();const e=s.emergence||{};document.getElementById('metrics').innerHTML=[['Generation',s.generation],['Population',s.agents],['Strategy memes',e.memes||0],['Organizations',e.organizations||0],['Discovery',e.discovery_points||0],['Innovation',e.innovation_points||0],['Social capital',e.social_capital||0],['Ideas',s.ideas]].map(x=>`<div class="card"><div class="label">${x[0]}</div><div class="value">${x[1]}</div></div>`).join('');document.getElementById('memes').innerHTML=(e.top_memes||[]).slice(0,7).map(m=>`<div class="row"><b>${m.name}</b><div class="muted">${m.thesis.slice(0,150)}</div><div class="muted">fitness ${Number(m.fitness).toFixed(3)} · carriers ${m.carriers} · mutations ${m.mutations}</div></div>`).join('')||'<div class="muted">No memes yet.</div>';document.getElementById('orgs').innerHTML=(e.organizations_state||[]).slice(-7).reverse().map(o=>`<div class="row"><b>${o.name}</b><div class="muted">mission: ${o.mission}</div><div class="muted">${o.members.length} members · treasury ${Number(o.treasury).toFixed(1)} · influence ${Number(o.influence).toFixed(2)}</div></div>`).join('')||'<div class="muted">Organizations emerge after the first cycle.</div>';document.getElementById('events').innerHTML=(e.events||[]).slice(-12).reverse().map(x=>`<div class="row"><span class="pulse"></span><b>${x.event}</b> <span class="muted">tick ${x.tick} · actor ${x.actor} · ${x.object}</span></div>`).join('');document.getElementById('state').textContent=JSON.stringify(s,null,2)}
async function step(){await fetch('/step',{method:'POST'});await refresh()}async function run(n){for(let i=0;i<n;i++){await step()}}refresh();
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML

@app.get("/state")
def state():
    return civilization.snapshot()

@app.post("/step")
def step():
    return civilization.step()
