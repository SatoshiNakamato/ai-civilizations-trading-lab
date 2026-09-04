# You.com MCP research

The civilization uses You.com's hosted keyless MCP profile for routine web search:

`https://api.you.com/mcp?profile=free`

You.com's current documentation says this profile requires no API key and provides `you-search` with a 100-search/day free allowance. Higher-limit tools such as research, contents, and finance require authenticated access. The project therefore keeps those paid/keyed capabilities separate from routine search.

## Runtime policy

- Check the local cache before searching.
- Reserve a daily search slot only immediately before a real MCP tool call.
- Store useful results in shared civilization memory so agents do not repeat identical searches.
- Never put an API key in this repository.
- Never emulate an MCP tool call with a plain POST to the MCP URL.

The repository module `civilizations/you_mcp.py` provides the endpoint, accounting, cache, and connection configuration boundary. An MCP-capable agent/harness must perform the actual `you-search` call.

## Claude Code configuration

If Claude Code is running in a supported environment, configure the free server with:

```text
claude mcp add --transport http you-com https://api.you.com/mcp?profile=free
```

Then verify with `claude mcp list` and `/mcp` inside a Claude Code session.
