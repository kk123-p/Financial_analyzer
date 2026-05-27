"""
Anthropic-format routing proxy for Claude Code Agent Teams.
Routes different model names to different backends.
Usage: python routing_proxy.py [--port PORT]
"""
import asyncio
import aiohttp
from aiohttp import web
import json

DEEPSEEK_URL = "https://api.deepseek.com/anthropic/v1/messages"
DEEPSEEK_KEY = "sk-d99fc231908a40c9bac5dc04601b4857"
MIMO_URL = "https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages"
MIMO_KEY = "tp-cjkvbys5ocjm25eanbxata8l3mcb3b3f0r3tc24o4dueoi2x"
PROXY_KEY = "sk-gateway-master-key-2026"

# (claude_model, backend_url, api_key, backend_model, label)
ROUTES = {
    "claude-opus-4-7":            (DEEPSEEK_URL, DEEPSEEK_KEY, "deepseek-chat", "DeepSeek V4 Pro"),
    "claude-sonnet-4-6":          (DEEPSEEK_URL, DEEPSEEK_KEY, "deepseek-chat", "DeepSeek V4 Pro"),
    "deepseek-v4-pro":            (DEEPSEEK_URL, DEEPSEEK_KEY, "deepseek-chat", "DeepSeek V4 Pro"),
    "claude-haiku-4-5-20251001":  (MIMO_URL, MIMO_KEY, "mimo-v2.5-pro", "Mimo V2.5 Pro"),
    "mimo-v2.5-pro":              (MIMO_URL, MIMO_KEY, "mimo-v2.5-pro", "Mimo V2.5 Pro"),
    "deepseek-v4-flash":          (DEEPSEEK_URL, DEEPSEEK_KEY, "deepseek-chat", "DeepSeek Flash"),
}


def resolve_backend(model):
    """Return (backend_url, api_key, backend_model, label) or None."""
    route = ROUTES.get(model)
    if not route:
        for key, val in ROUTES.items():
            if key in model or model in key:
                route = val
                break
    return route


async def handle_anthropic(request):
    """Forward any Anthropic-format request to the right backend."""
    # No auth check — localhost-only proxy, forwards to backends with
    # their own keys. Claude Code may send any token from its env/settings.

    body = await request.json()
    model = body.get("model", "")
    route = resolve_backend(model)
    if not route:
        return web.json_response(
            {"error": f"Unknown model: {model}. Known: {list(ROUTES.keys())}"},
            status=400)

    backend_url, api_key, backend_model, label = route
    original_model = model
    body["model"] = backend_model

    # Build backend URL from request path
    base = backend_url.rsplit("/v1/", 1)[0]  # e.g. https://api.deepseek.com/anthropic
    path = "/" + request.match_info.get("path", "v1/messages")
    full_url = f"{base}/{path}"

    fwd_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if "anthropic-version" in request.headers:
        fwd_headers["anthropic-version"] = request.headers["anthropic-version"]

    timeout = aiohttp.ClientTimeout(total=120)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(full_url, json=body, headers=fwd_headers) as resp:
                response_body = await resp.text()
                status = resp.status

        # Rewrite model name and strip thinking (JSON responses only)
        try:
            resp_json = json.loads(response_body)
            resp_json["model"] = original_model
            if "content" in resp_json:
                resp_json["content"] = [
                    c for c in resp_json["content"]
                    if c.get("type") != "thinking"
                ]
            response_body = json.dumps(resp_json)
        except (json.JSONDecodeError, KeyError):
            pass

        print(f"[proxy] {original_model} -> {label} [{status}] {path}")
        return web.Response(text=response_body, status=status,
                          content_type="application/json")
    except Exception as e:
        print(f"[proxy] ERROR: {e}")
        return web.json_response({"error": str(e)}, status=502)


async def handle_health(request):
    return web.json_response({"status": "ok", "routes": list(ROUTES.keys())})


app = web.Application()
app.router.add_post("/v1/{path:.*}", handle_anthropic)
app.router.add_get("/health", handle_health)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[2]) if "--port" in sys.argv else 4002
    print(f"[proxy] Starting on port {port}")
    for model, (url, key, bm, label) in ROUTES.items():
        print(f"  {model} -> {label}")
    web.run_app(app, port=port)
