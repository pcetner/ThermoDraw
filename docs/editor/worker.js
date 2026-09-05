// The library, in a worker. The page never blocks on Python: it posts
// {id, op, args} and gets {id, result} or {id, error} back, and every
// argument and result crosses as JSON text, so there is exactly one
// conversion each way and no proxy to leak.
//
// Started with {type: "boot", wheel, pyodide}: the wheel's absolute URL and
// the Pyodide version to fetch from jsDelivr. A module worker, because the
// classic `importScripts` of the CDN's pyodide.js fails to load in Chromium
// from a worker while the same file loads fine from a page; the ES module
// build imports cleanly from both.

let py = null;

function say(type, text) { postMessage({type, text}); }

async function boot(wheel, version) {
  const base = `https://cdn.jsdelivr.net/pyodide/v${version}/full/`;
  say("progress", "Fetching Python for the browser, about 10 MB, once.");
  const {loadPyodide} = await import(base + "pyodide.mjs");
  py = await loadPyodide({indexURL: base});
  say("progress", "Loading ThermoDraw.");
  await py.loadPackage(wheel, {messageCallback: () => {}});
  py.runPython("import json\nimport thermodraw._editor as E");
  const head = JSON.parse(py.runPython("json.dumps(E.head())"));
  postMessage({type: "ready", head});
}

function call(op, args) {
  py.globals.set("_args", JSON.stringify(args));
  const out = py.runPython(`json.dumps(E.${op}(*json.loads(_args)))`);
  return JSON.parse(out);
}

onmessage = async (e) => {
  const m = e.data;
  if (m.type === "boot") {
    try { await boot(m.wheel, m.pyodide); }
    catch (err) { postMessage({type: "failed", text: String(err)}); }
    return;
  }
  if (!py) { postMessage({id: m.id, error: "not ready"}); return; }
  try { postMessage({id: m.id, result: call(m.op, m.args)}); }
  catch (err) { postMessage({id: m.id, error: String(err)}); }
};
