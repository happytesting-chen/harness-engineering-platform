# Secure AI Application Template

## What is this project?

This project helps developers build AI applications securely with Claude Code without having to design the security architecture from scratch.

The goal is simple:

> **Developers focus on what the product should do. The Secure Template provides the security foundation around it.**

The template provides reusable security controls that are integrated into the AI application during development and protect the application at runtime when the application is wired through the template's runtime enforcement path.

For example, if you are building an AI News application, you mainly need to decide:

- What should the application do?
- Which LLM and framework should it use?
- What tools does it need?
- Which external sources should it access?
- What should the user interface look like?
- Where will the application be deployed?

You do not need to design security mechanisms such as tool authorization, network restrictions, secret protection, or untrusted-content protection from scratch.

The Secure Template provides these mechanisms and gives Claude Code a defined workflow for applying them according to the product requirements.

## Basic Development Process

```text
1. Copy the Secure Template
          |
          v
2. Open the project with Claude Code
          |
          v
3. Describe the application you want to build
          |
          v
4. Claude Code clarifies the requirements
          |
          v
5. Claude Code builds the application
   + applies security controls
          |
          v
6. Verification
          |
          v
7. Developer review and deployment
```

Security is not something added after the application is finished. Claude Code should identify the required controls before substantial coding, apply them while implementing the application, and verify them before completion.

## Step 1 - Copy the Secure Template

Start every new AI application from a fresh copy of the template.

For example, to create a project called `claims-agent`:

```bash
git clone https://github.com/YuanSingapore/harness-engineering-platform.git harness-engineering-platform
cp -r harness-engineering-platform/template/ claims-agent/
cd claims-agent/
chmod +x init.sh
./init.sh
```

`init.sh` is a health check. A fresh template is expected to report missing project configuration because the template does not yet know what application you are building.

At this stage, a failure is expected. Continue to Step 2.

## Step 2 - Start with Claude Code

Open the copied project with Claude Code.

Claude Code loads the project instructions from `CLAUDE.md`. `CLAUDE.md` imports the main development workflow from `AGENTS.md` and the active security controls from `Security-kit/active-controls.md`.

You do not need to manually tell Claude Code to read `AGENTS.md`. Simply describe the application you want to build.

For example:

> Build an AI News application that collects AI and cybersecurity news, selects four important stories, generates a digest, and allows users to ask questions about the news.

Claude Code should then guide the product-definition process rather than immediately starting substantial coding.

It should:

1. Read the project instructions and existing `Context/` files.
2. Ask the developer questions when important information is missing.
3. Record confirmed requirements in the appropriate `Context/` files.
4. Identify the security controls required by those requirements.
5. Begin implementation only when the critical requirements are sufficiently clear.

Typical clarification questions may include:

- Which LLM and framework should be used?
- Which tools or actions does the application need?
- Which websites, APIs, or external systems may it access?
- Does it use credentials or sensitive data?
- Where will it be deployed?
- What user interface is required?

The developer does not need to decide which `Context/` file each answer belongs in. Claude Code should organize and record the confirmed requirements.

## Step 3 - Claude Code Develops and Verifies the Application

Once the critical requirements are clear, Claude Code follows the workflow defined in `AGENTS.md`.

The intended flow is:

```text
Developer describes the product
          |
          v
Claude Code clarifies requirements
          |
          v
Confirmed requirements recorded in Context/
          |
          v
Required security controls identified
          |
          v
Application + security controls implemented together
          |
          v
Product tests + security verification
```

For example:

```text
Requirement:
Access TechCrunch and GitHub
          |
          v
Product implementation:
Fetch information from those sources
          |
          v
Security implementation:
Allow only the approved external destinations
```

If a new capability is introduced during development, Claude Code should update the relevant requirements and reassess the applicable controls before implementing that capability.

Claude Code should not claim the application is complete until the required verification passes.

## Step 4 - Developer Review and Deployment

The developer reviews the completed application and confirms that the product behavior, deployment assumptions, and remaining risks are acceptable for the target environment.

The deployed application must continue to use the template's runtime enforcement path. Security files existing in the project are not sufficient by themselves if the application bypasses the runtime controls.

## Complete Process

```text
COPY SECURE TEMPLATE
         |
         v
OPEN WITH CLAUDE CODE
         |
         v
DESCRIBE THE APPLICATION
         |
         v
DEVELOPER <--> CLAUDE CODE
Clarify the product
         |
         v
RECORD REQUIREMENTS IN Context/
         |
         v
IDENTIFY REQUIRED SECURITY CONTROLS
         |
         v
BUILD APPLICATION + SECURITY TOGETHER
         |
         v
VERIFY
         |
         v
DEVELOPER REVIEW / DEPLOY
```

In simple terms:

> **The developer defines what to build. Claude Code clarifies the requirements, records them, builds the application using the Secure Template, and verifies the result.**
