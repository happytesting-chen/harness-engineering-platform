# Getting started

Ten minutes, no API key, no dependencies beyond Python 3.11.

## 1. Get the code

```bash
git clone <repository-url> harness-engineering-platform
cd harness-engineering-platform
```

## 2. Copy the template into a new project

The template is what you ship; the repository around it is documentation and evidence.

```bash
cp -r template/ ../my-agent/
cd ../my-agent
chmod +x init.sh
```

## 3. Run the health check and read its failure

```bash
./init.sh
```

It exits 1 on a correct fresh copy, with exactly five errors: four files still hold
`{{PLACEHOLDER}}` blocks you must fill, and the security coverage file does not exist until you run
the tailoring command. That failure is the contract, not a bug: a health check that passed on an
unfilled template would be lying. CI in this repository pins the exact error set.

## 4. Follow the in-project handbook

From here the eight build steps are in the copied [`README.md`](../../template/README.md) — define
the product in `Context/`, fill the identity files, set the phases, set policy, tailor the controls,
then build inside the active phase. Every step ends with `./init.sh` telling you what is still open.

## 5. Attack it before you trust it

Section [Test the runtime](../../template/README.md#test-the-runtime) in the same handbook drives
the real hook binaries on an untouched copy. Do this once before wiring anything of your own: it
takes thirty seconds and it is the only way to know the gates fire in *your* editor.

## Where to go next

- Deploying an application rather than an IDE agent: [Integrate the runtime host](02-integrate-the-runtime-host.md).
- Wanting semantic screening on another machine: [Bring your own classifier](03-bring-your-own-classifier.md).
- Wanting to know what a passing gate proves and what it does not: [What is not enforced](../reference/07-what-is-not-enforced.md).
