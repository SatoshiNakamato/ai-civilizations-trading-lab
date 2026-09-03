from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from civilizations import Civilization

app = FastAPI(title="AI Civilizations Trading Lab")
civilization = Civilization(size=100, seed=42)

HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Civilizations</title>
<style>
body{font-family:system-ui;margin:0;padding:20px;max-width:1000px;margin:auto}
.card{border:1px solid #ddd;border-radius:12px;padding:16px;margin:12px 0}
button{padding:10px 16px;border-radius:8px;border:1px solid #aaa;background:white}
pre{white-space:pre-wrap;overflow:auto}
</style>
</head>
<body>
<h1>AI Civilization</h1>
<p>100 simulated market researchers evolving through bounded idea exchange.</p>
<button onclick="step()">Run one generation</button>
<div class="card"><h2>State</h2><pre id="state">Loading...</pre></div>
<script>
async function refresh(){
 const r=await fetch('/state');
 document.getElementById('state').textContent=JSON.stringify(await r.json(),null,2);
}
async function step(){await fetch('/step',{method:'POST'}); await refresh();}
refresh();
</script>
</body>
</html>
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
