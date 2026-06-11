# Brick Description Style Guide

Rules for writing LLM-optimized brick descriptions:

1. **First sentence: what it does** — verb form, ~5 words (e.g., "Multiply a * b.")
2. **Always include output fields** — `Returns {field_name: type}` with exact field names in curly braces
3. **Flag non-standard output keys** — if the output key is NOT `result`, add: `NOTE: output key is 'X', not 'result'`
4. **Include formulas** — for computations, state the formula (e.g., `a*b`, `a-b`)
5. **Include defaults** — if any parameter has a default, mention it (e.g., `default decimals=2`)
6. **Keep it short** — total description under 120 characters
7. **No fluff** — never start with "This brick", "This function", "A useful tool that"

## Examples

```
Good: "Multiply a * b. Returns {result: a*b}."
Good: "Round value to N decimal places (default decimals=2). Returns {result: rounded_value}."
Good: "Format as 'label: value' display string. Returns {display: str} — NOTE: output key is 'display', not 'result'."

Bad:  "This function multiplies two numbers together and returns the result."
Bad:  "A useful tool that rounds a floating-point number."
Bad:  "Multiply two numbers."  (missing output field names)
```
