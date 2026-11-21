# FX-007: live synthetic MCP connection probe

This probe runs the **unmodified pinned ForenZX server**, seeds a fictional completed job through its real SQLite job manager, and exercises its real HTTP endpoint. It can also ask the installed Codex CLI to call the two permitted read tools. It never starts a forensic analysis.

## Prerequisites

- Python 3.11 or newer in an isolated environment with the upstream dependencies installed.
- A clean checkout of `erikbabcan-commits/forenzx-mcp-hub` at commit `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`.
- For `--with-codex`: an installed Codex CLI and its existing authorized login. The probe does not log in, alter credentials, write a global MCP configuration, or persist project trust.
- For `--with-legacy-sdk`: the Python `mcp` package in the same environment. The separately recorded historical-client probe was designed for `mcp==1.29.0`.

The upstream server source is not included here. Its license remains a separate release gate.

## Run

From this repository, using the isolated upstream environment's Python:

```bash
/path/to/venv/bin/python integration/fx007/run_probe.py \
  --upstream /path/to/forenzx-mcp-hub \
  --output /path/to/new-fx007-report \
  --with-codex \
  --with-legacy-sdk
```

`--output` must be new or empty. Existing evidence is not overwritten. The default Codex timeout is 120 seconds; `--codex-timeout` accepts 20–300 seconds. Omit `--with-codex` to run only the HTTP acceptance checks; that does **not** establish AI-client compatibility.

Upstream's `[project]` dependency bounds are broader than some `[tool.poetry.dependencies]` bounds. A test environment should respect both or record the deviation. The report records installed package versions; it does not promise that an unpinned future dependency resolution reproduces those versions.

## What the probe does

1. Verifies the exact upstream commit and a clean working tree.
2. Creates a private temporary directory, fresh random credentials and signing secrets, and separate SQLite, data, vault and scratch locations. It uses production authentication behavior and binds the server to `127.0.0.1` on an unused local port.
3. Loads `product/fixtures/completed-hit.json`, creates a job through the upstream manager, substitutes the generated job ID and validates the result with upstream's actual `AnalysisResult` model before storing it.
4. Checks authentication failures, development-bypass rejection, API-key and JWT discovery, explicit supported-version requests, status, result equality, preservation of warnings/limitations, a cross-organization denial, and a missing job.
5. Runs the existing structural input validator on the retrieved result. This explicit check is **not** a pre-LLM enforcement mechanism inside Codex.
6. Optionally runs an unmodified Python SDK client and/or the installed Codex CLI. Codex receives only synthetic IDs and permission to use the two read tools. Its final structured answer must exactly match the selected synthetic source fields, and the server must actually have observed successful calls to both tools.
7. Stops only processes it created and deletes its temporary database, generated signing key and credentials.

The transparent ASGI recorder forwards messages unchanged. It records method/tool names, allowlisted protocol metadata, HTTP and JSON-RPC status, selected synthetic job IDs and response SHA-256 values. It does not record authorization headers, cookies or other request arguments. CLI logs are scrubbed for the generated secrets and bearer values before they are saved. Interruptions stop owned processes; Ctrl+C and SIGTERM return exit codes 130 and 143.

## Read the result correctly

`report.json` separates:

| Field | Meaning |
| --- | --- |
| `http_acceptance` | The synthetic endpoint/authorization/result checks passed. |
| `codex.accepted` | The requested named CLI run exited successfully, actually called both read tools, and returned the exact selected facts. |
| `requested_acceptance` | All requested primary checks passed; if Codex was requested, its acceptance is required. |
| `legacy_sdk` | Separate compatibility diagnostic. A legacy client's failure is not silently reclassified as success. |
| `server_discover_diagnostic` | Actual response to modern server discovery, separately recorded from explicitly pinned direct calls. |
| `engine_readiness` | Actual readiness response, which may be blocked because no approved forensic pack is enabled. |
| `not_tested` | Scope exclusions, including real evidence, signatures, forensic execution and report quality. |

Exit code `0` means the requested primary acceptance passed. Exit code `1` means it failed; `2` means the probe could not start. Optional legacy-client incompatibility does not change an otherwise successful primary result. No report or output field authorizes selling a finished forensic reporting product.

The synthetic fixture's original warnings are deliberately preserved even when their wording describes its offline origin. The probe's report separately states that those fictional bytes were served by a live local instance.

## Protocol and client references

- [MCP 2026-07-28 base protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)
- [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [Codex CLI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

The direct probe supplies the supported protocol in `params._meta` and `MCP-Protocol-Version`, with client information/capabilities and method/tool headers. Discovery and unsupported-version error semantics remain separate observations; successful supported-version calls do not prove full specification compliance.

See `codex-config.example.toml` for a credential-free configuration shape. Use only an endpoint you control or are authorized to access. A client allowlist does not create server-side report-only authorization; FX-008 remains a separate gate.
