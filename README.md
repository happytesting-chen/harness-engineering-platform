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
1. Clone the Secure Template repository
          |
          v
2. Start Claude Code in the repository
          |
          v
3. Tell Claude Code to create a new project
   using the Secure Template
          |
          v
4. Claude Code creates the project from template/
   and continues work in the new project
          |
          v
5. Describe the application you want to build
          |
          v
6. Claude Code clarifies requirements,
   builds the application + security controls,
   and verifies the result
          |
          v
7. Developer review and deployment
```

Security is not something added after the application is finished. Claude Code should identify the required controls before substantial coding, apply them while implementing the application, and verify them before completion.

## Step 1 - Clone the Secure Template

Clone the Secure Template repository and enter the repository:

```bash
git clone https://github.com/YuanSingapore/harness-engineering-platform.git harness-engineering-platform
cd harness-engineering-platform
```

The repository contains the reusable application template under `template/`.

## Step 2 - Ask Claude Code to Create a New Project

Start Claude Code from the cloned Secure Template repository.

Then tell Claude Code what project to create. For example:

> **Create a new project called `ai-news` using the Secure Template.**

Claude Code follows the repository-level `CLAUDE.md` bootstrap instructions. It creates the new project from the contents of `template/` without modifying the source template.

After creating the project, Claude Code continues all application work from the new project directory. The new project's own `CLAUDE.md` then becomes the Claude Code entry point and imports the main development workflow from `AGENTS.md` together with the active security controls.

The developer does not need to manually copy `template/` or manage the handover between the template repository and the new project.

## Step 3 - Describe the Application

Once the new project has been created, describe what you want to build.

For example:

> Build an AI News application that collects AI and cybersecurity news, selects four important stories, generates a digest, and allows users to ask questions about the news.

Claude Code should guide the product-definition process rather than immediately starting substantial coding.

It should:

1. Read the new project's instructions and existing `Context/` files.
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

## Step 4 - Claude Code Develops and Verifies the Application

Once the critical requirements are clear, Claude Code follows the workflow defined in the new project's `AGENTS.md`.

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

## Step 5 - Developer Review and Deployment

The developer reviews the completed application and confirms that the product behavior, deployment assumptions, and remaining risks are acceptable for the target environment.

The deployed application must continue to use the template's runtime enforcement path. Security files existing in the project are not sufficient by themselves if the application bypasses the runtime controls.

## Complete Process

```text
CLONE SECURE TEMPLATE REPOSITORY
         |
         v
START CLAUDE CODE
         |
         v
"Create a new project called ai-news
using the Secure Template."
         |
         v
CLAUDE CODE COPIES template/
TO THE NEW PROJECT
         |
         v
CONTINUE WORK IN NEW PROJECT
         |
         v
NEW PROJECT CLAUDE.md -> AGENTS.md
         |
         v
DEVELOPER DESCRIBES THE APPLICATION
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

> **Clone the Secure Template, ask Claude Code to create a new project from it, then describe what you want to build. Claude Code handles the project setup, requirement clarification, secure development, and verification workflow.**
