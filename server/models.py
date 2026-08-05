#!/usr/bin/env python3
"""One file per model, one place to switch, and a refusal when a model cannot
do the job.

    python3 server/models.py              # what is available and what runs
    python3 server/models.py use glm-5.2  # switch
    python3 server/models.py new          # what the provider offers that we have no file for

Models arrive constantly and each has its own quirks, so the quirks live in
`models/<id>.json` beside the model rather than in somebody's memory. The one
that matters most is `tools`:

    "openai"  tool calls in the OpenAI `tool_calls` field — works here
    "dsml"    DeepSeek's own syntax, emitted as assistant text; opencode cannot
              parse it, so the model reads back its own malformed output and
              loops (opencode#24566)
    "none"    no tool calling at all

**Switching to a model that cannot call tools is refused**, because the failure
does not look like a failure. There is no error: the agent simply answers with
markup in it, then answers again, then again — burning a turn's energy each
time. That is worth catching before it runs rather than after.

Two places used to need editing and now there is one. `opencode.json` holds
which model runs and what each model is; `public/settings.json` no longer names
a model at all — the page asks opencode what it is actually using, which is also
the truthful answer rather than what a file claims.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENT = ROOT / "agent"
MODELS = AGENT / "models"
CONFIG = AGENT / "opencode.json"
PROVIDER = "greenpt"
USABLE = {"openai"}


def described() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(MODELS.glob("*.json"))}


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")


def sync(cfg: dict, models: dict) -> dict:
    """Put every described model into the provider block.

    Declared in this repo rather than in ~/.config/opencode, so a checkout knows
    its own models and there is nothing to remember when setting the server up
    somewhere else. The key stays `{env:...}` — a placeholder is safe to commit,
    a key is not.
    """
    provider = cfg.setdefault("provider", {}).setdefault(PROVIDER, {})
    provider.setdefault("npm", "@ai-sdk/openai-compatible")
    provider.setdefault("name", "GreenPT")
    provider.setdefault("options", {
        "baseURL": "https://api.greenpt.ai/v1",
        "apiKey": "{env:GREENPT_API_KEY}",
    })
    provider["models"] = {
        mid: {k: v for k, v in (("name", m.get("name")), ("limit", m.get("limit"))) if v}
        for mid, m in models.items()
    }
    return cfg


def provider_models() -> list[str]:
    """What the provider actually offers, asked rather than assumed."""
    cfg = load_config()
    opts = ((cfg.get("provider") or {}).get(PROVIDER) or {}).get("options") or {}
    base = opts.get("baseURL", "https://api.greenpt.ai/v1")
    key = None
    # The key is an env placeholder in config; take the real one from the
    # environment of the running server, which is where it actually lives.
    pids = subprocess.run(["pgrep", "-f", "opencode serve"],
                          capture_output=True, text=True).stdout.split()
    for pid in pids:
        try:
            env = dict(l.split("=", 1) for l in
                       Path(f"/proc/{pid}/environ").read_text().split("\0") if "=" in l)
        except OSError:
            continue
        key = env.get("GREENPT_API_KEY") or key
    if not key:
        import os
        key = os.environ.get("GREENPT_API_KEY")
    if not key:
        sys.exit("GREENPT_API_KEY is not set and no running opencode has it either.")
    out = subprocess.run(["curl", "-sS", "-K", "-", f"{base}/models"],
                         input=f'header = "Authorization: Bearer {key}"\n',
                         capture_output=True, text=True)
    try:
        return sorted(m["id"] for m in json.loads(out.stdout).get("data", []))
    except (json.JSONDecodeError, KeyError):
        sys.exit(f"could not list models: {out.stdout[:120] or out.stderr[:120]}")


def show(models: dict, current: str) -> None:
    print(f"  running: {current}\n")
    for mid, m in models.items():
        tools = m.get("tools", "?")
        mark = "->" if current == f"{PROVIDER}/{mid}" else "  "
        flag = "" if tools in USABLE else f"   [no tools: {tools}]"
        print(f"  {mark} {mid:<32} {m.get('name', ''):<20}{flag}")
        if (note := m.get("note")) and tools not in USABLE:
            print(f"        {re.sub(r'\\s+', ' ', note)[:150]}…")


def use(mid: str, models: dict) -> None:
    m = models.get(mid)
    if not m:
        sys.exit(f"no models/{mid}.json — write one first, so the next person "
                 f"knows what this model does before switching to it.")
    tools = m.get("tools")
    if tools not in USABLE:
        sys.exit(f"{mid} cannot call tools ({tools}), and this agent is nothing "
                 f"but tools.\n\n  {re.sub(r'\\s+', ' ', m.get('note', ''))}\n\n"
                 f"Refusing rather than letting it fail quietly.")
    cfg = sync(load_config(), models)
    cfg["model"] = f"{PROVIDER}/{mid}"
    save_config(cfg)
    print(f"  now: {cfg['model']}\n  restart for it to take effect: ./start.sh")


def main() -> None:
    models = described()
    args = sys.argv[1:]

    if args and args[0] == "new":
        missing = [m for m in provider_models() if m not in models]
        print(f"  {len(missing)} model(s) offered with no file here:")
        for m in missing:
            print(f"    {m}")
        print("\n  add models/<id>.json to make one selectable.")
        return

    if args and args[0] == "use":
        if len(args) < 2:
            sys.exit("which model? `models.py` lists them.")
        return use(args[1], models)

    cfg = save_config(sync(load_config(), models)) or load_config()
    show(models, cfg.get("model", "(unset)"))


if __name__ == "__main__":
    main()
