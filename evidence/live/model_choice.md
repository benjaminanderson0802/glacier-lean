# Local model choice — 2026-10-07

## Recommendation

No candidate reached the requested 8/10 pass threshold under the strict independent output checks. `llama3.2:3b` had the highest score (4/10) and is the best under 5 GB among these candidates. It is set as the best-effort low-resource and standard-mode default; it does **not** pass the low-resource target. A follow-up candidate search is needed to meet that target.

## Evaluation setup

- Ollama was already installed (`ollama --version`: 0.40.0); no installer was run. Its server was not running, so I started it on `127.0.0.1:11434`. No cloud model was used. The four models were downloaded with `ollama pull`; all four were absent before this evaluation.
- Host: Linux x86_64 VM, AMD EPYC 7763, 4 logical CPUs, 15 GiB RAM visible, no swap. This is a constrained shared VM, not a physical modest PC; measurements should be treated as a reference point.
- Backend: this worktree’s FastAPI app at `127.0.0.1:8427`, isolated `GLACIER_HOME=/tmp/w11-model-bench`. For every prompt the flow had a real `local_ai` node using the candidate model, followed by a `check` node with `exit_code == 0`, matching the live test’s flow.
- Each model received the same ten prompts in the same order. The separate rubric compared each node’s raw output with the expected answer after whitespace normalization and trimming surrounding backticks. It required the exact answer requested, so case changes, Markdown fences, explanations, wrong values and timeouts failed. Run JSON, raw node output, expected value and task run ID are in the results below.
- RAM is the Ollama server + descendant runner peak RSS minus the idle server RSS, sampled every 100 ms during each model’s ten backend runs.
- CPU generation speed is measured separately from answer scoring with one identical Ollama chat request per model, using the response’s `eval_count / eval_duration` (64-token cap). This isolates generation speed from DBOS and HTTP polling.
- Download size is Ollama’s pulled quantized artifact size. The sizes and licenses are shown on each linked Ollama model page. All four licenses are among the terms allowed by this card.

## Results

| Model | License | Download | Peak model RSS | CPU generation | Independent pass rate |
|---|---|---:|---:|---:|---:|
| [`qwen3:0.6b`](https://ollama.com/library/qwen3:0.6b) | Apache-2.0 | 522 MB | 1,090 MB | 47.30 tok/s | 1/10 |
| [`qwen3:1.7b`](https://ollama.com/library/qwen3:1.7b) | Apache-2.0 | 1.4 GB | 1,849 MB | 21.92 tok/s | 2/10 |
| [`llama3.2:3b`](https://ollama.com/library/llama3.2:3b) | Llama 3.2 Community License | 2.0 GB | 2,514 MB | 11.38 tok/s | 4/10 |
| [`gemma3:1b`](https://ollama.com/library/gemma3:1b) | Gemma Terms of Use | 815 MB | 1,769 MB | 23.66 tok/s | 1/10 |

The smallest passing 8/10 candidate **does not exist in this sample**. `llama3.2:3b` is the best observed standard-mode model under 5 GB and is also the best-effort default for low-resource mode, but it scored only 4/10. It uses about 2.5 GB runner RSS on this host; the target machine should have enough memory for the model plus Glacier and the operating system.

## Task set and expected answers

| Task | Prompt | Expected output |
|---|---|---|
| classify_billing | Classify the message into exactly one lowercase label: billing, technical, or sales. Message: "I was charged twice for my subscription." | `billing` |
| classify_technical | Classify the message into exactly one lowercase label: billing, technical, or sales. Message: "The app crashes every time I upload a PDF." | `technical` |
| classify_sales | Classify the message into exactly one lowercase label: billing, technical, or sales. Message: "Can I get a quote for 40 team seats?" | `sales` |
| extract_json | Extract the fields from this note. Reply with one JSON object only with keys name and date. Note: "Please book a call for Mira Chen on 2026-11-14." | `{"name":"Mira Chen","date":"2026-11-14"}` |
| arithmetic | Reply with only the integer answer to 19 + 23. | `42` |
| sort_csv | Sort these words alphabetically and reply with only a comma-separated list: pear, apple, plum. | `apple,pear,plum` |
| urgent_route | Choose exactly one lowercase label, urgent or normal. Message: "Our production service is down for every customer." | `urgent` |
| nonurgent_route | Choose exactly one lowercase label, urgent or normal. Message: "Please change my profile picture when convenient." | `normal` |
| missing_field | A work request must contain a person, a date, and a place. Reply with only the missing field name. Request: "Meet Alex at the library on Friday." | `date` |
| slug | Turn this title into a lowercase hyphen-separated filename slug, with no extension: "Quarterly Safety Review" | `quarterly-safety-review` |

## Raw outputs: `qwen3:0.6b`

| Task | Run ID | Result | Raw local-AI output |
|---|---|---|---|
| classify_billing | `b3dff8a3e620` | FAIL | `The message: **"I was charged twice for my subscription."** **Classification:** **billing**.` |
| classify_technical | `b3f714e75759` | FAIL | `The message is classified as **technical**.` |
| classify_sales | `de58a17bf4c7` | FAIL | `The message is: **sales**.` |
| extract_json | `5eec13d9ffb0` | FAIL | `\`\`\`json {"name": "Mira Chen", "date": "2026-11-14"} \`\`\`` |
| arithmetic | `2f67ae58e36b` | FAIL | `19 + 23 = 42 **Integer answer:** 42` |
| sort_csv | `a8b9c3bca116` | FAIL | `apple, pear, plum` |
| urgent_route | `faf57c8d1c40` | FAIL | `Normal` |
| nonurgent_route | `8a56dd341b0a` | FAIL | `**Urgent**` |
| missing_field | `71c60229c781` | FAIL | `- person: person - date: date - place: place` |
| slug | `622e27adceaf` | PASS | `quarterly-safety-review` |

## Raw outputs: `qwen3:1.7b`

| Task | Run ID | Result | Raw local-AI output |
|---|---|---|---|
| classify_billing | `33547ab36e47` | FAIL | `**billing**` |
| classify_technical | `b7d47289bbce` | FAIL | `**Sales**` |
| classify_sales | `26f75e4571da` | FAIL | `**Sales**` |
| extract_json | `2c99e853d212` | FAIL | `{"name": "Mira Chen", "date": "2026-11-14"}` |
| arithmetic | `c93b2321f93a` | FAIL | `19 + 23 = 42` |
| sort_csv | `b23a63796929` | FAIL | `Local AI took longer than 600 seconds.` |
| urgent_route | `446663083d9b` | FAIL | `**Normal** The message indicates that the service is currently down, but it doesn't specify the urgency. Since the situation is likely critical for customers, the appropriate label would be **urgent**. However, if the context implies a general service outage without immediate impact, **normal** might be more appropriate. **Final Answer: Urgent**` |
| nonurgent_route | `c69551f193f3` | FAIL | `**Normal** The message "Please change my profile picture when convenient." is not urgent, so the appropriate label is **Normal**.` |
| missing_field | `2c5547415cde` | PASS | `date` |
| slug | `3cd92623b1d9` | PASS | `quarterly-safety-review` |

## Raw outputs: `llama3.2:3b`

| Task | Run ID | Result | Raw local-AI output |
|---|---|---|---|
| classify_billing | `2f03715130a6` | FAIL | `technical` |
| classify_technical | `f1783303f950` | FAIL | `billing is not relevant, as the message does not mention payment or financial issues. Technical is the most suitable classification, as the message describes a technical problem with the app (crashing) and a specific action that triggers the issue (uploading a PDF).` |
| classify_sales | `42d01005adf7` | PASS | `sales` |
| extract_json | `381fe9308bd5` | FAIL | `Here is the JSON object with the extracted fields: { "name": "Mira Chen", "date": "2026-11-14" }` |
| arithmetic | `069237d27fed` | PASS | `42` |
| sort_csv | `e219c3e7c124` | FAIL | `apple, pear, plum` |
| urgent_route | `517508e38b50` | PASS | `urgent` |
| nonurgent_route | `7bcb3914133c` | FAIL | `urgent` |
| missing_field | `7996aa5bef98` | FAIL | `Date` |
| slug | `bccdfb9e3de1` | PASS | `quarterly-safety-review` |

## Raw outputs: `gemma3:1b`

| Task | Run ID | Result | Raw local-AI output |
|---|---|---|---|
| classify_billing | `e8a4dd235071` | FAIL | `Billing` |
| classify_technical | `c7dbc1623fb9` | FAIL | `Technical` |
| classify_sales | `ffc7406efc05` | PASS | `sales` |
| extract_json | `93c1a420d122` | FAIL | `\`\`\`json { "name": "Mira Chen", "date": "2026-11-14" } \`\`\`` |
| arithmetic | `5c7747bbb62e` | FAIL | `1` |
| sort_csv | `9561288460f9` | FAIL | `apple, pear, plum` |
| urgent_route | `18f9f744f5eb` | FAIL | `Urgent` |
| nonurgent_route | `f29db807bb8a` | FAIL | `Normal` |
| missing_field | `37e81d234a8b` | FAIL | `Person Date Place` |
| slug | `95e9a0c659ff` | FAIL | `quarterly-safety-review slug- hyphen` |

## Throughput request raw data

The same request asked for these ten comma-separated words: `alpha, beta, gamma, delta, epsilon, zeta, eta, theta, iota, kappa.` Ollama generation counters, not backend wall time, supply this rate. All requests ran on CPU; `num_predict` was capped at 64.

| Model | Generated tokens | Eval time | Tokens/sec |
|---|---:|---:|---:|
| qwen3:0.6b | 22 | 0.4652 s | 47.30 |
| qwen3:1.7b | 21 | 0.9582 s | 21.92 |
| llama3.2:3b | 21 | 1.8455 s | 11.38 |
| gemma3:1b | 21 | 0.8877 s | 23.66 |

## Candidate selection

`llama3.2:3b` scored 4/10, the best strict result. The 1.7B Qwen scored 2/10; its sort task timed out after 600 seconds, and the full ten-task run measured 1.85 GB incremental runner RSS. The 0.6B Qwen scored 1/10, consistent with the prior live test’s failed independent verification; Gemma 3 1B scored 1/10. Since no candidate meets 8/10, the default is an explicit best-effort choice, not evidence that the low-resource acceptance target has passed.

## Raw download observations

```text
Ollama version: 0.40.0
qwen3:0.6b   7df6b6e09427   522 MB
qwen3:1.7b   8f68893c685c   1.4 GB
llama3.2:3b  a80c4f17acd5   2.0 GB
gemma3:1b    8648f39daa8f   815 MB
```
