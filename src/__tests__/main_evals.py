
import os,sys
import asyncio
from google.adk.agents import Agent

REPO_ROOT = os.getcwd()
SRC = os.path.join(REPO_ROOT, 'src')
PKG = os.path.join(SRC, 'multi_tool_agent')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if PKG not in sys.path:
    sys.path.insert(0, PKG)
from google.adk.runners import Runner,InMemoryRunner
from multi_tool_agent.MultiAgent import get_flow_agent
from multi_tool_agent.AgentConfig import base_model as base_model


agent=get_flow_agent()
eval_cases = [
    {"input": "I have a birthday party to attend next tuesday", "expected": "event added"},
    {"input": "what are my events  next week", "expected": "birthday"},
    {"input": "Add an alarm to take my medcine at 9 PM for next one week", "expected": "recurring event"},
]


async def run_eval_cases(eval_cases, agent):
    runner = InMemoryRunner(agent=agent, app_name="agents")
    results = []
    for case in eval_cases:
        output = await runner.run_debug(case["input"])

        texts = []
        for event in output:
            if event.content and event.content.parts:
                texts.extend([
                    part.text
                    for part in event.content.parts
                    if part.text and part.text.strip().lower() != "none"
                ])
        text = " \n".join(texts)

        results.append({
            "input": case["input"],
            "output": text,
            "expected": case["expected"],
            "pass": case["expected"].lower() in text.lower()
        })
    return results

async def run_evals():
    results = await run_eval_cases(eval_cases, agent)
    for r in results:
        print(f"Input: {r['input']}")
        print(f"Output: {r['output']}")
        print(f"Expected: {r['expected']}")
        print(f"Pass: {r['pass']}")
        print("-" * 40)
    return results
async def main():
    results = await run_eval_cases(eval_cases, agent)
    judged = []
    for case in results:
        verdict = await judge_case(case)
        judged.append({**case, "verdict": verdict})
    for r in judged:
        print(r)   

judge_agent= Agent(
        model=base_model,
        name="judge_agent",
        description="An agent that judges whether the agent output meets the expected behavior.",
        )
async def judge_case(case):

    judge_prompt = f"""
    You are an evaluator. Given the agent's output and the expected behavior,
    decide if the output satisfies the expectation.

    Input: {case['input']}
    Expected: {case['expected']}
    Output: {case['output']}

    Answer only with PASS or FAIL, and a one‑sentence justification.
    """


    runner = InMemoryRunner(agent=judge_agent, app_name="judge")
    output = await runner.run_debug(judge_prompt)

    # Collect text parts from the events
    texts = []
    for event in output:
        if event.content and event.content.parts:
            texts.extend([
                part.text
                for part in event.content.parts
                if part.text and part.text.strip().lower() != "none"
            ])
    return " ".join(texts)


if __name__ == "__main__":
    asyncio.run(main())