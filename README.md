# Secure AI Application Template

## What is this project?

This project helps developers build AI applications securely without having to design the security architecture from scratch.

The goal is simple:

> **Developers focus on what the product should do. The Secure Template provides the security foundation around it.**

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

## The Basic Development Process

```text
1. Copy the Secure Template
          |
          v
2. Describe and clarify the product
          |
          v
3. Record the requirements in Context/
          |
          v
4. Coding assistant develops the AI application
          |
          v
5. Developer review and deployment
```

Security is not something added after the application is finished. The Secure Template is intended to guide and protect the development process while the coding assistant builds the application.

## Step 1 - Copy the Secure Template

Start every new AI application from a fresh copy of the template.

For example, to create a project called `claims-agent`:

```bash
cp -r template/ claims-agent/
cd claims-agent/
chmod +x init.sh
./init.sh
```

### What is the health check?

<span style="color:blue"><strong>TO BE CLARIFIED:</strong> What exactly does the initial health check verify, which checks are expected to fail on a fresh template, and what must be completed before the health check can PASS?</span>

The health check checks whether the project has been properly configured and whether the required project and security checks pass.

The first health check is expected to **FAIL**. This is intentional.

A newly copied template does not yet know what application you are building. For example, it does not know:

- What is the purpose of the application?
- Which AI model or framework will be used?
- What tools does the application need?
- Which external systems does it need to access?
- Which security controls are relevant?

The health check reports what is still missing.

```text
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
```

At this stage, **FAIL is the correct result**. Continue to Step 2.

## Step 2 - Describe and Clarify the Product

<span style="color:blue"><strong>TO BE CLARIFIED — Where does the developer describe the product?</strong></span>

<span style="color:blue">After copying the Secure Template, where should the developer provide the initial product description? Should the developer describe the product directly in the chat with the coding assistant, or should the developer first write the description into a specific project file? If a file is required, which file should be used? If the product description starts in the chat, should the coding assistant then record the clarified requirements into the appropriate project files?</span>

<span style="color:blue"><strong>TO BE CLARIFIED — How does the coding assistant know that clarification is required?</strong></span>

<span style="color:blue">What tells the coding assistant that it must clarify the product requirements before starting substantial development? Is there a specific instruction file, prompt, command, or workflow that triggers this behavior? What categories of questions should the coding assistant ask, such as product functions, LLM/framework, required tools, external systems, data sources, credentials, deployment environment, and security-relevant requirements? Is there an existing file or checklist that defines these clarification questions?</span>

<span style="color:blue"><strong>TO BE CLARIFIED — Which instructions does the coding assistant follow first?</strong></span>

<span style="color:blue">When the coding assistant first opens a newly copied project, which file is it expected to read first? What tells it to follow the sequence of understanding the product, clarifying requirements, recording the requirements, developing the application, and completing the required verification? Is this root `README.md` intended mainly for the human developer, or is it also intended to control the coding assistant's workflow? If `README.md` is mainly developer documentation, which file contains the authoritative instructions that the coding assistant must follow?</span>

Before coding starts, describe what you want to build.

The developer does not need to provide a complete technical specification at the beginning. Start with the product idea.

For example:

> Build an AI News Agent that collects AI and cybersecurity news, selects four important stories, generates a digest, and allows users to ask questions about the news.

### Coding Assistant Clarifies the Requirements

<span style="color:blue"><strong>TO BE CLARIFIED — What tells the coding assistant to perform this step?</strong></span>

<span style="color:blue">Which project instruction tells the coding assistant to read the product description and ask questions when information is incomplete? Which files must it read before asking those questions, and where is the required reading order defined? After clarification is complete, what instruction tells the coding assistant what to do next?</span>

The coding assistant should read the product description and ask questions when important information is missing.

For example:

- Which news sources should the agent access?
- Which LLM and agent framework should it use?
- Does the agent need to save the digest?
- Does it use API credentials?
- Should it access any website, or only approved websites?
- Where will the application be deployed?

The purpose is to make sure the coding assistant understands the product before substantial coding begins.

These questions can also reveal security-relevant requirements. For example:

```text
Developer says:
"The News Agent should access TechCrunch and GitHub."

                |
                v

    Product Requirement
    Fetch information from TechCrunch and GitHub

                +

    Security Requirement
    Network access should be limited to approved destinations
```

The developer describes what the product needs. The Secure Template and coding assistant translate those requirements into the appropriate product implementation.

## Step 3 - Record the Requirements in Context/

<span style="color:blue"><strong>TO BE CLARIFIED — Who records the requirements in `Context/`?</strong></span>

<span style="color:blue">After the developer and coding assistant clarify the product, who is responsible for updating the files under `Context/`? Should the coding assistant automatically write the agreed requirements into these files, or does the developer need to update them manually? If the coding assistant is responsible, what instruction tells it which `Context/` file each type of requirement belongs in?</span>

The clarified requirements should be recorded under:

```text
Context/
|-- product-design.md
|-- ai-stack.md
|-- architecture.md
`-- deployment.md
```

The `Context/` folder is the project's source of truth for what should be built.

It should describe things such as:

- Product purpose
- Main functions
- AI model and framework
- Required tools
- External systems and websites
- Deployment environment
- Important product constraints

For example:

```text
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
```

The coding assistant should use `Context/` when building the application.

If important information is missing, it should ask the developer rather than silently guessing.

## Step 4 - Coding Assistant Develops the AI Application

<span style="color:blue"><strong>TO BE CLARIFIED — How does the coding assistant know that it is ready to start development?</strong></span>

<span style="color:blue">How does the coding assistant determine that the product requirements are sufficiently complete and development can begin? What prevents it from making assumptions and starting to code while important requirements are still unresolved? Is there a defined checkpoint, status, command, or instruction that marks the transition from requirement clarification to implementation?</span>

<span style="color:blue"><strong>TO BE CLARIFIED — Which files define the coding assistant's development workflow?</strong></span>

<span style="color:blue">Before writing application code, which project files must the coding assistant read? Does it need to read `Context/`, `AGENTS.md`, `SECURITY.md`, governance policies, runtime-security instructions, or other files? Where is this required reading order and development procedure defined? How is the same workflow communicated consistently to different coding assistants such as Claude Code, Cursor, Codex, Copilot, or Kiro?</span>

Once the requirements are sufficiently clear and recorded in `Context/`, the coding assistant develops the application using the Secure Template.

The detailed development, security-control selection, runtime enforcement, and verification mechanisms are provided by the template itself and its supporting instructions.

The developer should not need to design these mechanisms from scratch.

If a new product capability is introduced during development, the coding assistant should update the relevant project requirements and follow the template instructions before implementing the change.

## Step 5 - Developer Review and Deployment

Before deployment, the developer reviews the completed application and confirms that the product meets the intended requirements and is ready for the target environment.

## The Complete Process

```text
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
CODING ASSISTANT
DEVELOPS APPLICATION
         |
         v
DEVELOPER REVIEW
& DEPLOYMENT
```

In simple terms:

> **The developer defines what to build. The coding assistant clarifies the requirements and develops the AI application using the Secure Template. The template provides the security foundation throughout the development process.**
