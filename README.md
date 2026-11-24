# bench-openai-api

Measures how fast OpenAI-compatible chat completion APIs are. It does not grade answer quality. It runs three benchmarks and writes a Markdown report:

| Benchmark | What is sent |
|---|---|
| `tools` | A prompt plus two function definitions (`get_weather`, `get_time`). A run counts as OK when the response contains a tool call. |
| `structured` | Text to extract into a strict JSON schema with `response_format`. |
| `image` | The prompt in `img-sample.json`, with `image.png` as the image. The model returns the page as Markdown (extracted text plus image captions). A run counts as OK when the response is not empty. |

Metrics: latency (p50/mean/p95/min/max), time to first token, generation tok/s, end-to-end tok/s, token counts and req/s.

## Setup

```bash
pip install -r requirements.txt
```

Edit `config.yaml`. Each entry under `apis` needs `name`, `base_url`, `api_key` (sent as `Authorization: Bearer ...`) and `model`. `model` can be a single model or a list; every model in a list uses the same endpoint and token. Put the test image next to the script as `image.png`; the image prompt is in `img-sample.json` (its image URL is replaced with `image.png`).

## Run

```bash
python bench.py
```

One run benchmarks every model on all three tests and writes `results.md`. Settings such as `runs`, `concurrency` and `output` live in `config.yaml`.

## Compatibility settings

- `structured_mode: json_object` or `prompt`: for APIs that don't support `json_schema`.
- `stream_usage: false`: for APIs that reject `stream_options`. Token counts are then estimated and marked `~` in the report.
- `max_tokens_param: max_completion_tokens` and `temperature: null`: for OpenAI reasoning models.
- `tool_choice: required`: forces a tool call where the API supports it.
