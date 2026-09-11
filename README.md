SECURE AI APPLICATION TEMPLATE
==============================

What is this project?
---------------------

This project helps developers build AI applications and AI agents securely without having to design the security architecture from scratch.

The goal is simple:

    Developers focus on what the product should do.
    The Secure Template provides the security foundation around it.

The template provides reusable security controls, development guardrails, runtime protection, and verification.

For example, if you are building an AI News Agent, you mainly need to decide:

- What should the News Agent do?
- Which LLM and agent framework should it use?
- What tools does it need?
- Which news sources should it access?
- What should the user interface look like?
- Where will the application be deployed?

You do not need to design security mechanisms such as tool authorization, network restrictions, secret protection, or untrusted-content protection from scratch.

The Secure Template provides these mechanisms and guides the coding assistant to apply them according to your product requirements.


THE BASIC DEVELOPMENT PROCESS
=============================

    1. Copy the Secure Template
              |
              v
    2. Describe and clarify the product
              |
              v
    3. Record the requirements in Context/
              |
              v
    4. Identify the initial security requirements
              |
              v
    5. Build the application with security controls
              |
              v
    6. Verify the product and security
              |
              v
    7. Developer review and deployment

Security is not something added after the application is finished.

    Security is identified before development starts,
    applied while the application is being built,
    and verified before deployment.


STEP 1 - COPY THE SECURE TEMPLATE
=================================

Start every new AI application from a fresh copy of the template.

For example, to create a project called "claims-agent":

    cp -r template/ claims-agent/
    cd claims-agent/

Make the startup script executable:

    chmod +x init.sh

Run the first health check:

    ./init.sh

What is the health check?
-------------------------

The health check checks whether the project has been properly configured and whether the required project and security checks pass.

The first health check is expected to FAIL. This is intentional.

A newly copied template does not yet know what application you are building. For example, it does not know:

- What is the purpose of the application?
- Which AI model or framework will be used?
- What tools does the application need?
- Which external systems does it need to access?
- Which security controls are relevant?

The health check reports what is still missing.

    New Template
         |
         v
     ./init.sh
         |
         v
    Is the project ready?
       /        \
      NO        YES
      |          |
     FAIL       PASS
      |
      v
    Show what still needs to be completed

At this stage, FAIL is the correct result. Continue to Step 2.


STEP 2 - DESCRIBE AND CLARIFY THE PRODUCT
=========================================

Before coding starts, describe what you want to build.

The developer does not need to provide a complete technical specification at the beginning. Start with the product idea.

For example:

    Build an AI News Agent that collects AI and cybersecurity news,
    selects four important stories, generates a digest, and allows
    users to ask questions about the news.

Coding Assistant Clarifies the Requirements
-------------------------------------------

The coding assistant should read the product description and ask questions when important information is missing.

For example:

- Which news sources should the agent access?
- Which LLM and agent framework should it use?
- Does the agent need to save the digest?
- Does it use API credentials?
- Should it access any website, or only approved websites?
- Where will the application be deployed?

The purpose is to make sure the coding assistant understands the product before substantial coding begins.

These questions also help identify security-relevant requirements.

For example:

    Developer says:
    "The News Agent should access TechCrunch and GitHub."

                    |
                    v

        Product Requirement
        Fetch information from TechCrunch and GitHub

                    +

        Security Requirement
        Network access should be limited to approved destinations

The developer describes what the product needs. The Secure Template and coding assistant translate those requirements into the appropriate product and security implementation.


STEP 3 - RECORD THE REQUIREMENTS IN Context/
============================================

The clarified requirements should be recorded under:

    Context/

For example:

    Context/
    |-- product-design.md
    |-- ai-stack.md
    |-- architecture.md
    `-- deployment.md

The Context folder is the project's source of truth for what should be built.

It should describe things such as:

- Product purpose
- Main functions
- AI model and framework
- Required tools
- External systems and websites
- Deployment environment
- Important product constraints

For example:

    Product: AI News Agent
    Framework: Strands Agents
    Model: Claude
    UI: Streamlit

    Required capabilities:
      - Fetch news
      - Get GitHub trends
      - Save digest

    Required external access:
      - thehackernews.com
      - techcrunch.com
      - github.com
      - api.github.com

The coding assistant should use Context/ when building the application.

If important information is missing, it should ask the developer rather than silently guessing.


STEP 4 - IDENTIFY THE INITIAL SECURITY REQUIREMENTS
===================================================

Before substantial coding begins, the product requirements are checked against the security controls provided by the Secure Template.

The purpose is simple:

    What is the application going to do?
                    |
                    v
    What security controls are required?

For example:

    PRODUCT REQUIREMENT              SECURITY CONTROL

    Agent uses tools           --->  Tool Permission
    Agent accesses websites    --->  Egress Control
    Application uses API keys  --->  Secret Protection
    Agent reads Internet data  --->  Content Trust

For the AI News Agent:

    AI News Agent
         |
         +-- Uses tools -----------------> Tool Permission
         |
         +-- Accesses selected websites -> Egress Control
         |
         +-- Uses API credentials ------> Secret Protection
         |
         `-- Reads external content ----> Content Trust

The coding assistant should refer to the Secure Template's security guidance, policies, and reusable security mechanisms when determining how these controls should be implemented.

The coding assistant should not invent a new security architecture for every application.

This step establishes the INITIAL SECURITY BASELINE before development.


STEP 5 - BUILD THE APPLICATION WITH SECURITY CONTROLS
=====================================================

The coding assistant can now build the application based on the requirements in Context/.

Security should be built together with the product. It should not be added only after the application is finished.

Instead, each product capability should be implemented together with its relevant security control.

    PRODUCT CAPABILITY                 SECURITY

    Build fetch_news             +     Egress Control
    Build agent tools            +     Tool Permission
    Use API credentials          +     Secret Protection
    Process external articles    +     Content Trust

Example - Egress Control
------------------------

Suppose the developer says:

    "The News Agent can access TechCrunch and GitHub."

This requirement is recorded in Context/.

The coding assistant identifies that the application needs external network access. The Secure Template indicates that Egress Control applies.

The coding assistant therefore builds the news-fetching capability using the provided runtime security mechanism and configures the approved destinations.

    Product Requirement
    Access TechCrunch and GitHub
              |
              v
    Egress Control Required
              |
              v
    Configure Approved Destinations
              |
              v
    Build fetch_news through Runtime Security
              |
              v
        At Runtime:

    techcrunch.com  ---> ALLOW
    github.com      ---> ALLOW
    unknown-site    ---> BLOCK

Security During Development
---------------------------

The initial security requirements are identified before development starts. However, security must continue to be checked while the application is being developed.

If a new capability is added, the coding assistant should determine whether the security requirements have changed.

For example:

    New Requirement:
    "Send the news digest by email."
              |
              v
    New capability detected
              |
              v
    Check security impact
              |
              +--> New tool?
              +--> New network destination?
              +--> New credentials?
              +--> Sensitive information?
              |
              v
    Update security controls if required
              |
              v
    Build the new capability

Therefore:

    Security is identified before development starts,
    applied during development,
    and updated whenever the product changes.


RUNTIME SECURITY
================

The security controls must be part of the real application execution path.

Having security files in the project is not enough.

For example:

    User
      |
      v
     LLM
      |
      | proposes an action
      v
    Tool Call
      |
      v
    +----------------------+
    |   Runtime Security   |
    |                      |
    | Tool Permission      |
    | Egress Control       |
    | Secret Protection    |
    +----------+-----------+
               |
          ALLOW or BLOCK
               |
               v
           Real Tool
               |
               v
        External Content
               |
               v
        +---------------+
        | Content Trust |
        +-------+-------+
                |
                v
               LLM

The key principle is:

    The AI model can propose an action.
    Security mechanisms decide whether that action is allowed to happen.


STEP 6 - VERIFY THE PRODUCT AND SECURITY
========================================

After development, verify both sides of the application:

                 VERIFICATION
                      |
              +-------+-------+
              |               |
              v               v
        Product Tests    Security Tests
              |               |
              v               v
        Does it work?    Is it protected?

For the AI News Agent:

    PRODUCT TESTS                  SECURITY TESTS

    Fetch news             PASS    Approved tool       -> ALLOW
    Generate digest        PASS    Unapproved tool     -> BLOCK
    Access GitHub          PASS    Approved website    -> ALLOW
    Save digest            PASS    Unapproved website  -> BLOCK
                                  Secret leakage      -> BLOCK
                                  Suspicious content  -> BLOCK

Run the project health check again:

    ./init.sh

Security verification should prove that the security mechanism actually prevented the prohibited action, not simply that the LLM said it was blocked.

For example:

    LLM requests an unapproved tool
              |
              v
        Runtime Security
              |
              v
        NOT APPROVED
              |
              v
           BLOCKED
              |
              v
    Real tool does NOT execute
              |
              v
             PASS


STEP 7 - DEVELOPER REVIEW AND DEPLOYMENT
========================================

Before deployment, the developer reviews the completed application.

Confirm that:

- The product behaves as expected.
- The required tools are correct.
- The approved external destinations are correct.
- The required security controls are active.
- Security tests pass.
- The real application uses the runtime security path.
- There is no unintended path that bypasses runtime security.
- Any remaining security gaps or risks have been reviewed.


THE COMPLETE PROCESS
====================

    COPY SECURE TEMPLATE
             |
             v
    DESCRIBE THE PRODUCT
             |
             v
    DEVELOPER <--> CODING ASSISTANT
    Clarify the requirements
             |
             v
    RECORD REQUIREMENTS
         in Context/
             |
             v
    IDENTIFY INITIAL
    SECURITY REQUIREMENTS
             |
             v
    BUILD THE APPLICATION
             |
        +----+----+
        |         |
        v         v
     Product    Security
     Features   Controls
        |         |
        +----+----+
             |
             v
          VERIFY
        +----+----+
        |         |
        v         v
     Product    Security
      Tests      Tests
        |         |
        +----+----+
             |
             v
      REVIEW & DEPLOY

In simple terms:

    Developer defines what to build.

    Coding assistant clarifies the requirements and builds the application using the Secure Template.

    Security requirements are identified before development, applied while the application is being built, and verified before deployment.

    At runtime, the AI model may propose an action, but the security mechanisms make the final ALLOW or BLOCK decision.
