# Generic Instructions for Creating C4 Architecture Documentation for a business application with multiple GitHub repositories.

## Purpose

Use this instruction set to create one architecture document that covers a single business application composed of multiple repositories.

This instruction set is for cross-repo architecture only (not single-repo documentation).

## Mandatory trigger input

When these instructions are triggered, the requester **must provide links to all repositories in scope**.

Required input:
- Business application name
- Repository links in scope (one link per repository)

If repository links are not provided, stop and request them before drafting.

## Expected outputs

At minimum, produce one Markdown file with this naming pattern:
- `c4_<business_application_name>_architecture.md`

For example, for business application `fleet_operations`:
- `c4_fleet_operations_architecture.md`

The file must include clearly separated sections for:
- Index/overview
- Repository landscape and ownership map
- C1 system context (application-level)
- C2 container view (cross-repo)
- C3 component views (per key repository/component)
- Cross-repo integration and data flow view
- Deployment view
- Governance and maintenance

## Process

### 1) Confirm scope from provided repository links

Build an explicit in-scope list using the provided links and include:
- repository name,
- repository purpose in the business application,
- primary runtime role (frontend, backend, integration, infrastructure, library, etc.),
- owner/team (if available).

Do not infer additional repositories unless explicitly approved.

### 2) Discover architecture facts across repositories

Collect information from each in-scope repository:
- source code and folder structure,
- runtime/deployment config (`docker-compose`, infra manifests, app settings),
- existing READMEs and architecture docs,
- APIs, events, queues, scheduled jobs, and shared contracts,
- identity/authentication and authorization model.

Document only what is true in the repositories now.

### 3) Define cross-repo C4 scope and boundaries

Decide and state clearly:
- system of interest (business application boundary),
- external actors/systems,
- runtime containers and which repository owns each container,
- major component boundaries per container,
- integration patterns between repositories (sync, async, batch),
- environments and deployment topology to include.

### 4) Ask customization questions before drafting

Before writing final docs, ask and capture answers for:
1. **Audience** — Who is this for (new engineers, architects, operations, auditors)?
2. **Detail level** — High-level only, balanced, or deep technical detail?
3. **Key content priorities** — Which topics must be emphasized (security, integrations, eventing, deployment, ownership, ADR links, etc.)?
4. **Out-of-scope content** — What should be intentionally excluded?
5. **Diagram style constraints** — Mermaid style preferences, naming conventions, and label language.
6. **Maintenance model** — Who owns updates and when docs must be updated.

If answers are missing, use conservative defaults and document assumptions.

### 5) Place cross-cutting architecture guidance in the C4 document

Include the following directly in the document:
- **System at a glance + business capability map** in the index/overview section.
- **Repository landscape and dependency map** in the repository landscape section.
- **Runtime interaction summary** in the C2 container section.
- **Critical cross-repo data flows and trust boundaries** in the integration section.
- **Deployment and environment notes** in the deployment section.
- **Ownership, maintenance expectations, and PR checklist** in governance.

These sections must reflect customization answers from step 4.

### 6) Produce the C4 document

Create each section with:
- short purpose section,
- Mermaid diagram,
- concise explanatory notes,
- consistent naming across the full document.

Keep each view focused:
- C1: actors, external systems, and overall application boundary,
- C2: runtime containers across repositories and responsibilities,
- C3: component-level internals for key repositories/components,
- Integration: cross-repo contracts, protocols, and data movement,
- Deployment: environments, topology, and operational concerns.

For **C1 system context (application-level)**, add a stakeholder completeness check:
- List all known system users/stakeholders across in-scope repositories and platform context.
- Ask this verification question before finalizing: **"Are any system users or stakeholder groups missing from the C1 system context (for example: end users, operators, support, maintainers, security/compliance, external partners, or platform teams)?"**
- If new stakeholders are identified, update both the C1 diagram and notes.

### 7) Validate diagrams and consistency

Check that:
- Mermaid diagrams render without parse errors,
- terminology is consistent across sections,
- repository names and links are consistent everywhere,
- internal links/anchors are valid,
- no contradictions exist between diagrams and notes.

### 8) Add maintenance guidance

Ensure docs define:
- triggers for required updates,
- review expectations in PRs,
- ownership/fallback responsibility,
- where architecture-impact notes belong in PR templates/descriptions,
- expected section update behavior when repositories, interfaces, or runtime topology change.

## Writing standards

- Be business-application and repository specific; avoid generic filler text.
- Keep language clear and concise.
- Use stable capability and component names over temporary implementation details.
- Explicitly map each major container/component to its source repository.
- Use Mermaid syntax compatible with GitHub rendering. Validate the syntax, see https://docs.github.com/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams#creating-mermaid-diagrams
- Simplify long labels for better diagram readability in GitHub’s renderer.
- If uncertain, ask questions explicitly.

## Optional starter template for customization intake

Use these prompts with stakeholders before finalizing docs:

- "Please provide the full list of repository links in scope for this business application."
- "What are the top 3 architecture concerns this documentation must clarify across repositories?"
- "What level of detail is expected: executive, engineering, or implementation-deep?"
- "Which cross-repo integrations and data flows are most critical to visualize?"
- "Do we need explicit sections for security boundaries, compliance, or threat surfaces?"
- "Should ownership and maintenance requirements be strict (PR-blocking) or advisory?"
- "Are any system users or stakeholder groups missing from the C1 system context diagram and notes?"