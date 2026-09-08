# Getting started

Ten minutes, no API key.

## Before you start

- **Claude Code**, installed and signed in. This guide is Claude Code hooks — no Claude Code, nothing to hook. (On Kiro? See [Tool compatibility](04-tool-compatibility.md).)
- **Python 3.11+** and **git**. That's it — the kit has no other dependencies.
- **Open the copy as its own project root in Claude Code.** This one saves you an hour: hooks load from `.claude/settings.json` at the project root, and only there. Open a parent folder instead and nothing fires — no error, just silence.

## Get the code

```bash
git clone https://github.com/YuanSingapore/harness-engineering-platform.git harness-engineering-platform
cd harness-engineering-platform
```

## Copy the template into a new project

The template is what you ship. Everything else in this repository is docs and evidence for it.

```bash
cp -r template/ ../my-agent/
cd ../my-agent
chmod +x init.sh
```

## Run the health check

```bash
./init.sh
```

It fails. On purpose. A fresh copy always exits 1 with five errors: four files still have
`{{PLACEHOLDER}}` blocks to fill, and the security coverage file doesn't exist until you run
`/security-tailor` (a Claude Code slash command, not a script). If `init.sh` passed on an unfilled
template, it would be lying to you — so it doesn't. CI pins this exact error set.

## Follow the handbook

The copied [`README.md`](../../template/README.md) walks you through the rest: define the
product, fill in your identity, set your phases and policy, tailor the security controls, then
build. Each step ends with `./init.sh` telling you what's still left.

## Attack it before you trust it

The handbook's [Test the runtime](../../template/README.md#test-the-runtime) section fires the
real hooks against an untouched copy — no setup needed. Do this once, first, before you build
anything: 30 seconds to know the gates actually work in your editor, not just on paper.

## Where to go next

- Deploying an application, not an IDE agent → [Integrate the runtime host](02-integrate-the-runtime-host.md)
- Need the classifier on a different machine → [Bring your own classifier](03-bring-your-own-classifier.md)
- Want to know what a passing gate does *not* prove → [What is not enforced](../reference/05-boundaries.md)
