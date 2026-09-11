# Secure AI Application Template

## What is this project?

This project helps developers build AI applications and AI agents securely without having to design the security architecture from scratch.

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

### What is the health check?(need to double check later!)

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

-- developer need to go where to describe the product?? in the chatting box with coding assistant or need to modify some file? if needed, which file? if need coding assistant prompt to ask questions, how would coding assistant know that he should ask questions? and ask which kind of questions? any files for coding assistant to follow?

-- coding assistant clarify the product, how could coding assistant know that he should clarify the product, coding assistant will read which file first, the steps for coding assistant to follow is this main readme.md? 

Before coding starts, describe what you want to build.

The developer does not need to provide a complete technical specification at the beginning. Start with the product idea.

For example:

> Build an AI News Agent that collects AI and cybersecurity news, selects four important stories, generates a digest, and allows users to ask questions about the news.

### Coding Assistant Clarifies the Requirements

The coding assistant should read the product description and ask questions when important information is missing. (the same, coding assistant should read, but which file is asking coding assistand to read, and after that do what, which file is for coding assistant to read?)

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
???? who will record the requirement in context, will coding assistant record this?


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
