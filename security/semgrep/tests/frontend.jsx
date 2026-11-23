// Test cases for security/semgrep/frontend.yml (parsed as JavaScript with JSX).
// Annotations: the line after a ruleid comment must be reported; after an ok comment it must stay silent.
// Inputs arrive as function parameters because Semgrep propagates constants from local variables.
import { useState } from "react";

export function DomSinks({ html, node, range, text }) {
  // ruleid: ieogagi-fe-dom-xss-sink
  const a = <div dangerouslySetInnerHTML={{ __html: html }} />;
  // ruleid: ieogagi-fe-dom-xss-sink
  const b = <p className="note" dangerouslySetInnerHTML={{ __html: html }}>
    {text}
  </p>;
  // ruleid: ieogagi-fe-dom-xss-sink
  node.innerHTML = html;
  // ruleid: ieogagi-fe-dom-xss-sink
  node.innerHTML += html;
  // ruleid: ieogagi-fe-dom-xss-sink
  node.outerHTML = html;
  // ruleid: ieogagi-fe-dom-xss-sink
  node.insertAdjacentHTML("beforeend", html);
  // ruleid: ieogagi-fe-dom-xss-sink
  document.write(html);
  // ruleid: ieogagi-fe-dom-xss-sink
  document.writeln(html);
  // ruleid: ieogagi-fe-dom-xss-sink
  const fragment = range.createContextualFragment(html);
  // ruleid: ieogagi-fe-dom-xss-sink
  const e = <iframe title="preview" srcDoc={html} />;
  // ruleid: ieogagi-fe-dom-xss-sink
  const f = <iframe title="preview" className="frame" srcDoc={html}></iframe>;
  // ruleid: ieogagi-fe-dom-xss-sink
  node.srcdoc = html;
  // ruleid: ieogagi-fe-dom-xss-sink
  document.getElementById("preview").srcdoc = html;
  // ok: ieogagi-fe-dom-xss-sink
  const g = <iframe title="preview" src="/preview" />;
  // ok: ieogagi-fe-dom-xss-sink
  node.textContent = text;
  // ok: ieogagi-fe-dom-xss-sink
  node.innerText = text;
  // ok: ieogagi-fe-dom-xss-sink
  const c = <p className="note">{text}</p>;
  // ok: ieogagi-fe-dom-xss-sink
  const d = document.createElement("div");
  return [a, b, c, d, e, f, g, fragment];
}

export function DynamicCode({ code, handler, delay }) {
  // ruleid: ieogagi-fe-dynamic-code
  eval(code);
  // ruleid: ieogagi-fe-dynamic-code
  const made = new Function("a", code);
  // ruleid: ieogagi-fe-dynamic-code
  const called = Function("return 1");
  // ruleid: ieogagi-fe-dynamic-code
  setTimeout("tick()", 100);
  // ruleid: ieogagi-fe-dynamic-code
  setInterval(`tick(${delay})`, 100);
  // ruleid: ieogagi-fe-dynamic-code
  globalThis.eval(code);
  // ruleid: ieogagi-fe-dynamic-code
  self.eval(code);
  // ruleid: ieogagi-fe-dynamic-code
  window.eval(code);
  // ruleid: ieogagi-fe-dynamic-code
  window["eval"](code);
  // ruleid: ieogagi-fe-dynamic-code
  globalThis["eval"](code);
  // ruleid: ieogagi-fe-dynamic-code
  globalThis.setTimeout("tick()", 100);
  // ruleid: ieogagi-fe-dynamic-code
  globalThis.setTimeout(`tick(${delay})`, 100);
  // ruleid: ieogagi-fe-dynamic-code
  self.setInterval("tick()", 100);
  // ruleid: ieogagi-fe-dynamic-code
  window.setTimeout("tick()", 100);
  // ruleid: ieogagi-fe-dynamic-code
  window.setInterval(`tick(${delay})`, 100);
  // ok: ieogagi-fe-dynamic-code
  globalThis.setTimeout(() => handler(), 100);
  // ok: ieogagi-fe-dynamic-code
  window.setInterval(handler, delay);
  // ok: ieogagi-fe-dynamic-code
  setTimeout(() => handler(), 100);
  // ok: ieogagi-fe-dynamic-code
  setTimeout(handler, delay);
  // ok: ieogagi-fe-dynamic-code
  setInterval(() => handler(), delay);
  // ok: ieogagi-fe-dynamic-code
  const parsed = JSON.parse(code);
  return [made, called, parsed];
}

export function DebugCode(value, notifier) {
  const logger = { log: (message) => message };
  // ruleid: ieogagi-fe-debug-code
  console.log(value);
  // ruleid: ieogagi-fe-debug-code
  console.error("failed", value);
  // ruleid: ieogagi-fe-debug-code
  window.console.warn(value);
  // ruleid: ieogagi-fe-debug-code
  alert("saved");
  // ruleid: ieogagi-fe-debug-code
  window.confirm("delete?");
  // ruleid: ieogagi-fe-debug-code
  const answer = prompt("name");
  // ruleid: ieogagi-fe-debug-code
  debugger;
  // ok: ieogagi-fe-debug-code
  logger.log(value);
  // ok: ieogagi-fe-debug-code
  notifier.alert(value);
  // ok: ieogagi-fe-debug-code
  const confirmLabel = String(value);
  return [answer, confirmLabel];
}

export function BrowserStorage(key, value) {
  const memory = new Map();
  // ruleid: ieogagi-fe-browser-storage
  localStorage.setItem(key, value);
  // ruleid: ieogagi-fe-browser-storage
  sessionStorage.getItem(key);
  // ruleid: ieogagi-fe-browser-storage
  window.localStorage.removeItem(key);
  // ruleid: ieogagi-fe-browser-storage
  window.sessionStorage.clear();
  // ruleid: ieogagi-fe-browser-storage
  const request = indexedDB.open("cache");
  // ruleid: ieogagi-fe-browser-storage
  indexedDB.deleteDatabase("cache");
  // ruleid: ieogagi-fe-browser-storage
  const db = indexedDB;
  // ruleid: ieogagi-fe-browser-storage
  const names = indexedDB.databases();
  // ruleid: ieogagi-fe-browser-storage
  window.indexedDB.open("cache");
  // ruleid: ieogagi-fe-browser-storage
  window.indexedDB.deleteDatabase("cache");
  // ruleid: ieogagi-fe-browser-storage
  const windowDb = window.indexedDB;
  // ruleid: ieogagi-fe-browser-storage
  document.cookie = `theme=${value}`;
  // ruleid: ieogagi-fe-browser-storage
  const cookies = document.cookie;
  // ok: ieogagi-fe-browser-storage
  const [state, setState] = useState(value);
  // ok: ieogagi-fe-browser-storage
  memory.set(key, value);
  // ok: ieogagi-fe-browser-storage
  const title = document.title;
  return [request, db, names, windowDb, cookies, state, setState, title];
}

export function Redirects(next, navigate, frame) {
  // ruleid: ieogagi-fe-open-redirect
  window.location = next;
  // ruleid: ieogagi-fe-open-redirect
  location.href = next;
  // ruleid: ieogagi-fe-open-redirect
  window.location.href = next;
  // ruleid: ieogagi-fe-open-redirect
  location.assign(next);
  // ruleid: ieogagi-fe-open-redirect
  location.replace(next);
  // ruleid: ieogagi-fe-open-redirect
  window.location.replace(next);
  // ruleid: ieogagi-fe-open-redirect
  window.open(next, "_blank");
  // ruleid: ieogagi-fe-open-redirect
  document.location = next;
  // ruleid: ieogagi-fe-open-redirect
  document.location.href = next;
  // ruleid: ieogagi-fe-open-redirect
  top.location = next;
  // ruleid: ieogagi-fe-open-redirect
  top.location.href = next;
  // ruleid: ieogagi-fe-open-redirect
  location = next;
  // ruleid: ieogagi-fe-open-redirect
  frame.contentWindow.location.assign(next);
  // ruleid: ieogagi-fe-open-redirect
  top.location.replace(next);
  // ruleid: ieogagi-fe-open-redirect
  self.location.assign(next);
  // ruleid: ieogagi-fe-open-redirect
  document.location.replace(next);
  // ruleid: ieogagi-fe-open-redirect
  parent.location.href = next;
  // ruleid: ieogagi-fe-open-redirect
  window.location = "//evil.example/login";
  // ruleid: ieogagi-fe-open-redirect
  document.location = "javascript:void(0)";
  // ok: ieogagi-fe-open-redirect
  document.location = "/login";
  // ok: ieogagi-fe-open-redirect
  document.location.href = "/login";
  // ok: ieogagi-fe-open-redirect
  top.location = "/login";
  // ok: ieogagi-fe-open-redirect
  top.location.href = "/";
  // ok: ieogagi-fe-open-redirect
  location = "/staff/records";
  // ok: ieogagi-fe-open-redirect
  top.location.assign("/login");
  // ok: ieogagi-fe-open-redirect
  self.location.replace("/login");
  // ok: ieogagi-fe-open-redirect
  document.location.replace("/login");
  // ok: ieogagi-fe-open-redirect
  window.location.assign("/login");
  // ok: ieogagi-fe-open-redirect
  location.href = "/";
  // ok: ieogagi-fe-open-redirect
  window.location = "/staff/records";
  // ok: ieogagi-fe-open-redirect
  window.open("/help", "_blank");
  // ok: ieogagi-fe-open-redirect
  const location = useLocation(next);
  // ok: ieogagi-fe-open-redirect
  navigate(next);
  // ok: ieogagi-fe-open-redirect
  const here = window.location.pathname;
  return here;
}

export function Randoms(max) {
  // ruleid: ieogagi-fe-weak-random
  const token = Math.random().toString(36).slice(2);
  // ruleid: ieogagi-fe-weak-random
  const pick = Math.floor(Math.random() * max);
  // ok: ieogagi-fe-weak-random
  const bytes = crypto.getRandomValues(new Uint32Array(4));
  // ok: ieogagi-fe-weak-random
  const id = crypto.randomUUID();
  // ok: ieogagi-fe-weak-random
  const bounded = Math.max(1, max);
  return [token, pick, bytes, id, bounded];
}

export function Messages(frame, payload, trustedOrigin, worker) {
  // ruleid: ieogagi-fe-postmessage-wildcard
  window.parent.postMessage(payload, "*");
  // ruleid: ieogagi-fe-postmessage-wildcard
  frame.contentWindow.postMessage(payload, "*", []);
  // ruleid: ieogagi-fe-postmessage-wildcard
  frame.contentWindow.postMessage(payload, { targetOrigin: "*" });
  // ok: ieogagi-fe-postmessage-wildcard
  frame.contentWindow.postMessage(payload, trustedOrigin);
  // ok: ieogagi-fe-postmessage-wildcard
  window.parent.postMessage(payload, window.location.origin);
  // ok: ieogagi-fe-postmessage-wildcard
  worker.postMessage(payload);
}

export function Endpoints(path) {
  // ruleid: ieogagi-fe-hardcoded-endpoint
  const remote = fetch("https://api.example.com/v1/items");
  // ruleid: ieogagi-fe-hardcoded-endpoint
  const local = fetch("http://localhost:8000/api/health");
  // ruleid: ieogagi-fe-hardcoded-endpoint
  const hostPort = "10.0.0.5:8000";
  // ruleid: ieogagi-fe-hardcoded-endpoint
  const address = "192.168.0.10";
  // ruleid: ieogagi-fe-hardcoded-endpoint
  const templated = `https://api.example.com/${path}`;
  // ok: ieogagi-fe-hardcoded-endpoint
  const relative = fetch("/api/children");
  // ok: ieogagi-fe-hardcoded-endpoint
  const sameOrigin = new URL(path, window.location.origin);
  // ok: ieogagi-fe-hardcoded-endpoint
  const isSecure = path.startsWith("https://");
  // ok: ieogagi-fe-hardcoded-endpoint
  const version = "1.2.3";
  // ok: ieogagi-fe-hardcoded-endpoint
  const svgNode = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  // ok: ieogagi-fe-hardcoded-endpoint
  const xlink = "http://www.w3.org/1999/xlink";
  return [remote, local, hostPort, address, templated, relative, sameOrigin, isSecure, version, svgNode, xlink];
}

export function Icon() {
  return (
    // ok: ieogagi-fe-hardcoded-endpoint
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true" />
  );
}

export async function EmptyCatch({ work, notify }) {
  // ruleid: ieogagi-fe-empty-catch
  try {
    await work();
  } catch {
    // Clipboard access denied: nothing else to do.
  }
  // ruleid: ieogagi-fe-empty-catch
  try {
    await work();
  } catch (error) {}
  // ruleid: ieogagi-fe-empty-catch
  try {
    await work();
  } catch (error) {
  } finally {
    notify("done");
  }
  // ruleid: ieogagi-fe-empty-catch
  work().catch(() => {});
  // ruleid: ieogagi-fe-empty-catch
  work().catch((error) => {
    // ignored
  });
  // ruleid: ieogagi-fe-empty-catch
  work().catch(function () {});
  // ok: ieogagi-fe-empty-catch
  try {
    await work();
  } catch {
    notify("failed");
  }
  // ok: ieogagi-fe-empty-catch
  try {
    await work();
  } catch {
    return false;
  }
  // ok: ieogagi-fe-empty-catch
  work().catch(() => notify("failed"));
  // ok: ieogagi-fe-empty-catch
  work().catch((error) => {
    notify(error.name);
  });
  // ok: ieogagi-fe-empty-catch
  try {
    await work();
  } finally {
    notify("done");
  }
  return true;
}
