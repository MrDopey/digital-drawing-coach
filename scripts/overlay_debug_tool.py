#!/usr/bin/env python3
"""Local web app for debugging overlay-mode annotation coordinates: sends a
chosen image and an editable prompt (pre-filled with the app's real overlay
prompt) straight to the LLM, and renders the response under several
coordinate hypotheses (see drawing_coach.overlay_debug_lib)."""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import litellm
from PIL import Image

from drawing_coach import paths
from drawing_coach.config_manager import ConfigManager
from drawing_coach.llm_config import LLMConfig
from drawing_coach.llm_debug_log import DebugIOLogger
from drawing_coach.overlay_debug_runner import (
    DEFAULT_SCHEMA,
    DEFAULT_SYSTEM_PROMPT,
    run_debug_request,
)


def _run_request(config: LLMConfig, payload: dict) -> dict:
    try:
        image = Image.open(io.BytesIO(base64.b64decode(payload["image_b64"])))
        image = image.convert("RGB")
    except Exception as exc:
        return {"ok": False, "error": f"Could not decode image: {exc}"}

    schema_text = payload.get("schema_json")
    if schema_text:
        try:
            response_format = json.loads(schema_text)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"Schema is not valid JSON: {exc}"}
    else:
        response_format = None

    character_bbox = payload.get("character_bbox")
    if character_bbox is not None:
        character_bbox = tuple(int(round(v)) for v in character_bbox)

    return run_debug_request(
        config,
        image,
        system_prompt=payload.get("system_prompt") or None,
        response_format=response_format,
        character_bbox=character_bbox,
    )


def _make_handler(config: LLMConfig):
    default_prompt_json = json.dumps(DEFAULT_SYSTEM_PROMPT).replace("</", "<\\/")
    default_schema_text = json.dumps(DEFAULT_SCHEMA, indent=2)
    default_schema_json = json.dumps(default_schema_text).replace("</", "<\\/")
    model_json = json.dumps(config.model)
    page = (
        INDEX_HTML.replace("__DEFAULT_PROMPT_JSON__", default_prompt_json)
        .replace("__DEFAULT_SCHEMA_JSON__", default_schema_json)
        .replace("__MODEL_JSON__", model_json)
    )
    page_bytes = page.encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:  # quiet the default access log
            pass

        def do_GET(self) -> None:
            if self.path != "/":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page_bytes)))
            self.end_headers()
            self.wfile.write(page_bytes)

        def do_POST(self) -> None:
            if self.path != "/api/run":
                self.send_response(404)
                self.end_headers()
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length))
                result = _run_request(config, payload)
            except Exception as exc:
                result = {"ok": False, "error": f"Server error: {exc}"}
            body = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


INDEX_HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Overlay Debug Tool</title>
<style>
  :root {
    --bg: #f4f5f7; --panel: #ffffff; --border: #dde1e8; --text: #14161c;
    --muted: #5b6270; --mono-bg: #eceef2; --stage-bg: #1b1d22;
    --danger: #c22; --danger-bg: #fde8e8; --warn: #92620a; --warn-bg: #fdf3d8;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1115; --panel: #171a21; --border: #262b36; --text: #e8eaf0;
      --muted: #8b93a6; --mono-bg: #1d2029; --stage-bg: #0b0c10;
      --danger: #f87171; --danger-bg: #2a1518; --warn: #eab308; --warn-bg: #2a2410;
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
  code, pre, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .page { max-width: 1520px; margin: 0 auto; padding: 24px; }
  header h1 { font-size: 20px; margin: 0 0 6px; }
  header p { margin: 0; color: var(--muted); font-size: 13px; max-width: 76ch; line-height: 1.5; }
  .layout { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(300px, 1fr);
    gap: 20px; margin-top: 20px; align-items: start; }
  @media (max-width: 980px) { .layout { grid-template-columns: 1fr; } }
  .stage-wrap { background: var(--stage-bg); border: 1px solid var(--border);
    border-radius: 10px; padding: 10px; position: sticky; top: 16px; min-height: 200px; }
  @media (max-width: 980px) { .stage-wrap { position: static; } }
  .stage { position: relative; width: 100%; line-height: 0; border-radius: 4px; overflow: hidden; }
  .stage img { display: block; width: 100%; height: auto; }
  .stage svg { position: absolute; inset: 0; width: 100%; height: 100%; }
  .drawlayer { position: absolute; inset: 0; cursor: crosshair; }
  .placeholder { color: var(--muted); font-size: 13px; padding: 60px 20px; text-align: center; }
  .drawrect { position: absolute; border: 2px dashed #818cf8; background: rgba(129,140,248,0.12); pointer-events: none; }
  .badge-layer { position: absolute; inset: 0; }
  .badge { position: absolute; transform: translate(-50%,-50%); width: 20px; height: 20px;
    border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px;
    font-weight: 700; color: #0b0c0f; border: 1.5px solid rgba(0,0,0,0.55); box-shadow: 0 1px 3px rgba(0,0,0,0.4); }
  .grid-label-layer { position: absolute; inset: 0; pointer-events: none; }
  .grid-label { position: absolute; font-size: 9.5px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    color: #001018; background: rgba(56,220,255,0.9); padding: 1px 3px; border-radius: 2px; white-space: nowrap; line-height: 1.3; }
  .grid-label-x { top: 0; transform: translate(-50%, 0); }
  .grid-label-y { left: 0; transform: translate(0, -50%); }
  aside.panel { display: flex; flex-direction: column; gap: 14px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .card h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted);
    margin: 0 0 10px; font-weight: 650; }
  .field { margin-bottom: 12px; }
  .field:last-child { margin-bottom: 0; }
  .field label.step { display: block; font-size: 12.5px; font-weight: 600; margin-bottom: 5px; }
  .hint { font-size: 11.5px; color: var(--muted); margin-top: 4px; }
  input[type="file"] { font-size: 12.5px; width: 100%; }
  textarea { width: 100%; font-size: 12px; padding: 8px; border: 1px solid var(--border);
    border-radius: 6px; background: var(--mono-bg); color: var(--text); resize: vertical; }
  button { font-size: 13px; font-weight: 600; border: 1px solid var(--border); border-radius: 6px;
    padding: 7px 12px; background: var(--mono-bg); color: var(--text); cursor: pointer; }
  button:hover:not(:disabled) { border-color: var(--muted); }
  button:disabled { opacity: 0.5; cursor: default; }
  button.primary { background: #4c5b73; color: white; border-color: #4c5b73; }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .status { font-size: 12.5px; color: var(--muted); margin-top: 8px; min-height: 16px; }
  .status.error { color: var(--danger); background: var(--danger-bg); padding: 8px 10px; border-radius: 6px; }
  .status.warn { color: var(--warn); background: var(--warn-bg); padding: 8px 10px; border-radius: 6px; }
  .hyp-row { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-top: 1px solid var(--border); }
  .hyp-row:first-of-type { border-top: none; padding-top: 2px; }
  .hyp-row input[type="checkbox"] { margin-top: 3px; width: 15px; height: 15px; flex-shrink: 0; }
  .swatch { width: 12px; height: 12px; border-radius: 3px; margin-top: 4px; flex-shrink: 0; border: 1px solid rgba(128,128,128,0.4); }
  .hyp-copy { flex: 1; min-width: 0; }
  .hyp-copy label { font-size: 13px; font-weight: 600; cursor: pointer; display: block; }
  .hyp-copy p { margin: 3px 0 0; font-size: 11.5px; color: var(--muted); line-height: 1.4; }
  .hyp-copy .formula { display: block; margin-top: 4px; font-size: 10.5px; color: var(--muted); }
  .skip-note { font-size: 11.5px; color: var(--muted); padding: 6px 0; border-top: 1px dashed var(--border); margin-top: 4px; }
  .aux-row { display: flex; align-items: center; gap: 8px; padding-top: 10px; margin-top: 10px;
    border-top: 1px dashed var(--border); font-size: 12px; color: var(--muted); }
  ol.legend-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
  ol.legend-list li { display: flex; gap: 8px; font-size: 12px; line-height: 1.4; }
  ol.legend-list .idx { flex-shrink: 0; width: 18px; height: 18px; border-radius: 50%; background: var(--mono-bg);
    border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 10.5px;
    font-weight: 700; color: var(--muted); }
  .scroll-pane { font-size: 12px; line-height: 1.5; color: var(--muted); max-height: 220px; overflow-y: auto; white-space: pre-wrap; }
  .meta-line { font-size: 11.5px; color: var(--muted); margin-top: 8px; }
  #results { display: none; }
</style>
</head>
<body>
<div class="page">
  <header>
    <h1>Overlay coordinate debug tool</h1>
    <p>Sends a chosen image, plus the prompt below, straight to the configured LLM, then re-projects
      the returned annotations under several hypotheses about what the normalised coordinates might
      actually mean.</p>
  </header>

  <div class="layout">
    <div class="stage-wrap">
      <div class="stage" id="stage">
        <div class="placeholder" id="placeholder">Choose an image to begin.</div>
      </div>
    </div>

    <aside class="panel">
      <div class="card">
        <h2>System prompt</h2>
        <textarea id="promptText" class="mono" rows="10"></textarea>
        <div class="row" style="margin-top:8px;">
          <button id="resetPromptBtn">Reset to current app prompt</button>
        </div>
        <div class="hint">Pre-filled with the exact prompt overlay mode sends today. Edit freely —
          Run sends whatever is in this box.</div>
      </div>

      <div class="card">
        <h2>Response schema</h2>
        <textarea id="schemaText" class="mono" rows="12"></textarea>
        <div class="row" style="margin-top:8px;">
          <button id="resetSchemaBtn">Reset to current app schema</button>
        </div>
        <div class="hint">Pre-filled with the exact <code>response_format</code> JSON schema overlay
          mode sends today. Must stay valid JSON. If you remove or rename <code>feedback_text</code> /
          <code>annotations</code>, parsing will just show 0 annotations rather than fail.</div>
      </div>

      <div class="card">
        <h2>Run</h2>
        <div class="field">
          <label class="step">1. Choose image</label>
          <input type="file" id="fileInput" accept="image/*" />
        </div>
        <div class="field">
          <label class="step">2. (optional) Mark the character</label>
          <div class="row">
            <button id="clearBoxBtn" disabled>Clear box</button>
          </div>
          <div class="hint">Drag on the image to draw a box around the figure. After Run, the
            response re-projected onto that box (H5) is shown automatically, alongside the
            unmodified full-image reading (H0) for comparison — toggle either off below.</div>
        </div>
        <div class="field">
          <button class="primary" id="runBtn" disabled>Run</button>
        </div>
        <div class="status" id="status"></div>
        <div class="aux-row">
          <input type="checkbox" id="toggleGrid" checked />
          <label for="toggleGrid">Show pixel/percent grid</label>
        </div>
        <div class="hint">Drawn on the image as soon as you choose it, independently of any LLM
          call — if this grid doesn't appear, the SVG overlay isn't rendering in this browser at
          all, which narrows the problem down before blaming the LLM response.</div>
      </div>

      <div id="results">
        <div class="card">
          <h2>Hypotheses</h2>
          <div id="hypControls"></div>
          <div id="skipNotes"></div>
          <div class="aux-row">
            <input type="checkbox" id="toggleCanvas" checked />
            <label for="toggleCanvas">Show detected canvas boundary</label>
          </div>
          <div class="aux-row">
            <input type="checkbox" id="toggleCharbox" checked />
            <label for="toggleCharbox">Show character bounding box</label>
          </div>
          <div class="meta-line" id="metaLine"></div>
        </div>

        <div class="card">
          <h2>Annotation key</h2>
          <ol class="legend-list" id="legendList"></ol>
        </div>

        <div class="card">
          <h2>feedback_text</h2>
          <div class="scroll-pane mono" id="feedbackText"></div>
        </div>

        <div class="card">
          <h2>Raw LLM response</h2>
          <div class="scroll-pane mono" id="rawResponse"></div>
        </div>
      </div>
    </aside>
  </div>
</div>

<script id="defaultPromptData" type="application/json">__DEFAULT_PROMPT_JSON__</script>
<script id="defaultSchemaData" type="application/json">__DEFAULT_SCHEMA_JSON__</script>
<script id="modelData" type="application/json">__MODEL_JSON__</script>
<script>
(function () {
  const svgNS = 'http://www.w3.org/2000/svg';
  const stage = document.getElementById('stage');
  const placeholder = document.getElementById('placeholder');
  const fileInput = document.getElementById('fileInput');
  const runBtn = document.getElementById('runBtn');
  const clearBoxBtn = document.getElementById('clearBoxBtn');
  const statusEl = document.getElementById('status');
  const results = document.getElementById('results');
  const promptText = document.getElementById('promptText');
  const resetPromptBtn = document.getElementById('resetPromptBtn');
  const schemaText = document.getElementById('schemaText');
  const resetSchemaBtn = document.getElementById('resetSchemaBtn');

  const DEFAULT_PROMPT = JSON.parse(document.getElementById('defaultPromptData').textContent);
  const DEFAULT_SCHEMA = JSON.parse(document.getElementById('defaultSchemaData').textContent);
  const MODEL_NAME = JSON.parse(document.getElementById('modelData').textContent);
  promptText.value = DEFAULT_PROMPT;
  resetPromptBtn.addEventListener('click', () => { promptText.value = DEFAULT_PROMPT; });
  schemaText.value = DEFAULT_SCHEMA;
  resetSchemaBtn.addEventListener('click', () => { schemaText.value = DEFAULT_SCHEMA; });

  let img = null;
  let svg = null;
  let gridSvg = null;
  let gridLabelLayer = null;
  let drawLayer = null;
  let drawRectEl = null;
  let imageB64 = null;
  let characterBbox = null; // [x0,y0,x1,y1] in natural image pixels
  let dragStart = null;

  const GRID_STEP = 0.1;

  function buildGrid() {
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    gridSvg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    gridSvg.setAttribute('preserveAspectRatio', 'none');
    gridSvg.innerHTML = '';
    if (gridLabelLayer) gridLabelLayer.remove();
    gridLabelLayer = document.createElement('div');
    gridLabelLayer.className = 'grid-label-layer';

    for (let f = 0; f <= 1.0001; f += GRID_STEP) {
      const edge = f <= 0.001 || f >= 0.999;
      const x = f * w;
      const vline = document.createElementNS(svgNS, 'line');
      vline.setAttribute('x1', x); vline.setAttribute('y1', 0);
      vline.setAttribute('x2', x); vline.setAttribute('y2', h);
      vline.setAttribute('stroke', 'rgba(38,220,255,0.55)');
      vline.setAttribute('stroke-width', edge ? '2' : '1');
      vline.setAttribute('vector-effect', 'non-scaling-stroke');
      gridSvg.appendChild(vline);

      const y = f * h;
      const hline = document.createElementNS(svgNS, 'line');
      hline.setAttribute('x1', 0); hline.setAttribute('y1', y);
      hline.setAttribute('x2', w); hline.setAttribute('y2', y);
      hline.setAttribute('stroke', 'rgba(38,220,255,0.55)');
      hline.setAttribute('stroke-width', edge ? '2' : '1');
      hline.setAttribute('vector-effect', 'non-scaling-stroke');
      gridSvg.appendChild(hline);

      const xLabel = document.createElement('div');
      xLabel.className = 'grid-label grid-label-x';
      xLabel.style.left = (f * 100) + '%';
      xLabel.textContent = Math.round(f * 100) + '% ' + Math.round(x) + 'px';
      gridLabelLayer.appendChild(xLabel);

      const yLabel = document.createElement('div');
      yLabel.className = 'grid-label grid-label-y';
      yLabel.style.top = (f * 100) + '%';
      yLabel.textContent = Math.round(f * 100) + '% ' + Math.round(y) + 'px';
      gridLabelLayer.appendChild(yLabel);
    }

    stage.appendChild(gridLabelLayer);
    applyGridVisibility();
  }

  function applyGridVisibility() {
    const on = document.getElementById('toggleGrid').checked;
    gridSvg.style.display = on ? '' : 'none';
    if (gridLabelLayer) gridLabelLayer.style.display = on ? '' : 'none';
  }

  document.getElementById('toggleGrid').addEventListener('change', applyGridVisibility);

  function setStatus(msg, level) {
    statusEl.textContent = msg || '';
    statusEl.className = 'status' + (level ? ' ' + level : '');
  }

  function naturalPoint(evt) {
    const rect = stage.getBoundingClientRect();
    const fx = Math.min(Math.max((evt.clientX - rect.left) / rect.width, 0), 1);
    const fy = Math.min(Math.max((evt.clientY - rect.top) / rect.height, 0), 1);
    return [fx * img.naturalWidth, fy * img.naturalHeight];
  }

  function renderDrawRect() {
    if (drawRectEl) drawRectEl.remove();
    if (!characterBbox) return;
    const [x0, y0, x1, y1] = characterBbox;
    drawRectEl = document.createElement('div');
    drawRectEl.className = 'drawrect';
    drawRectEl.style.left = (x0 / img.naturalWidth * 100) + '%';
    drawRectEl.style.top = (y0 / img.naturalHeight * 100) + '%';
    drawRectEl.style.width = ((x1 - x0) / img.naturalWidth * 100) + '%';
    drawRectEl.style.height = ((y1 - y0) / img.naturalHeight * 100) + '%';
    stage.appendChild(drawRectEl);
  }

  function buildStage() {
    stage.innerHTML = '';
    gridLabelLayer = null;
    img = document.createElement('img');
    img.id = 'frame';
    img.onload = buildGrid;
    stage.appendChild(img);

    gridSvg = document.createElementNS(svgNS, 'svg');
    gridSvg.classList.add('grid-svg');
    stage.appendChild(gridSvg);

    svg = document.createElementNS(svgNS, 'svg');
    stage.appendChild(svg);

    drawLayer = document.createElement('div');
    drawLayer.className = 'drawlayer';
    stage.appendChild(drawLayer);

    drawLayer.addEventListener('mousedown', (e) => {
      dragStart = naturalPoint(e);
    });
    drawLayer.addEventListener('mousemove', (e) => {
      if (!dragStart) return;
      const p = naturalPoint(e);
      characterBbox = [
        Math.min(dragStart[0], p[0]), Math.min(dragStart[1], p[1]),
        Math.max(dragStart[0], p[0]), Math.max(dragStart[1], p[1]),
      ];
      renderDrawRect();
    });
    window.addEventListener('mouseup', () => {
      if (!dragStart) return;
      dragStart = null;
      clearBoxBtn.disabled = !characterBbox;
    });
  }

  clearBoxBtn.addEventListener('click', () => {
    characterBbox = null;
    renderDrawRect();
    clearBoxBtn.disabled = true;
  });

  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      imageB64 = dataUrl.split(',')[1];
      placeholder.style.display = 'none';
      buildStage();
      img.src = dataUrl;
      characterBbox = null;
      clearBoxBtn.disabled = true;
      runBtn.disabled = false;
      results.style.display = 'none';
      setStatus('');
    };
    reader.readAsDataURL(file);
  });

  runBtn.addEventListener('click', async () => {
    try {
      JSON.parse(schemaText.value);
    } catch (err) {
      setStatus('Schema is not valid JSON: ' + err, 'error');
      return;
    }
    runBtn.disabled = true;
    results.style.display = 'none';
    setStatus('Calling the LLM…');
    try {
      const resp = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_b64: imageB64,
          character_bbox: characterBbox,
          system_prompt: promptText.value,
          schema_json: schemaText.value,
        }),
      });
      const data = await resp.json();
      if (!data.ok) {
        setStatus(data.error || 'Unknown error', 'error');
        return;
      }
      setStatus(data.warning ? ('Warning: ' + data.warning) : 'Done.', data.warning ? 'warn' : null);
      renderResults(data);
    } catch (err) {
      setStatus('Request failed: ' + err, 'error');
    } finally {
      runBtn.disabled = false;
    }
  });

  function prettyPrintRaw(raw) {
    if (!raw) return '(empty response)';
    try {
      return JSON.stringify(JSON.parse(raw), null, 2);
    } catch (err) {
      return raw; // not JSON (e.g. a prose fallback) — show verbatim
    }
  }

  function pctX(px, w) { return (px / w * 100).toFixed(3) + '%'; }
  function pctY(py, h) { return (py / h * 100).toFixed(3) + '%'; }

  function makeMarker(defs, id, color) {
    const marker = document.createElementNS(svgNS, 'marker');
    marker.setAttribute('id', id);
    marker.setAttribute('markerUnits', 'userSpaceOnUse');
    marker.setAttribute('markerWidth', '14');
    marker.setAttribute('markerHeight', '14');
    marker.setAttribute('refX', '11');
    marker.setAttribute('refY', '7');
    marker.setAttribute('orient', 'auto-start-reverse');
    const path = document.createElementNS(svgNS, 'path');
    path.setAttribute('d', 'M0,0 L14,7 L0,14 Z');
    path.setAttribute('fill', color);
    marker.appendChild(path);
    defs.appendChild(marker);
  }

  function addRefRect(bbox, color) {
    const [x0, y0, x1, y1] = bbox;
    const rect = document.createElementNS(svgNS, 'rect');
    rect.setAttribute('x', x0);
    rect.setAttribute('y', y0);
    rect.setAttribute('width', x1 - x0);
    rect.setAttribute('height', y1 - y0);
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', color);
    rect.setAttribute('stroke-width', '2');
    rect.setAttribute('stroke-dasharray', '10 8');
    rect.setAttribute('vector-effect', 'non-scaling-stroke');
    svg.appendChild(rect);
    return rect;
  }

  function renderResults(data) {
    results.style.display = 'block';
    svg.setAttribute('viewBox', `0 0 ${data.image_w} ${data.image_h}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.innerHTML = '';
    stage.querySelectorAll('.badge-layer').forEach((el) => el.remove());

    const defs = document.createElementNS(svgNS, 'defs');
    svg.appendChild(defs);

    if (data.canvas_bbox) {
      const r = addRefRect(data.canvas_bbox, 'rgba(255,255,255,0.85)');
      document.getElementById('toggleCanvas').onchange = (e) => {
        r.style.display = e.target.checked ? '' : 'none';
      };
    }
    if (data.character_bbox) {
      const r = addRefRect(data.character_bbox, '#818cf8');
      document.getElementById('toggleCharbox').onchange = (e) => {
        r.style.display = e.target.checked ? '' : 'none';
      };
    }

    const legend = document.getElementById('legendList');
    legend.innerHTML = '';
    const first = data.hypotheses[0];
    first.shapes.forEach((shape, i) => {
      const li = document.createElement('li');
      const idx = document.createElement('span');
      idx.className = 'idx';
      idx.textContent = String(i + 1);
      const txt = document.createElement('span');
      txt.textContent = shape.label ? shape.label : ('(' + shape.type + ', no label)');
      li.appendChild(idx);
      li.appendChild(txt);
      legend.appendChild(li);
    });

    const controls = document.getElementById('hypControls');
    controls.innerHTML = '';

    data.hypotheses.forEach((hyp) => {
      const markerId = 'arrow-' + hyp.key;
      makeMarker(defs, markerId, hyp.color);

      const g = document.createElementNS(svgNS, 'g');
      g.style.display = hyp.default ? '' : 'none';

      const badgeGroup = document.createElement('div');
      badgeGroup.className = 'badge-layer';
      badgeGroup.style.display = hyp.default ? '' : 'none';

      hyp.shapes.forEach((shape, i) => {
        let anchor = null;
        if (shape.type === 'arrow') {
          const line = document.createElementNS(svgNS, 'line');
          line.setAttribute('x1', shape.p1[0]); line.setAttribute('y1', shape.p1[1]);
          line.setAttribute('x2', shape.p2[0]); line.setAttribute('y2', shape.p2[1]);
          line.setAttribute('stroke', hyp.color);
          line.setAttribute('stroke-width', '2.5');
          line.setAttribute('vector-effect', 'non-scaling-stroke');
          line.setAttribute('marker-end', 'url(#' + markerId + ')');
          g.appendChild(line);
          anchor = shape.p2;
        } else if (shape.type === 'line') {
          const poly = document.createElementNS(svgNS, 'polyline');
          poly.setAttribute('points', shape.points.map(p => p[0] + ',' + p[1]).join(' '));
          poly.setAttribute('fill', 'none');
          poly.setAttribute('stroke', hyp.color);
          poly.setAttribute('stroke-width', '2.5');
          poly.setAttribute('vector-effect', 'non-scaling-stroke');
          g.appendChild(poly);
          anchor = shape.points[0];
        } else if (shape.type === 'circle') {
          const circle = document.createElementNS(svgNS, 'circle');
          circle.setAttribute('cx', shape.center[0]);
          circle.setAttribute('cy', shape.center[1]);
          circle.setAttribute('r', Math.max(shape.radius, 1));
          circle.setAttribute('fill', 'none');
          circle.setAttribute('stroke', hyp.color);
          circle.setAttribute('stroke-width', '2.5');
          circle.setAttribute('vector-effect', 'non-scaling-stroke');
          g.appendChild(circle);
          anchor = shape.center;
        }
        if (anchor) {
          const badge = document.createElement('div');
          badge.className = 'badge';
          badge.style.left = pctX(anchor[0], data.image_w);
          badge.style.top = pctY(anchor[1], data.image_h);
          badge.style.background = hyp.color;
          badge.textContent = String(i + 1);
          badgeGroup.appendChild(badge);
        }
      });

      svg.appendChild(g);
      stage.appendChild(badgeGroup);

      const row = document.createElement('div');
      row.className = 'hyp-row';
      const check = document.createElement('input');
      check.type = 'checkbox';
      check.checked = hyp.default;
      const swatch = document.createElement('div');
      swatch.className = 'swatch';
      swatch.style.background = hyp.color;
      const copy = document.createElement('div');
      copy.className = 'hyp-copy';
      const label = document.createElement('label');
      label.textContent = hyp.label;
      copy.appendChild(label);
      const desc = document.createElement('p');
      desc.textContent = hyp.desc;
      copy.appendChild(desc);
      const formula = document.createElement('span');
      formula.className = 'formula mono';
      formula.textContent = hyp.formula;
      copy.appendChild(formula);
      row.appendChild(check); row.appendChild(swatch); row.appendChild(copy);
      controls.appendChild(row);

      check.addEventListener('change', (e) => {
        g.style.display = e.target.checked ? '' : 'none';
        badgeGroup.style.display = e.target.checked ? '' : 'none';
      });
    });

    const skipNotes = document.getElementById('skipNotes');
    skipNotes.innerHTML = '';
    if (!data.canvas_bbox) {
      const n = document.createElement('div');
      n.className = 'skip-note';
      n.textContent = 'H1 skipped — no confident light/white canvas region detected in this image.';
      skipNotes.appendChild(n);
    }
    if (!data.character_bbox) {
      const n = document.createElement('div');
      n.className = 'skip-note';
      n.textContent = 'H5 skipped — draw a box around the character before running to include it.';
      skipNotes.appendChild(n);
    }

    document.getElementById('feedbackText').textContent = data.feedback_text || '(empty)';
    document.getElementById('rawResponse').textContent = prettyPrintRaw(data.raw_response);
    document.getElementById('metaLine').textContent =
      data.image_w + '×' + data.image_h + 'px · model: ' + MODEL_NAME +
      ' · dumped to ' + data.debug_dump_dir;
  }
})();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    config = ConfigManager().load()
    if not config.is_configured():
        print(
            "Warning: no LLM configured (set it in the app's Settings, or via "
            "DRAWING_COACH_MODEL / DRAWING_COACH_API_KEY) — requests will fail "
            "until one is set.",
            file=sys.stderr,
        )
    config.debug_log_llm_io = True
    litellm.callbacks.append(DebugIOLogger(config))

    handler = _make_handler(config)
    server = HTTPServer(("127.0.0.1", args.port), handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Overlay debug tool running at {url}")
    print(f"Debug dumps will be written under {paths.debug_log_dir()}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
