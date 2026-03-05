import argparse
import json
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from fcgen import PROJECT_ROOT, TEMPLATES_DIR
from fcgen.core.runner import run_template


TEMPLATES = {
    "bracket": {
        "example": TEMPLATES_DIR / "bracket" / "examples" / "basic.json",
        "schema": TEMPLATES_DIR / "bracket" / "schema.json",
        "default_out": "output/bracket",
    },
    "enclosure": {
        "example": TEMPLATES_DIR / "enclosure" / "examples" / "basic.json",
        "schema": TEMPLATES_DIR / "enclosure" / "schema.json",
        "default_out": "output/enclosure",
    },
    "adapter_plate": {
        "example": TEMPLATES_DIR / "adapter_plate" / "examples" / "basic.json",
        "schema": TEMPLATES_DIR / "adapter_plate" / "schema.json",
        "default_out": "output/adapter_plate",
    },
}


HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>fcgen ブラウザ UI</title>
  <style>
    :root {
      --bg-a: #f5f3ff;
      --bg-b: #ecfeff;
      --panel: #ffffff;
      --line: #d4d4d8;
      --ink: #18181b;
      --muted: #52525b;
      --accent: #0f766e;
      --accent-2: #115e59;
      --warn: #b91c1c;
      --ok: #166534;
      --log-bg: #0b1020;
      --log-ink: #dbeafe;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
      background: radial-gradient(circle at 5% 0%, var(--bg-a), transparent 35%), linear-gradient(140deg, var(--bg-a), var(--bg-b));
    }
    .wrap {
      max-width: 1180px;
      margin: 20px auto;
      padding: 0 14px 20px;
    }
    .hero {
      background: linear-gradient(130deg, #0f766e, #0e7490);
      color: #f8fafc;
      padding: 16px;
      border-radius: 14px;
      margin-bottom: 12px;
      box-shadow: 0 8px 28px rgba(15, 118, 110, 0.26);
    }
    .hero h1 {
      margin: 0 0 5px;
      font-size: 24px;
      line-height: 1.2;
    }
    .hero p {
      margin: 0;
      font-size: 13px;
      opacity: 0.95;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 12px;
      box-shadow: 0 8px 24px rgba(2, 6, 23, 0.06);
    }
    .title {
      font-weight: 700;
      font-size: 14px;
      margin-bottom: 10px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.25fr 1.75fr auto;
      gap: 10px;
      align-items: end;
    }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: end;
    }
    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 5px;
      font-weight: 600;
    }
    select, input, button, textarea {
      font: inherit;
    }
    select, input {
      width: 100%;
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    button {
      border: none;
      border-radius: 8px;
      padding: 9px 13px;
      cursor: pointer;
      color: #fff;
      background: var(--accent);
      font-weight: 600;
    }
    button:hover { background: var(--accent-2); }
    button.secondary {
      background: #334155;
    }
    button.secondary:hover {
      background: #1e293b;
    }
    button:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }
    .hint {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .required {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .required code {
      background: #f1f5f9;
      border-radius: 6px;
      padding: 2px 6px;
      margin-right: 5px;
      display: inline-block;
      margin-top: 4px;
    }
    .status {
      margin-top: 8px;
      font-size: 12px;
      font-weight: 600;
    }
    .status.ok { color: var(--ok); }
    .status.err { color: var(--warn); }
    textarea {
      width: 100%;
      min-height: 360px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      line-height: 1.45;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      background: #fcfcfd;
    }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }
    .quick {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      font-size: 12px;
      color: var(--muted);
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: var(--log-bg);
      color: var(--log-ink);
      border-radius: 8px;
      padding: 10px;
      min-height: 120px;
      font-size: 12px;
    }
    #links {
      margin-top: 8px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    a { color: var(--accent); font-weight: 600; }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .actions { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>fcgen Browser UI</h1>
      <p>テンプレートを選択し、JSONを編集して実行。生成ファイルをそのまま開けます。</p>
    </section>

    <section class="card">
      <div class="title">1) 設定</div>
      <div class="grid">
        <div>
          <label for="template">テンプレート</label>
          <select id="template"></select>
        </div>
        <div>
          <label for="outdir">出力フォルダ（プロジェクト相対）</label>
          <input id="outdir" placeholder="output/bracket" />
        </div>
        <div class="actions">
          <button id="load" class="secondary">サンプル読込</button>
          <button id="run">実行</button>
        </div>
      </div>
      <div class="hint">ヒント: 出力フォルダが存在しない場合は自動作成されます。</div>
      <div id="requiredGuide" class="required"></div>
      <div id="status" class="status"></div>
    </section>

    <section class="card">
      <div class="toolbar">
        <div class="title" style="margin:0;">2) パラメータ JSON</div>
        <div class="quick">
          <span>クイック操作:</span>
          <button id="formatJson" class="secondary" type="button">JSON整形</button>
          <button id="resetOut" class="secondary" type="button">出力先リセット</button>
        </div>
      </div>
      <textarea id="params" spellcheck="false"></textarea>
    </section>

    <section class="card">
      <div class="title">3) 実行結果</div>
      <pre id="result">準備完了</pre>
      <div id="links"></div>
    </section>
  </div>
<script>
const templateSel = document.getElementById('template');
const outDir = document.getElementById('outdir');
const params = document.getElementById('params');
const result = document.getElementById('result');
const links = document.getElementById('links');
const status = document.getElementById('status');
const requiredGuide = document.getElementById('requiredGuide');
const runBtn = document.getElementById('run');
const loadBtn = document.getElementById('load');
const formatBtn = document.getElementById('formatJson');
const resetOutBtn = document.getElementById('resetOut');
let templateMeta = {};

function log(msg) {
  result.textContent = msg;
}

function setStatus(msg, isError = false) {
  status.textContent = msg;
  status.className = isError ? 'status err' : 'status ok';
}

function setBusy(busy) {
  runBtn.disabled = busy;
  loadBtn.disabled = busy;
  runBtn.textContent = busy ? '実行中...' : '実行';
}

function resetOutputForTemplate(templateName) {
  outDir.value = templateMeta[templateName].default_out;
}

function renderRequiredGuide(templateName) {
  const meta = templateMeta[templateName] || {};
  const items = meta.required_paths || [];
  if (!items.length) {
    requiredGuide.textContent = '';
    return;
  }
  const html = items.map((k) => '<code>' + k + '</code>').join('');
  requiredGuide.innerHTML = '必須キー: ' + html;
}

function validateRequiredTopLevel(obj, templateName) {
  const req = (templateMeta[templateName] || {}).required_top || [];
  const missing = req.filter((k) => !(k in obj));
  return missing;
}

function getValueByPath(obj, path) {
  const parts = path.split('.');
  let cur = obj;
  for (const p of parts) {
    if (cur === null || typeof cur !== 'object' || !(p in cur)) {
      return { exists: false, value: undefined };
    }
    cur = cur[p];
  }
  return { exists: true, value: cur };
}

function findMissingRequiredPaths(obj, templateName) {
  const reqPaths = (templateMeta[templateName] || {}).required_paths || [];
  return reqPaths.filter((p) => !getValueByPath(obj, p).exists);
}

function renderMissingGuide(missingPaths) {
  if (!missingPaths.length) return '';
  const preview = missingPaths.slice(0, 12).map((p) => '- ' + p).join('\\n');
  const more = missingPaths.length > 12 ? ('\\n... +' + (missingPaths.length - 12) + ' more') : '';
  return '不足している必須キー:\\n' + preview + more;
}

function renderFiles(data) {
  links.innerHTML = '';
  if (!data.files) return;
  const order = ['step', 'stl', 'report_json', 'report_md', 'log'];
  for (const k of order) {
    if (!data.files[k]) continue;
    const a = document.createElement('a');
    a.href = data.files[k];
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = k;
    links.appendChild(a);
  }
}

async function init() {
  try {
    const r = await fetch('/api/templates');
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'failed to load templates');
    templateMeta = data.templates;
    for (const name of Object.keys(templateMeta)) {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      templateSel.appendChild(opt);
    }
    templateSel.addEventListener('change', onTemplateChange);
    loadBtn.addEventListener('click', loadExample);
    runBtn.addEventListener('click', runGen);
    formatBtn.addEventListener('click', formatJson);
    resetOutBtn.addEventListener('click', () => resetOutputForTemplate(templateSel.value));
    params.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runGen();
      }
    });
    await onTemplateChange();
    setStatus('準備完了');
  } catch (err) {
    setStatus('初期化に失敗しました', true);
    log('init error: ' + err);
  }
}

async function onTemplateChange() {
  const t = templateSel.value;
  resetOutputForTemplate(t);
  renderRequiredGuide(t);
  await loadExample();
}

async function loadExample() {
  links.innerHTML = '';
  setStatus('サンプルを読み込み中...');
  try {
    const t = templateSel.value;
    const r = await fetch('/api/example?template=' + encodeURIComponent(t));
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'failed to load example');
    params.value = JSON.stringify(data.params, null, 2);
    setStatus('サンプル読込完了: ' + t);
    log('サンプルを読み込みました: ' + t);
  } catch (err) {
    setStatus('サンプル読込に失敗しました', true);
    log('example load error: ' + err);
  }
}

function formatJson() {
  try {
    const parsed = JSON.parse(params.value);
    params.value = JSON.stringify(parsed, null, 2);
    setStatus('JSONを整形しました');
  } catch (err) {
    setStatus('JSON整形に失敗しました', true);
    log('JSON parse error: ' + err);
  }
}

async function runGen() {
  links.innerHTML = '';
  let obj;
  try {
    obj = JSON.parse(params.value);
  } catch (err) {
    setStatus('JSONが不正です', true);
    log('JSON parse error: ' + err);
    return;
  }
  const missing = validateRequiredTopLevel(obj, templateSel.value);
  if (missing.length) {
    setStatus('必須キーが不足しています', true);
    log('不足トップレベルキー: ' + missing.join(', '));
    return;
  }
  const missingPaths = findMissingRequiredPaths(obj, templateSel.value);
  if (missingPaths.length) {
    setStatus('必須キーが不足しています', true);
    log(renderMissingGuide(missingPaths));
    return;
  }

  setBusy(true);
  setStatus('生成を実行中...');
  log('実行中...');
  try {
    const r = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template: templateSel.value,
        out_dir: outDir.value,
        params: obj
      })
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || JSON.stringify(data, null, 2));
    setStatus('生成が完了しました');
    log(JSON.stringify(data, null, 2));
    renderFiles(data);
  } catch (err) {
    setStatus('生成に失敗しました', true);
    log('run error: ' + err);
  } finally {
    setBusy(false);
  }
}

init();
</script>
</body>
</html>
"""


def _safe_resolve_out_dir(out_dir: str, template: str) -> Path:
    raw = out_dir.strip() if out_dir else TEMPLATES[template]["default_out"]
    p = Path(raw)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (PROJECT_ROOT / p).resolve()
    return resolved


def _to_web_path(file_path: Path) -> str:
    rel = file_path.resolve().relative_to(PROJECT_ROOT)
    return "/files/" + str(rel).replace("\\", "/")


def _schema_required_info(template: str) -> dict:
    schema_path = TEMPLATES[template]["schema"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    required_top = list(schema.get("required", []))
    required_paths: list[str] = []

    def walk(node: dict, prefix: str = "") -> None:
        req = node.get("required", [])
        props = node.get("properties", {})
        for key in req:
            path = f"{prefix}.{key}" if prefix else key
            required_paths.append(path)
            child = props.get(key)
            if isinstance(child, dict) and child.get("type") == "object":
                walk(child, path)

    walk(schema)
    return {
        "required_top": required_top,
        "required_paths": required_paths,
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_text(HTTPStatus.OK, HTML, "text/html; charset=utf-8")
            return
        if path == "/api/templates":
            payload = {
                "templates": {
                    name: {
                        "default_out": meta["default_out"],
                        **_schema_required_info(name),
                    }
                    for name, meta in TEMPLATES.items()
                }
            }
            self._send_json(HTTPStatus.OK, payload)
            return
        if path == "/api/example":
            qs = parse_qs(parsed.query)
            template = qs.get("template", [""])[0]
            if template not in TEMPLATES:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"unknown template: {template}"})
                return
            ex_path = TEMPLATES[template]["example"]
            params = json.loads(ex_path.read_text(encoding="utf-8"))
            self._send_json(HTTPStatus.OK, {"template": template, "params": params})
            return
        if path.startswith("/files/"):
            rel = unquote(path[len("/files/") :]).replace("/", "\\")
            target = (PROJECT_ROOT / rel).resolve()
            try:
                target.relative_to(PROJECT_ROOT)
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid file path"})
                return
            if not target.exists() or not target.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "file not found"})
                return
            data = target.read_bytes()
            ctype = "application/octet-stream"
            if target.suffix.lower() in {".json"}:
                ctype = "application/json; charset=utf-8"
            elif target.suffix.lower() in {".md", ".txt", ".step", ".stl"}:
                ctype = "text/plain; charset=utf-8"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            template = payload["template"]
            params = payload["params"]
            out_dir = payload.get("out_dir", "")
            if template not in TEMPLATES:
                raise RuntimeError(f"unknown template: {template}")
            resolved_out = _safe_resolve_out_dir(out_dir=out_dir, template=template)
            result = run_template(template=template, params=params, out_dir=resolved_out, dry_run=False)
            files = {
                "step": _to_web_path(Path(result["outputs"]["step"])),
                "stl": _to_web_path(Path(result["outputs"]["stl"])),
                "report_json": _to_web_path(Path(result["outputs"]["report_json"])),
                "report_md": _to_web_path(Path(result["outputs"]["report_md"])),
                "log": _to_web_path(Path(result["outputs"]["log"])),
            }
            self._send_json(HTTPStatus.OK, {"ok": True, "result": result, "files": files})
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()},
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="fcgen browser UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"fcgen web ui: http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
