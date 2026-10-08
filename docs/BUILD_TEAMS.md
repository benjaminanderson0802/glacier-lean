# Build: from your vision to a team that finishes it

Owner's goal (2026-10-08): Build interviews you until it understands the whole vision, designs the most efficient AI team and plan for that project, and the team runs in Automations without stopping until it is done (except owner approvals). The designer of the team does not take part in the build.

This design follows what has been shown to work in practice, not role names. Sources are listed at the end; vendor numbers are self-reported.

## 1. Interview -> Spec (Build tab)
- The interviewer keeps asking until it can state the vision back and the owner confirms it: goal, users, what "done" looks like, must-haves, out of scope, constraints (money, time, hardware, accounts), examples, risks.
- Output is a **Spec**: requirements written as checkable statements ("WHEN ... THE SYSTEM SHALL ..."), an explicit out-of-scope list, and an end-to-end acceptance check. The owner approves it. Saved to memory; every check refers back to it. [Kiro specs; Claude Code best practices]

## 2. Designer sets up the project, then leaves
The **Designer** (owner's rule: it never works on the build itself) produces, from the Spec:
- **Feature list**: a long list of small, testable features, each marked failing, stored as structured data. Workers can never edit it except through the evaluator's pass (enforced in code). [Anthropic long-running harness]
- **Harness**: workspace/repo, a startup script, a smoke test, mechanical checks (tests, linters, type checks with fix-oriented error messages), a progress log and a decision log. [Anthropic; OpenAI harness engineering]
- **Team shape sized to the project**, not a fixed cast. Default is the smallest team that works: a **Lead** (picks the next task each cycle and judges progress), **Builder(s)**, and a separate skeptical **Evaluator**; plus a **Researcher** only for breadth-first work (finding options, reading docs) and a clean-context **Reviewer** for risky changes. More roles only when the Spec needs them; role-play casts fail often. [MAST study arXiv 2503.13657; Cognition]
- **Supervisors**: the Designer appoints the Lead/Evaluator as its supervisors and hands off. It returns only if the owner asks for a re-plan.
The owner approves the team and plan once.

## 3. The loop (lives in Automations, runs until done)
Each cycle, enforced by Glacier's code, not by prompts:
1. **Lead** picks the next ready feature, sized like a few hours of junior work, and writes its **contract** with the Evaluator: exact pass criteria.
2. **Builder** starts with a **fresh context** (Spec excerpt, the feature, its contract, the progress log, git history; nothing else), implements, runs the checks, commits on its own branch/worktree, and updates the progress log.
3. **Evaluator** (fresh context, tuned to be skeptical, runs real tests and the app) grades against the contract. Only an Evaluator pass marks the feature passing. [Anthropic harness design]
4. **Final objective check**: before "done", the whole Spec's acceptance check runs; the biggest measured gain in role-based systems came from checking against the original objective. [MAST]
Code changes stay in one thread per area; extra agents add research and review, not conflicting parallel edits. [Cognition]

## 4. Never stalling (code-enforced)
- Max 3 build/evaluate attempts per feature -> reset context with a handoff note -> Lead re-plans the feature smaller.
- After 2 re-plans -> a claim to the owner with evidence (diff, logs, failing check); the rest of the plan keeps going.
- Retries, checkpoints and resume-after-crash are handled by Glacier's durable workflows; every cycle starts fresh to avoid drift; the Lead checks overall progress each cycle. [Cursor scaling agents; Claude Code best practices]

## 5. Engines
- **Local models (one at a time)**: strictly sequential; smaller features; more fixed steps and fewer open decisions; rely harder on tests and linters. Each task the worker takes on its role with a fresh context and clears it afterwards. Optional: send planning and final evaluation to a stronger engine if one is available (the main model still sets the quality ceiling). [Cognition; inference: little public evidence on long runs with small models]
- **Subscription CLI / API (parallel)**: Lead + independent Builders + Evaluator, each Builder in its own git worktree on tasks that do not depend on each other; start with 3-5 workers and add more only while merge conflicts and evaluator failures stay low; strong models for Lead and Evaluator, cheaper for Builders. [Cursor; Claude Code /batch guidance]

## 6. Upkeep
A periodic clean-up pass against "golden rules" checked by linters; re-check the harness when models change. [OpenAI harness engineering]

## Sources
- Anthropic, Effective harnesses for long-running agents: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, Harness design for long-running apps: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic, Multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
- Cognition, Don't build multi-agents: https://cognition.com/blog/dont-build-multi-agents ; Multi-agents working: https://cognition.com/blog/multi-agents-working
- Cursor, Scaling agents: https://cursor.com/blog/scaling-agents
- OpenAI, Harness engineering: https://openai.com/index/harness-engineering/
- Claude Code best practices: https://code.claude.com/docs/en/best-practices
- Cognition, Devin annual performance review 2025: https://cognition.com/blog/devin-annual-performance-review-2025 ; GitHub Copilot agent guidance: https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results
- Kiro specs: https://kiro.dev/docs/specs/concepts
- Why do multi-agent LLM systems fail? (MAST): https://arxiv.org/abs/2503.13657
- Agentless: https://arxiv.org/abs/2407.01489 ; Stripe Minions: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
