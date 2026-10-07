# Local model choice — 2026-10-07

## Recommendation

No candidate met the low-resource threshold of 8/10. `granite3.3:2b` is the highest scoring allowed model (4/10), and is the best result among these candidates with an Ollama download under 3 GB. It is the fallback default for standard mode. Low-resource mode defaults to `qwen3:0.6b` (about 1 GiB peak), the only candidate measured to fit a modest PC. The measured resident memory peak was about 5.13 GiB for Granite on this host, so this default is not proven to fit a 4 GB PC. Glacier chooses the smallest evaluated model already installed before falling back to the default.

**Integrator note:** most failures were formatting, not wrong answers (for example `19 + 23 = 42. **Integer answer:** 42.` instead of `42`). A follow-up makes Glacier's local-AI step ask for the answer only, at temperature 0, and re-measures.

## Evaluation setup

- Ollama 0.40.0 was already installed. The existing shared daemon/model store was left untouched. A separate Ollama server at `127.0.0.1:11435` was started by this evaluation with `OLLAMA_LLM_LIBRARY=cpu`; its log reported CPU inference. Models were pulled to the evaluation user’s Ollama store.
- Host: Linux x86_64 VM, AMD EPYC 7763, 4 logical CPUs. Ollama reported 7.6 GiB total memory available to the CPU runner (container-visible memory); this is not a physical modest PC.
- Each model ran the same ten prompts below, in the same order, through a real Glacier backend `local_ai` node followed by a `check` node (`exit_code == 0`). A separate harness compared the raw AI node result to the expected answer after trimming outer whitespace and backtick characters. Task correctness is independent of the workflow completion check.
- Glacier’s request contains Ollama `"think": false`. Results were checked for `<think>...</think>`; no output contained a think block in this run, so no stripping workaround was needed for scoring. The local-AI request already disables thinking.
- Peak RAM is the maximum sampled RSS of the CPU `llama-server` runner during each model’s ten backend runs (sampled every 200 ms); it is runner RSS, not total host memory. Tokens/sec is Ollama `eval_count / eval_duration` from one separate CPU request with `num_predict=64`.
- Download sizes are the actual Ollama `list` sizes for pulled quantized tags. Each linked Ollama model page lists an Apache-2.0 license.

## Summary results

| Model | License | Download | Peak runner RSS | CPU tokens/sec | Strict pass rate |
|---|---|---:|---:|---:|---:|
| [`qwen3:0.6b`](https://ollama.com/library/qwen3:0.6b) | Apache-2.0 | 522 MB | 1.06 GiB (1083 MiB) | 81.54 | 1/10 |
| [`qwen3:1.7b`](https://ollama.com/library/qwen3:1.7b) | Apache-2.0 | 1.4 GB | 3.31 GiB (3386 MiB) | 33.11 | 2/10 |
| [`granite3.3:2b`](https://ollama.com/library/granite3.3:2b) | Apache-2.0 | 1.5 GB | 5.13 GiB (5251 MiB) | 24.16 | 4/10 |
| [`smollm2:1.7b`](https://ollama.com/library/smollm2:1.7b) | Apache-2.0 | 1.8 GB | 5.90 GiB (6038 MiB) | 26.53 | 0/10 |

No model reached 8/10. Granite 3.3 2B is the measured accuracy winner. Qwen3 0.6B is smallest and fastest, but scored 1/10. The standard fallback uses Granite because its download is 1.5 GB (<3 GB); actual runner memory is substantially higher than download size.

## Tasks and expected outputs

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

## Raw outputs

`PASS` means the complete raw output equals the expected value under the independent comparison above. Results include backend run IDs.

### `qwen3:0.6b`

<details><summary>classify_billing — FAIL — run 03905820173f</summary>

<pre>The message &quot;I was charged twice for my subscription&quot; is classified as **sales**.</pre>

</details>

<details><summary>classify_technical — FAIL — run 4c1dc4df3031</summary>

<pre>The message: &quot;The app crashes every time I upload a PDF.&quot;
**Classification:** **technical**

**Reasoning:** The message indicates a technical issue with the app, specifically that it crashes when uploading PDF files.</pre>

</details>

<details><summary>classify_sales — FAIL — run 77dc1afe85cd</summary>

<pre>The message is: **&quot;Can I get a quote for 40 team seats?&quot;**

**Classification:** **sales** (the message is asking for a quote, likely related to pricing or sales information).</pre>

</details>

<details><summary>extract_json — FAIL — run 4835898c607d</summary>

<pre>```json
{&quot;name&quot;: &quot;Mira Chen&quot;, &quot;date&quot;: &quot;2026-11-14&quot;}
```</pre>

</details>

<details><summary>arithmetic — FAIL — run 9d471191d462</summary>

<pre>19 + 23 = 42.
**Integer answer:** 42.</pre>

</details>

<details><summary>sort_csv — FAIL — run 1687ab446561</summary>

<pre>apple, pear, plum.</pre>

</details>

<details><summary>urgent_route — FAIL — run c26770ee471f</summary>

<pre>**Urgent**</pre>

</details>

<details><summary>nonurgent_route — FAIL — run 195901ce3a9d</summary>

<pre>**Urgent**</pre>

</details>

<details><summary>missing_field — FAIL — run 1988fec534cc</summary>

<pre>- person: person
- date: date
- place: place</pre>

</details>

<details><summary>slug — PASS — run 48d5a0186d17</summary>

<pre>quarterly-safety-review</pre>

</details>

### `qwen3:1.7b`

<details><summary>classify_billing — FAIL — run 6ebdb67f13a8</summary>

<pre>**billing**</pre>

</details>

<details><summary>classify_technical — FAIL — run aed817237496</summary>

<pre>**Sales**</pre>

</details>

<details><summary>classify_sales — FAIL — run 2c5f95b1e218</summary>

<pre>**Sales**

Explanation: The message is a request for a quote, which is typically associated with **sales**. The phrase &quot;get a quote&quot; is a common sales-oriented request.</pre>

</details>

<details><summary>extract_json — FAIL — run 4d911e55b2b8</summary>

<pre>{&quot;name&quot;: &quot;Mira Chen&quot;, &quot;date&quot;: &quot;2026-11-14&quot;}</pre>

</details>

<details><summary>arithmetic — FAIL — run 058e788b9f2a</summary>

<pre>19 + 23 = 42</pre>

</details>

<details><summary>sort_csv — FAIL — run 023885c9535a</summary>

<pre>Local AI took longer than 180 seconds.</pre>

</details>

<details><summary>urgent_route — FAIL — run 61a51dd9916c</summary>

<pre>**Normal**.</pre>

</details>

<details><summary>nonurgent_route — FAIL — run 52e1dee61a7f</summary>

<pre>**Normal**

The message &quot;Please change my profile picture when convenient.&quot; is not urgent. It is a general request and does not require immediate action. Therefore, the appropriate label is **Normal**.</pre>

</details>

<details><summary>missing_field — PASS — run 791a82c24068</summary>

<pre>date</pre>

</details>

<details><summary>slug — PASS — run 9bea5cebe004</summary>

<pre>quarterly-safety-review</pre>

</details>

### `granite3.3:2b`

<details><summary>classify_billing — PASS — run 56c22842877c</summary>

<pre>billing</pre>

</details>

<details><summary>classify_technical — FAIL — run 855bff8bcb7e</summary>

<pre>The message &quot;The app crashes every time I upload a PDF.&quot; can be classified under the &quot;technical&quot; label. This is because the issue described pertains to the functionality of the application (the &quot;app&quot;), specifically a problem with uploading a file (PDF), which is a technical aspect of software usage.</pre>

</details>

<details><summary>classify_sales — FAIL — run 7894dfaa48bd</summary>

<pre>The message &quot;Can I get a quote for 40 team seats?&quot; can be classified as &#x27;sales&#x27;. This is because the inquiry is about obtaining pricing for a bulk purchase, which is a sales-oriented concern.</pre>

</details>

<details><summary>extract_json — FAIL — run 0c8429cff05b</summary>

<pre>{
  &quot;name&quot;: &quot;Mira Chen&quot;,
  &quot;date&quot;: &quot;2026-11-14&quot;
}</pre>

</details>

<details><summary>arithmetic — PASS — run a3be9743797e</summary>

<pre>42</pre>

</details>

<details><summary>sort_csv — FAIL — run e07d308977ee</summary>

<pre>apple, pear, plum</pre>

</details>

<details><summary>urgent_route — FAIL — run 0ceb05007109</summary>

<pre>&quot;urgent&quot;</pre>

</details>

<details><summary>nonurgent_route — PASS — run bc5d67f40502</summary>

<pre>normal</pre>

</details>

<details><summary>missing_field — FAIL — run 17867f285ceb</summary>

<pre>The missing field is &quot;reason&quot;.</pre>

</details>

<details><summary>slug — PASS — run 6f85a377279b</summary>

<pre>quarterly-safety-review</pre>

</details>

### `smollm2:1.7b`

<details><summary>classify_billing — FAIL — run 80656dcd3674</summary>

<pre>Local AI took longer than 180 seconds.</pre>

</details>

<details><summary>classify_technical — FAIL — run bb654bf6e565</summary>

<pre>The message is classified as &#x27;technical&#x27;.</pre>

</details>

<details><summary>classify_sales — FAIL — run 9d478eb28f66</summary>

<pre>The message &quot;Can I get a quote for 40 team seats?&quot; is classified under the &quot;billing&quot; label.</pre>

</details>

<details><summary>extract_json — FAIL — run aca8c1004af3</summary>

<pre>{
  &quot;name&quot;: &quot;Mira Chen&quot;,
  &quot;date&quot;: &quot;2026-11-14&quot;
}</pre>

</details>

<details><summary>arithmetic — FAIL — run f9bf1209fe13</summary>

<pre>The integer answer to 19 + 23 is 42.</pre>

</details>

<details><summary>sort_csv — FAIL — run 812620d79d80</summary>

<pre>apple, pear, plum</pre>

</details>

<details><summary>urgent_route — FAIL — run a58252abf546</summary>

<pre>The message you provided doesn&#x27;t contain enough information to accurately label it as either urgent or normal. Please provide more context or details about the message for accurate classification.</pre>

</details>

<details><summary>nonurgent_route — FAIL — run 9e8dba4e38f1</summary>

<pre>urgent</pre>

</details>

<details><summary>missing_field — FAIL — run 7ce0933a25d0</summary>

<pre>Date</pre>

</details>

<details><summary>slug — FAIL — run 5dbcd71aed13</summary>

<pre>&quot;quarterly-safety-review&quot;</pre>

</details>

## Ollama artifact observations

```text
Ollama version: 0.40.0
CPU-only server: 127.0.0.1:11435; OLLAMA_LLM_LIBRARY=cpu
Model                         Ollama size / artifact ID
qwen3:0.6b                    522 MB / 7df6b6e09427
qwen3:1.7b                    1.4 GB / 8f68893c685c
granite3.3:2b                 1.5 GB / 07bd1f170855
smollm2:1.7b                  1.8 GB / cef4a1e09247
```

Runner RSS varied widely from model file size on this container and should be treated as a measurement of this VM configuration, not a hardware requirement. The earlier shared-daemon run was discarded for performance/RAM reporting because Ollama reported GPU execution and its RSS sampler targeted the wrong process name. Pass rates above come from the corrected CPU-only backend run.
