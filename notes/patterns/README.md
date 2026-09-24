# Patterns

Proven, repeatable recipes for producing a kind of media, e.g. *a tileable PBR texture*, *a set of UI sound effects*, *a textured prop in a Unity scene*. A pattern combines tools and scripts. Tool notes describe individual tools.

A pattern belongs here once it has worked at least once in a logged experiment. Until then, it is a backlog item.

Each pattern (`notes/patterns/<slug>.md`) has:

- front matter (`status`, `last_verified`, `versions`), as in [AGENTS.md](../../AGENTS.md)
- **Produces:** what comes out, formats, licence constraints
- **Steps:** exact commands or scripts
- **Checks:** how the agent confirms the result is good (preview, measurements, tests)
- **Pitfalls:** what goes wrong and what to do instead
- **Evidence:** links to the experiments behind it

## Index

| Pattern | Produces | Status |
|---------|----------|--------|
| [Generated asset with provenance](generated-asset-with-provenance.md) | A PNG or WAV plus a `.json` sidecar | verified (macOS) |
