#!/usr/bin/env python3
"""
Speed benchmark for OpenAI-compatible chat completion APIs.

Benchmarks:
  tools       - function / tool calling
  structured  - structured output (response_format json_schema / json_object)
  image       - image -> Markdown (text extraction + image captions), prompt from img-sample.json

Measures latency, time-to-first-token (when streaming), output tokens/sec and
throughput. It does not judge answer quality; it only checks that the response
has the expected shape (a tool call / parseable JSON), so failures are visible.

Usage:
  python bench.py        # reads config.yaml, img-sample.json, image.png next to this script
"""
from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import platform
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

BENCHMARKS = ("tools", "structured", "image")

# --------------------------------------------------------------------------- #
# Payloads
# --------------------------------------------------------------------------- #

WEATHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["city", "unit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current local time for a city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    },
]

STRUCTURED_SCHEMA = {
    "name": "person_profile",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string"},
            "city": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}},
            "employed": {"type": "boolean"},
        },
        "required": ["name", "age", "email", "city", "skills", "employed"],
        "additionalProperties": False,
    },
}

STRUCTURED_TEXT = (
    "Extract a profile from this text: Maria Gonzalez is a 34 year old software "
    "engineer living in Lisbon. She currently works at a fintech startup and is "
    "skilled in Python, Rust, Kubernetes and PostgreSQL. Reach her at "
    "maria.gonzalez@example.com."
)

def load_image_messages(path: Path, image_url: str, detail: str | None) -> list[dict]:
    """Load the image prompt messages and point every image_url part at our image."""
    if not path.exists():
        raise SystemExit(f"Image prompt file not found: {path}")
    messages = json.loads(path.read_text())["messages"]
    for msg in messages:
        if isinstance(msg.get("content"), list):
            for part in msg["content"]:
                if part.get("type") == "image_url":
                    part["image_url"] = {**part.get("image_url", {}), "url": image_url}
                    if detail:
                        part["image_url"]["detail"] = detail
    return messages


def _json_instruction(schema: dict) -> str:
    return "Respond only with a JSON object matching this JSON schema:\n" + json.dumps(schema["schema"])


def build_request(bench: str, api: "ApiConfig", s: "Settings", image_messages: list | None) -> dict:
    body: dict[str, Any] = {
        "model": api.model,
        api.max_tokens_param: s.max_tokens,
    }
    if s.temperature is not None:
        body["temperature"] = s.temperature

    if bench == "tools":
        body["messages"] = [
            {"role": "system", "content": "You are a helpful assistant. Use the provided tools."},
            {"role": "user", "content": "What's the weather in Paris right now, in celsius?"},
        ]
        body["tools"] = WEATHER_TOOLS
        body["tool_choice"] = api.tool_choice

    elif bench == "structured":
        body["messages"] = [
            {"role": "system", "content": "You extract structured data from text."},
            {"role": "user", "content": STRUCTURED_TEXT},
        ]
        _apply_response_format(body, api, STRUCTURED_SCHEMA)

    elif bench == "image":
        body["messages"] = image_messages
    else:
        raise ValueError(bench)

    if s.stream:
        body["stream"] = True
        if api.stream_usage:
            body["stream_options"] = {"include_usage": True}

    body.update(api.extra_body)
    return body


def _apply_response_format(body: dict, api: "ApiConfig", schema: dict) -> None:
    mode = api.structured_mode
    if mode == "json_schema":
        body["response_format"] = {"type": "json_schema", "json_schema": schema}
    elif mode == "json_object":
        body["response_format"] = {"type": "json_object"}
        _append_instruction(body, _json_instruction(schema))
    elif mode == "prompt":
        _append_instruction(body, _json_instruction(schema))
    else:
        raise ValueError(f"unknown structured_mode: {mode}")


def _append_instruction(body: dict, text: str) -> None:
    body["messages"][0]["content"] += "\n\n" + text


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

@dataclass
class Settings:
    runs: int = 5
    warmup: int = 1
    concurrency: int = 1
    timeout: float = 120.0
    stream: bool = True
    max_tokens: int = 512
    temperature: float | None = 0.0   # null = don't send
    image: str = "image.png"
    image_detail: str | None = None   # low | high | auto; null = leave as in img-sample.json
    output: str = "results.md"
    benchmarks: list[str] = field(default_factory=lambda: list(BENCHMARKS))


@dataclass
class ApiConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    benchmarks: list[str]
    tool_choice: Any = "auto"
    structured_mode: str = "json_schema"   # json_schema | json_object | prompt
    stream_usage: bool = True              # send stream_options.include_usage
    max_tokens_param: str = "max_tokens"   # or max_completion_tokens
    headers: dict = field(default_factory=dict)
    extra_body: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name} / {self.model}"

    @property
    def url(self) -> str:
        base = self.base_url.rstrip("/")
        return base if base.endswith("/chat/completions") else base + "/chat/completions"


_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            v = os.environ.get(m.group(1))
            if v is None:
                raise SystemExit(f"Config references ${{{m.group(1)}}} but it is not set in the environment")
            return v
        return _ENV_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: str) -> tuple[Settings, list[ApiConfig]]:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    settings = Settings(**(raw.get("settings") or {}))
    apis = []
    for entry in raw.get("apis") or []:
        entry = dict(entry)
        if entry.pop("enabled", True) is False:
            continue
        entry = {k: (_expand_env(v) if k not in ("name",) else v) for k, v in entry.items()}
        entry.setdefault("benchmarks", settings.benchmarks)
        for key in ("name", "base_url", "api_key", "model"):
            if not entry.get(key):
                raise SystemExit(f"API entry missing '{key}': {entry.get('name', entry)}")
        models = entry.pop("model")
        for model in (models if isinstance(models, list) else [models]):
            apis.append(ApiConfig(model=str(model), **entry))
    if not apis:
        raise SystemExit("No APIs configured")
    return settings, apis


# --------------------------------------------------------------------------- #
# Image handling
# --------------------------------------------------------------------------- #

def resolve_image(image: str, base_dir: Path) -> tuple[str, str]:
    """Return (url_for_api, human_label)."""
    if re.match(r"^(https?:|data:)", image):
        return image, image if not image.startswith("data:") else "data URL"
    p = Path(image)
    if not p.is_absolute():
        p = base_dir / p
    if not p.exists():
        raise SystemExit(f"Image not found: {p}")
    data = p.read_bytes()
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}", f"{p.name} ({len(data) / 1024:.0f} KB)"


# --------------------------------------------------------------------------- #
# Running requests
# --------------------------------------------------------------------------- #

@dataclass
class Result:
    ok: bool
    latency: float                      # seconds, request sent -> response complete
    ttft: float | None = None           # seconds, request sent -> first content/tool token
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    tokens_estimated: bool = False
    error: str | None = None

    @property
    def gen_tps(self) -> float | None:
        """Output tokens/sec during generation (excludes time to first token)."""
        if not self.completion_tokens:
            return None
        span = self.latency - (self.ttft or 0.0)
        return self.completion_tokens / span if span > 0 else None

    @property
    def e2e_tps(self) -> float | None:
        if not self.completion_tokens or self.latency <= 0:
            return None
        return self.completion_tokens / self.latency


def _validate(bench: str, content: str, tool_calls: dict[int, dict]) -> str | None:
    """Return an error string if the response doesn't have the expected shape."""
    if bench == "tools":
        if not tool_calls:
            return "no tool call returned"
        for tc in tool_calls.values():
            try:
                json.loads(tc.get("arguments") or "{}")
            except json.JSONDecodeError:
                return "tool call arguments are not valid JSON"
        return None
    if bench == "image":
        return None if content.strip() else "empty response"
    text = content.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return "response is not valid JSON"
    if not isinstance(obj, dict):
        return "response JSON is not an object"
    return None


async def run_one(client: httpx.AsyncClient, api: ApiConfig, bench: str, body: dict, stream: bool) -> Result:
    headers = {"Authorization": f"Bearer {api.api_key}", "Content-Type": "application/json", **api.headers}
    t0 = time.perf_counter()
    ttft: float | None = None
    content_parts: list[str] = []
    tool_calls: dict[int, dict] = {}
    usage: dict = {}

    try:
        if stream:
            async with client.stream("POST", api.url, headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    text = (await resp.aread()).decode(errors="replace")
                    return Result(False, time.perf_counter() - t0, error=f"HTTP {resp.status_code}: {text[:300]}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        return Result(False, time.perf_counter() - t0, error=f"stream error: {json.dumps(chunk['error'])[:300]}")
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    for choice in chunk.get("choices") or []:
                        delta = choice.get("delta") or {}
                        got = False
                        if delta.get("content"):
                            content_parts.append(delta["content"])
                            got = True
                        if delta.get("reasoning_content") or delta.get("reasoning"):
                            got = True
                        for tc in delta.get("tool_calls") or []:
                            slot = tool_calls.setdefault(tc.get("index", 0), {"name": "", "arguments": ""})
                            fn = tc.get("function") or {}
                            slot["name"] += fn.get("name") or ""
                            slot["arguments"] += fn.get("arguments") or ""
                            got = True
                        if got and ttft is None:
                            ttft = time.perf_counter() - t0
        else:
            resp = await client.post(api.url, headers=headers, json=body)
            if resp.status_code != 200:
                return Result(False, time.perf_counter() - t0, error=f"HTTP {resp.status_code}: {resp.text[:300]}")
            payload = resp.json()
            usage = payload.get("usage") or {}
            msg = ((payload.get("choices") or [{}])[0]).get("message") or {}
            content_parts.append(msg.get("content") or "")
            for i, tc in enumerate(msg.get("tool_calls") or []):
                fn = tc.get("function") or {}
                tool_calls[i] = {"name": fn.get("name", ""), "arguments": fn.get("arguments") or ""}
    except httpx.TimeoutException:
        return Result(False, time.perf_counter() - t0, error="timeout")
    except httpx.HTTPError as e:
        return Result(False, time.perf_counter() - t0, error=f"{type(e).__name__}: {e}")

    latency = time.perf_counter() - t0
    content = "".join(content_parts)
    completion = usage.get("completion_tokens")
    estimated = False
    if completion is None:
        chars = len(content) + sum(len(t["name"]) + len(t["arguments"]) for t in tool_calls.values())
        completion = max(1, round(chars / 4)) if chars else None
        estimated = True
    err = _validate(bench, content, tool_calls)
    return Result(err is None, latency, ttft, usage.get("prompt_tokens"), completion, estimated, err)


@dataclass
class BenchRun:
    api: ApiConfig
    bench: str
    results: list[Result]
    wall: float


async def run_bench(client: httpx.AsyncClient, api: ApiConfig, bench: str, s: Settings, image_messages: list | None) -> BenchRun:
    body = build_request(bench, api, s, image_messages)
    for _ in range(s.warmup):
        await run_one(client, api, bench, body, s.stream)

    sem = asyncio.Semaphore(max(1, s.concurrency))
    done = 0

    async def task() -> Result:
        nonlocal done
        async with sem:
            r = await run_one(client, api, bench, body, s.stream)
            done += 1
            mark = "." if r.ok else "x"
            print(mark, end="", flush=True)
            return r

    t0 = time.perf_counter()
    results = await asyncio.gather(*(task() for _ in range(s.runs)))
    wall = time.perf_counter() - t0
    return BenchRun(api, bench, list(results), wall)


# --------------------------------------------------------------------------- #
# Stats & Markdown report
# --------------------------------------------------------------------------- #

def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    k = (len(v) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def summarize(run: BenchRun) -> dict:
    ok = [r for r in run.results if r.ok]
    lat = [r.latency for r in ok]
    ttft = [r.ttft for r in ok if r.ttft is not None]
    gen = [r.gen_tps for r in ok if r.gen_tps]
    e2e = [r.e2e_tps for r in ok if r.e2e_tps]
    out = [r.completion_tokens for r in ok if r.completion_tokens]
    inp = [r.prompt_tokens for r in ok if r.prompt_tokens]
    return {
        "n": len(run.results),
        "ok": len(ok),
        "lat_mean": statistics.mean(lat) if lat else None,
        "lat_p50": _pct(lat, 0.5),
        "lat_p95": _pct(lat, 0.95),
        "lat_min": min(lat) if lat else None,
        "lat_max": max(lat) if lat else None,
        "lat_std": statistics.stdev(lat) if len(lat) > 1 else None,
        "ttft_p50": _pct(ttft, 0.5),
        "ttft_p95": _pct(ttft, 0.95),
        "gen_tps": statistics.median(gen) if gen else None,
        "e2e_tps": statistics.median(e2e) if e2e else None,
        "out_tokens": statistics.mean(out) if out else None,
        "in_tokens": statistics.mean(inp) if inp else None,
        "estimated": any(r.tokens_estimated for r in ok),
        "rps": len(ok) / run.wall if run.wall > 0 else None,
        "wall": run.wall,
        "errors": [r.error for r in run.results if not r.ok],
    }


def _ms(v: float | None) -> str:
    return "–" if v is None else f"{v * 1000:,.0f}"


def _num(v: float | None, fmt: str = ".1f") -> str:
    return "–" if v is None else format(v, fmt)


BENCH_TITLES = {
    "tools": "Function / tool calling",
    "structured": "Structured output",
    "image": "Image to Markdown (text extraction + captions)",
}


def render_markdown(runs: list[BenchRun], s: Settings, image_label: str | None, started: datetime, total: float) -> str:
    L: list[str] = []
    L.append("# OpenAI-compatible API speed benchmark\n")
    L.append(f"- **Date:** {started:%Y-%m-%d %H:%M:%S}")
    L.append(f"- **Runs per benchmark:** {s.runs} (+{s.warmup} warmup, not counted)")
    L.append(f"- **Concurrency:** {s.concurrency}")
    L.append(f"- **Streaming:** {'yes' if s.stream else 'no'}  ·  **max_tokens:** {s.max_tokens}  ·  **temperature:** {s.temperature}")
    if image_label:
        L.append(f"- **Image:** {image_label}, prompt from img-sample.json" + (f" (detail: {s.image_detail})" if s.image_detail else ""))
    L.append(f"- **Host:** {platform.system()} {platform.release()}, Python {platform.python_version()}")
    L.append(f"- **Total time:** {total:.1f}s\n")

    summaries = {(r.api.label, r.bench): summarize(r) for r in runs}
    apis = list(dict.fromkeys(r.api.label for r in runs))
    models = {r.api.label: r.api.model for r in runs}
    names = {r.api.label: r.api.name for r in runs}
    benches = [b for b in BENCHMARKS if any(r.bench == b for r in runs)]

    # Overview: p50 latency matrix
    L.append("## Overview — median latency (ms)\n")
    L.append("| API | Model | " + " | ".join(BENCH_TITLES[b].split(" (")[0] for b in benches) + " |")
    L.append("|---|---|" + "---:|" * len(benches))
    for a in apis:
        cells = []
        for b in benches:
            sm = summaries.get((a, b))
            if sm is None:
                cells.append("n/a")
            elif sm["ok"] == 0:
                cells.append("failed")
            else:
                cells.append(_ms(sm["lat_p50"]) + ("" if sm["ok"] == sm["n"] else f" ({sm['ok']}/{sm['n']})"))
        L.append(f"| {names[a]} | `{models[a]}` | " + " | ".join(cells) + " |")
    L.append("")

    # Per benchmark detail
    for b in benches:
        rows = [(a, summaries[(a, b)]) for a in apis if (a, b) in summaries]
        rows.sort(key=lambda x: (x[1]["lat_p50"] is None, x[1]["lat_p50"] or 0))
        L.append(f"## {BENCH_TITLES[b]}\n")
        L.append("| # | API | Model | OK | p50 ms | mean ms | p95 ms | min ms | max ms | TTFT p50 ms | TTFT p95 ms | gen tok/s | e2e tok/s | out tok | in tok | req/s |")
        L.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for i, (a, sm) in enumerate(rows, 1):
            est = "~" if sm["estimated"] else ""
            L.append(
                f"| {i} | {names[a]} | `{models[a]}` | {sm['ok']}/{sm['n']} | {_ms(sm['lat_p50'])} | {_ms(sm['lat_mean'])} | "
                f"{_ms(sm['lat_p95'])} | {_ms(sm['lat_min'])} | {_ms(sm['lat_max'])} | {_ms(sm['ttft_p50'])} | "
                f"{_ms(sm['ttft_p95'])} | {est}{_num(sm['gen_tps'])} | {est}{_num(sm['e2e_tps'])} | "
                f"{est}{_num(sm['out_tokens'], '.0f')} | {_num(sm['in_tokens'], '.0f')} | {_num(sm['rps'], '.2f')} |"
            )
        winner = next(((a, sm) for a, sm in rows if sm["lat_p50"] is not None), None)
        if winner and len(rows) > 1:
            L.append(f"\n**Fastest (p50):** {names[winner[0]]} `{models[winner[0]]}` — {_ms(winner[1]['lat_p50'])} ms")
        L.append("")

    # Errors
    err_rows = [(a, b, sm["errors"]) for (a, b), sm in summaries.items() if sm["errors"]]
    if err_rows:
        L.append("## Errors\n")
        for a, b, errs in err_rows:
            counts: dict[str, int] = {}
            for e in errs:
                counts[e or "unknown"] = counts.get(e or "unknown", 0) + 1
            L.append(f"**{a} / {b}**\n")
            for e, c in sorted(counts.items(), key=lambda x: -x[1]):
                L.append(f"- {c}× `{e.replace('`', "'").replace(chr(10), ' ')}`")
            L.append("")

    L.append("## Metric notes\n")
    L.append("- **Latency**: request sent → full response received, successful requests only.")
    L.append("- **TTFT**: time to first streamed content, reasoning or tool-call token (streaming only).")
    L.append("- **gen tok/s**: output tokens ÷ (latency − TTFT), i.e. decode speed. **e2e tok/s**: output tokens ÷ latency.")
    L.append("- **req/s**: successful requests ÷ wall-clock time for the batch (meaningful with concurrency > 1).")
    L.append("- **OK**: response had the expected shape (a tool call, parseable JSON, or non-empty Markdown for image). Content quality is not checked.")
    L.append("- `~` means token counts were estimated (≈4 chars/token) because the API returned no usage data.")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.yaml"


async def main_async() -> None:
    settings, apis = load_config(str(CONFIG))
    plan = [(api, b) for api in apis for b in BENCHMARKS if b in api.benchmarks]
    if not plan:
        raise SystemExit("Nothing to run")

    image_messages, image_label = None, None
    if any(b == "image" for _, b in plan):
        image_url, image_label = resolve_image(settings.image, HERE)
        image_messages = load_image_messages(HERE / "img-sample.json", image_url, settings.image_detail)

    print(f"{len(apis)} model(s), {len(plan)} benchmark run(s), {settings.runs} requests each\n")
    started = datetime.now()
    t0 = time.perf_counter()
    runs: list[BenchRun] = []
    limits = httpx.Limits(max_connections=max(10, settings.concurrency * 2))
    async with httpx.AsyncClient(timeout=settings.timeout, limits=limits) as client:
        for api, b in plan:
            print(f"[{b:>10}] {api.label} ", end="", flush=True)
            run = await run_bench(client, api, b, settings, image_messages)
            sm = summarize(run)
            print(f"  {sm['ok']}/{sm['n']} ok, p50 {_ms(sm['lat_p50'])} ms")
            if sm["errors"]:
                print(f"             first error: {sm['errors'][0][:160]}")
            runs.append(run)
    total = time.perf_counter() - t0

    md = render_markdown(runs, settings, image_label, started, total)
    out = Path(settings.output)
    if not out.is_absolute():
        out = HERE / out
    out.write_text(md)
    print(f"\nReport written to {out}")


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
