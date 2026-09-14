# Secure AI Application Template

## What is this project?

This project helps developers build AI applications securely without having to design the security architecture from scratch.

The goal is simple:

> **Developers focus on what the product should do. The Secure Template provides the security foundation around it.**

The template provides reusable security controls that are integrated into the AI application during development and automatically protect the application at runtime.

For example, if you are building an AI News Agent, you mainly need to decide what the application should do, which LLM and framework it should use, what tools and external sources it needs, what the user interface should look like, and where it will be deployed.

You do not need to design security mechanisms such as tool authorization, network restrictions, secret protection, or untrusted-content protection from scratch. The Secure Template provides these mechanisms and instructs the coding assistant how to apply them according to your product requirements.

## The Basic Development Process

```text
1. Copy the Secure Template
          |
          v
2. Start with Your Coding Assistant
          |
          v
3. Coding Assistant Develops and Verifies the Application
          |
          v
4. Developer Review and Deployment
```

Security is not something added after the application is finished. The Secure Template guides the coding assistant to apply the required security controls while the application is being developed and to verify them before completion.

## Step 1 - Copy the Secure Template

Start every new AI application from a fresh copy of the template.

For example, to create a project called `claims-agent`:

```bash
cp -r template/ claims-agent/
cd claims-agent/
chmod +x init.sh
./init.sh
```

The initial health check may report that project-specific information is still missing. This is expected for a fresh template because the template does not yet know what application you are building.

Continue to Step 2 and let the coding assistant guide the project setup and development workflow.

## Step 2 - Start with Your Coding Assistant

Open the copied project with your preferred coding assistant and tell it:

> **Read `AGENTS.md` and follow the workflow defined there.**

You can then provide a simple description of what you want to build. You do not need to prepare a complete technical specification or manually decide which `Context/` files to edit.

For example:

> Build an AI News application that collects AI and cybersecurity news, selects four important stories, generates a digest, and allows users to ask questions about the news.

The coding assistant follows `AGENTS.md` and guides you through the product-definition process. It asks questions when important information is missing, confirms the requirements with you, and records the agreed requirements in the appropriate `Context/` files before substantial development begins.

For an AI News application, the coding assistant may ask about the LLM and framework, required tools, approved news sources, API credentials, storage, user interface, and deployment environment.

Some product decisions also determine security requirements. For example:

```text
Developer says:
"The application should access TechCrunch and GitHub."

                |
                v

Product Requirement
Access TechCrunch and GitHub

                +

Security Requirement
Limit network access to approved destinations
```

The developer defines what the product needs. The coding assistant uses the Secure Template to translate those requirements into the application design, configuration, and required security controls.

## Step 3 - Coding Assistant Develops and Verifies the Application

Once the important requirements are sufficiently clear and recorded in `Context/`, the coding assistant continues with the development workflow defined in `AGENTS.md`.

The coding assistant builds the product functions and applies the relevant Secure Template controls as part of the same development process. For example, a feature that accesses an external website must use the template's network/egress controls; a feature that invokes a tool must use the template's tool-permission and runtime enforcement mechanisms.

If a new capability is introduced during development, the coding assistant should clarify the new requirement when necessary, update `Context/`, reassess the relevant controls, and then implement the change.

Before claiming the application is complete, the coding assistant runs the required product and security verification defined by the template.

## Step 4 - Developer Review and Deployment

The developer reviews the completed application, confirms that it meets the intended product requirements, reviews any unresolved risks or decisions requiring human approval, and determines whether it is ready for the target deployment environment.

## The Complete Process

```text
COPY SECURE TEMPLATE
         |
         v
OPEN WITH CODING ASSISTANT
         |
         v
"Read AGENTS.md and follow the workflow defined there."
         |
         v
CODING ASSISTANT <--> DEVELOPER
Define and clarify the product
         |
         v
CODING ASSISTANT
Records requirements in Context/
         |
         v
CODING ASSISTANT
Builds application + applies security controls
         |
         v
VERIFICATION
Product + security checks
         |
         v
DEVELOPER REVIEW
& DEPLOYMENT
```

In simple terms:

> **The developer defines what to build. `AGENTS.md` tells the coding assistant how to clarify, build, secure, and verify it using the Secure Template.**
