"""Smoke test: MAF workflow with a LOOP, file checkpoints, human approval, and resume in a fresh process."""
import asyncio, sys, shutil, os
from dataclasses import dataclass
from agent_framework import (Executor, WorkflowBuilder, WorkflowContext, FileCheckpointStorage,
                             handler, response_handler)

CK = "ckpt"

@dataclass
class Work:
    n: int

@dataclass
class Approval:
    summary: str

class Builder(Executor):
    @handler
    async def build(self, msg: Work, ctx: WorkflowContext[Work]) -> None:
        print(f"  builder: iteration {msg.n}")
        await ctx.send_message(Work(msg.n + 1))

class Checker(Executor):
    @handler
    async def check(self, msg: Work, ctx: WorkflowContext[Work]) -> None:
        if msg.n < 3:
            print(f"  checker: n={msg.n} not done -> loop back")
            await ctx.send_message(Work(msg.n))
        else:
            print(f"  checker: n={msg.n} done -> ask human")
            await ctx.request_info(Approval(f"finished after {msg.n} loops"), bool)

    @response_handler
    async def on_answer(self, original: Approval, approved: bool, ctx: WorkflowContext[Work, str]) -> None:
        await ctx.yield_output(f"human said {approved} to: {original.summary}")

def build():
    b, c = Builder(id="builder"), Checker(id="checker")
    return (WorkflowBuilder(start_executor=b, max_iterations=50, name="glacier-loop-test",
                            checkpoint_storage=FileCheckpointStorage(CK, allowed_checkpoint_types=["__main__:Work", "__main__:Approval"]))
            .add_edge(b, c).add_edge(c, b).build())

async def phase1():
    res = await build().run(Work(0))
    reqs = res.get_request_info_events()
    print("phase1 pending approvals:", len(reqs), "state:", res.get_final_state())
    with open("req_id", "w") as f: f.write(reqs[0].request_id)

async def phase2():
    storage = FileCheckpointStorage(CK, allowed_checkpoint_types=["__main__:Work", "__main__:Approval"])
    latest = await storage.get_latest(workflow_name="glacier-loop-test")
    rid = open("req_id").read()
    res = await build().run(checkpoint_id=latest.checkpoint_id, checkpoint_storage=storage, responses={rid: True})
    print("phase2 outputs:", res.get_outputs())

if __name__ == "__main__":
    if sys.argv[1] == "1":
        shutil.rmtree(CK, ignore_errors=True)
        asyncio.run(phase1())
    else:
        asyncio.run(phase2())
