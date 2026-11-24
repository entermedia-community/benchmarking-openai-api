# OpenAI-compatible API speed benchmark

- **Date:** 2026-11-24 13:01:34
- **Runs per benchmark:** 5 (+1 warmup, not counted)
- **Concurrency:** 1
- **Streaming:** yes  ·  **max_tokens:** 512  ·  **temperature:** 0
- **Image:** image.png (1769 KB), prompt from img-sample.json
- **Host:** Darwin 27.2.0, Python 3.13.2
- **Total time:** 1969.7s

## Overview — median latency (ms)

| API | Model | Function / tool calling | Structured output | Image to Markdown |
|---|---|---:|---:|---:|
| Qwen (Vast AI) | `Qwen3.8-27B` | 3,726 | 9,507 | 28,794 |
| Qwen (Alibaba) | `qwen4-max` | 2,576 | 2,629 | 11,718 |
| Qwen (Alibaba) | `qwen3.8-max` | 3,039 | 7,217 | 90,700 |
| Qwen (Alibaba) | `qwen3.8-flash` | 2,495 | 4,477 | 27,470 |
| Qwen (Alibaba) | `qwen3.7-plus` | 3,705 | 12,294 | 63,787 |
| Qwen (Alibaba) | `qwen3.7-max` | 3,656 | 12,427 | failed |
| Qwen (Alibaba) | `qwen3.6-plus` | 5,005 | failed | 21,733 |

## Function / tool calling

| # | API | Model | OK | p50 ms | mean ms | p95 ms | min ms | max ms | TTFT p50 ms | TTFT p95 ms | gen tok/s | e2e tok/s | out tok | in tok | req/s |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Qwen (Alibaba) | `qwen3.8-flash` | 5/5 | 2,495 | 2,686 | 3,492 | 2,262 | 3,698 | 1,558 | 1,749 | 86.9 | 29.5 | 82 | 431 | 0.37 |
| 2 | Qwen (Alibaba) | `qwen4-max` | 5/5 | 2,576 | 2,522 | 2,760 | 2,195 | 2,806 | 2,079 | 2,354 | 127.2 | 20.2 | 52 | 295 | 0.40 |
| 3 | Qwen (Alibaba) | `qwen3.8-max` | 5/5 | 3,039 | 2,999 | 3,145 | 2,818 | 3,171 | 1,941 | 2,086 | 51.9 | 18.8 | 56 | 431 | 0.33 |
| 4 | Qwen (Alibaba) | `qwen3.7-max` | 5/5 | 3,656 | 3,370 | 3,736 | 2,805 | 3,749 | 2,486 | 2,715 | 107.2 | 30.4 | 104 | 393 | 0.30 |
| 5 | Qwen (Alibaba) | `qwen3.7-plus` | 5/5 | 3,705 | 4,679 | 6,232 | 3,637 | 6,252 | 1,937 | 2,091 | 62.9 | 31.3 | 176 | 393 | 0.21 |
| 6 | Qwen (Vast AI) | `Qwen3.8-27B` | 5/5 | 3,726 | 3,744 | 3,783 | 3,722 | 3,790 | 1,051 | 1,093 | 27.2 | 19.6 | 73 | 431 | 0.27 |
| 7 | Qwen (Alibaba) | `qwen3.6-plus` | 5/5 | 5,005 | 5,053 | 5,312 | 4,872 | 5,352 | 1,820 | 1,929 | 59.6 | 38.1 | 198 | 393 | 0.20 |

**Fastest (p50):** Qwen (Alibaba) `qwen3.8-flash` — 2,495 ms

## Structured output

| # | API | Model | OK | p50 ms | mean ms | p95 ms | min ms | max ms | TTFT p50 ms | TTFT p95 ms | gen tok/s | e2e tok/s | out tok | in tok | req/s |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Qwen (Alibaba) | `qwen4-max` | 5/5 | 2,629 | 2,821 | 3,333 | 2,413 | 3,370 | 2,144 | 2,764 | 112.9 | 24.7 | 70 | 209 | 0.35 |
| 2 | Qwen (Alibaba) | `qwen3.8-flash` | 5/5 | 4,477 | 4,494 | 5,017 | 3,726 | 5,053 | 1,618 | 1,658 | 68.3 | 42.8 | 192 | 114 | 0.22 |
| 3 | Qwen (Alibaba) | `qwen3.8-max` | 5/5 | 7,217 | 7,101 | 8,026 | 6,169 | 8,189 | 2,034 | 2,546 | 39.5 | 25.8 | 187 | 114 | 0.14 |
| 4 | Qwen (Vast AI) | `Qwen3.8-27B` | 5/5 | 9,507 | 9,507 | 9,528 | 9,484 | 9,531 | 1,070 | 1,249 | 22.9 | 20.3 | 193 | 112 | 0.11 |
| 5 | Qwen (Alibaba) | `qwen3.7-plus` | 5/5 | 12,294 | 13,119 | 16,765 | 10,730 | 17,547 | 1,964 | 2,163 | 59.8 | 51.4 | 663 | 76 | 0.08 |
| 6 | Qwen (Alibaba) | `qwen3.7-max` | 5/5 | 12,427 | 12,754 | 14,209 | 11,127 | 14,412 | 2,439 | 2,944 | 87.4 | 71.5 | 867 | 76 | 0.08 |
| 7 | Qwen (Alibaba) | `qwen3.6-plus` | 0/5 | – | – | – | – | – | – | – | – | – | – | – | 0.00 |

**Fastest (p50):** Qwen (Alibaba) `qwen4-max` — 2,629 ms

## Image to Markdown (text extraction + captions)

| # | API | Model | OK | p50 ms | mean ms | p95 ms | min ms | max ms | TTFT p50 ms | TTFT p95 ms | gen tok/s | e2e tok/s | out tok | in tok | req/s |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Qwen (Alibaba) | `qwen4-max` | 5/5 | 11,718 | 11,812 | 12,525 | 11,292 | 12,713 | 6,752 | 7,812 | 105.8 | 43.7 | 512 | 7231 | 0.08 |
| 2 | Qwen (Alibaba) | `qwen3.6-plus` | 5/5 | 21,733 | 25,310 | 35,204 | 20,734 | 37,566 | 14,192 | 15,537 | 71.9 | 38.2 | 999 | 2959 | 0.04 |
| 3 | Qwen (Alibaba) | `qwen3.8-flash` | 5/5 | 27,470 | 30,552 | 48,044 | 20,779 | 52,916 | 7,352 | 19,923 | 80.7 | 56.2 | 1647 | 2997 | 0.03 |
| 4 | Qwen (Vast AI) | `Qwen3.8-27B` | 5/5 | 28,794 | 29,207 | 32,269 | 26,886 | 33,016 | 4,703 | 9,061 | 21.9 | 17.8 | 512 | 4521 | 0.03 |
| 5 | Qwen (Alibaba) | `qwen3.7-plus` | 5/5 | 63,787 | 70,391 | 93,371 | 52,663 | 95,713 | 8,150 | 22,252 | 65.9 | 56.3 | 3750 | 2959 | 0.01 |
| 6 | Qwen (Alibaba) | `qwen3.8-max` | 5/5 | 90,700 | 88,117 | 110,048 | 54,397 | 111,110 | 7,838 | 18,907 | 48.2 | 42.0 | 3673 | 2959 | 0.01 |
| 7 | Qwen (Alibaba) | `qwen3.7-max` | 0/5 | – | – | – | – | – | – | – | – | – | – | – | 0.00 |

**Fastest (p50):** Qwen (Alibaba) `qwen4-max` — 11,718 ms

## Errors

**Qwen (Alibaba) / qwen3.7-max / image**

- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"The provided messages input is invalid. The error info is [Unexpected item type in content.].","type":"invalid_request_error"},"id":"chatcmpl-741b8d09-b496-9c0a-8081-1789e36a25fb"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"The provided messages input is invalid. The error info is [Unexpected item type in content.].","type":"invalid_request_error"},"id":"chatcmpl-4768a9c9-25a9-9dd1-af71-f7730f1fc567"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"The provided messages input is invalid. The error info is [Unexpected item type in content.].","type":"invalid_request_error"},"id":"chatcmpl-f5961794-39f3-9cd9-b122-077c65da8959"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"The provided messages input is invalid. The error info is [Unexpected item type in content.].","type":"invalid_request_error"},"id":"chatcmpl-9f368d82-7550-9fb5-82f9-f75d22d251b8"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"The provided messages input is invalid. The error info is [Unexpected item type in content.].","type":"invalid_request_error"},"id":"chatcmpl-acc53e32-0b45-9daf-8eec-998e558901cd"}  `

**Qwen (Alibaba) / qwen3.6-plus / structured**

- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.","type":"invalid_request_error"},"id":"chatcmpl-8515de10-c5eb-9817-b03b-2a34e466644d"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.","type":"invalid_request_error"},"id":"chatcmpl-dbc2511b-c2ab-9fde-b62a-105b48baa649"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.","type":"invalid_request_error"},"id":"chatcmpl-44047850-a582-9f6f-8ef5-e2ec4f7db72f"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.","type":"invalid_request_error"},"id":"chatcmpl-a0327a5a-c5e0-9445-a08b-3d89bea8c492"}  `
- 1× `HTTP 400: data: {"error":{"code":"invalid_parameter_error","param":null,"message":"'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.","type":"invalid_request_error"},"id":"chatcmpl-fa79b454-c4f3-974a-bbbb-8856c5a453b6"}  `

## Metric notes

- **Latency**: request sent → full response received, successful requests only.
- **TTFT**: time to first streamed content, reasoning or tool-call token (streaming only).
- **gen tok/s**: output tokens ÷ (latency − TTFT), i.e. decode speed. **e2e tok/s**: output tokens ÷ latency.
- **req/s**: successful requests ÷ wall-clock time for the batch (meaningful with concurrency > 1).
- **OK**: response had the expected shape (a tool call, parseable JSON, or non-empty Markdown for image). Content quality is not checked.
- `~` means token counts were estimated (≈4 chars/token) because the API returned no usage data.
