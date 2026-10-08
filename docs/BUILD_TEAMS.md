# Build: from your vision to a running team

Owner's design (2026-10-08). The Ask tab becomes **Build**.

## 1. Interview (Build tab)
A conversation with the AI until it fully understands the project. The interviewer grills the owner: goal, who it is for, what "done" means, must-haves and must-nots, constraints (money, time, hardware, accounts), examples liked and disliked, risks. It keeps asking until it can state the vision back and the owner confirms it. The confirmed **Vision** is saved as a memory note and becomes the reference every role checks against.

## 2. Plan (the Planner designs the team, then steps away)
The **Planner** turns the Vision into:
- **Roles**: the team needed start to finish (for example architect, builders, tester, reviewer, writer, supervisors, a governor). Each role has a short charter: what it does, what it may change, what it must hand over, which checks prove its work.
- **Work plan**: tasks with order and dependencies, each with acceptance checks that an independent checker runs. Tasks are small enough to finish in one sitting.
- **Flow guards**: what to do when work stalls (stuck task becomes a claim, alternate route, re-split), so there are no bottlenecks or rabbit holes; limits on retries and time per task.
- **Supervisors**: the Planner appoints one or more supervisors to oversee the team on its behalf (review results, unblock, re-assign).
The owner approves the plan (one approval). **The Planner does not take part in the build.** It is not a member of the team and does not run tasks or supervise; it only returns if the owner asks for a re-plan.

## 3. Run (the team lives in Automations)
Automations hold not only closed loops and pipelines but also **running teams**. A team runs its loop until the work plan is complete, stopping only for approvals the plan marked as needing the owner.
- **Local models**: one worker at a time. Each turn the next ready task is picked, the worker "puts on the mask" of that task's role (role charter + task + only the relevant memory and files), works with a fresh context, hands over, and its memory is cleared before the next task.
- **Subscription CLI or API**: several workers in parallel (a limit the owner sets), each in its own isolated workspace.
- **Supervisors** review each handover against its checks; the **governor** checks every result against the Vision and the plan and stops drift.
- Progress, costs, and what needs the owner are visible on Home and in the team's view.

## 4. Proof
A build is done only when every task's checks pass and the governor confirms the Vision's "done" list is met. The same verification rules as the rest of Glacier (no false "done").

## Engine choices and controls

Build uses the same engines as Ask: Codex, Claude Code, Gemini CLI, an OpenAI-compatible API, Anthropic API, or a local Ollama model. API keys stay in the operating-system keyring. An API run also needs its allowed host and monthly cap configured in Settings > Models. Glacier reserves the estimated cost before each request and refuses a request that would pass the cap; the default cap remains $0 under decision D4.

Codex workers use the Codex workspace runner. Other engines receive a fresh task brief and the relevant workspace files, then return a unified patch that Glacier checks before applying. Each task still gets its own independent review and acceptance checks. Subscription and API teams use separate Git worktrees and run three to five workers at once. Local teams run one worker at a time and receive a fresh task context.

Pause finishes the tasks already running and then waits before starting more. Resume starts from the saved task states and leaves completed tasks alone. Stop terminates active worker processes, marks the team stopped, and leaves its worktrees on disk for inspection. Pause, resume, and stop are recorded in the audit log.
