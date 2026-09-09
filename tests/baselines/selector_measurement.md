# Selector measurement: 101 bricks vs 14 (Auto-Generated)

Do not hand-edit. Regenerate with:

    BRICKS_UPDATE_BASELINE=1 python -m pytest tests/core/test_selector_measurement.py

Produced by `tests/core/test_selector_measurement.py`, which is also where the
task set, the metric definitions and the limits of this measurement are written
down. Short version: there is no model in this loop, so this measures what the
caller is *shown*, not what a model would *pick*. The full-registry hit-rate is
100% by construction, and so is its precision (1 / listing-size, since each
task has one expected brick) - the rival count is the informative number.

## Configurations

- **full registry** - `CatalogConfig.common_set` = all 101 registered bricks.
- **common set** - `CatalogConfig.common_set` = the 14 names `block-set.md`
  lists under "Keep visible, unchanged".

## Summary

| metric | full registry | common set |
| --- | --- | --- |
| bricks listed (tier 1) | 101 | 14 |
| tier-1 hit-rate | 30/30 = 100.0% | 14/30 = 46.7% |
| tier-1 precision (mean) | 0.0099 | 0.0714 |
| same-keyword rivals in the listing (mean) | 3.00 | 0.37 |
| hit-rate after one tier-2 search | 30/30 = 100.0% | 30/30 = 100.0% |
| candidates to choose between (mean) | 101.0 | 17.2 |
| worst-case two-step candidates | 101 | 31 |

The common-set tier-1 hit-rate (14/30 = 46.7%) is by construction as well:
the 14 inside tasks are exactly one task per `common_set` brick, so this is
the task mix restated, not a discovered rate.

Tier 2 is the same search in both configurations, so it has one number:
the query returned every expected brick on 27/30 = 90.0% of tasks.
The tasks where it did not are recorded below; each of those happens to be
answerable from tier 1 in the common-set configuration, which is why the
two-step hit-rate is unaffected. It would not be, if those bricks were hidden.

Two tasks have a second equally correct answer not counted above: T11
(`is_not_empty`) is also answered, inverted, by `is_empty_list`; T17
(`truncate_text`) names the same job as `truncate_string`, the pair
`block-set.md` calls a coin-flip. Expected answers are unchanged.

## Per task

### T01 - Sort the day's calendar events by start time.

- expected: `sort_dict_list`
- tier-2 query: "sort" - 2 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 1 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T02 - Pull the title field out of each event record.

- expected: `map_values`
- tier-2 query: "field" - 12 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 11 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 3 same-keyword rival(s) listed - two-step HIT over 22 candidates

### T03 - Group this week's expenses by category.

- expected: `group_by_key`
- tier-2 query: "group" - 2 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 1 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T04 - Add up the total amount across a list of invoice records.

- expected: `calculate_aggregates`
- tier-2 query: "total" - 3 of 101 bricks match it, expected brick NOT FOUND
- full registry: tier-1 HIT  - 101 listed, 3 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 1 same-keyword rival(s) listed - two-step HIT over 16 candidates

### T05 - The reply had JSON inside a markdown fence - get the object out.

- expected: `extract_json_from_str`
- tier-2 query: "json" - 3 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 2 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 16 candidates

### T06 - Keep only the name and email keys of a contact record.

- expected: `select_dict_keys`
- tier-2 query: "keys" - 12 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 11 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 1 same-keyword rival(s) listed - two-step HIT over 24 candidates

### T07 - Merge the default settings with the user's overrides.

- expected: `merge_dictionaries`
- tier-2 query: "merge" - 2 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 1 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T08 - What date is seven days after 2026-03-01?

- expected: `add_days`
- tier-2 query: "days" - 4 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 3 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 1 same-keyword rival(s) listed - two-step HIT over 16 candidates

### T09 - How many days lie between the invoice date and the due date?

- expected: `date_diff`
- tier-2 query: "between" - 4 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 3 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 17 candidates

### T10 - Check whether the order total is greater than 500.

- expected: `compare_values`
- tier-2 query: "greater" - 0 of 101 bricks match it, expected brick NOT FOUND
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 14 candidates

### T11 - Stop the run when today's event list came back empty.

- expected: `is_not_empty`
- tier-2 query: "empty" - 5 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 4 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 18 candidates

### T12 - Remove repeated tags from a list, keeping the original order.

- expected: `unique_values`
- tier-2 query: "repeated" - 0 of 101 bricks match it, expected brick NOT FOUND
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 14 candidates

### T13 - Round the average to two decimal places.

- expected: `round_number`
- tier-2 query: "round" - 3 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 2 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 16 candidates

### T14 - What share of the tasks were completed, as a percent?

- expected: `percentage`
- tier-2 query: "percent" - 3 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 2 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 HIT  - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 16 candidates

### T15 - Turn a list of rows into a CSV string to attach to the mail.

- expected: `convert_to_csv_str`
- tier-2 query: "csv" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T16 - Strip the HTML tags out of the fetched article body.

- expected: `remove_html_tags`
- tier-2 query: "html" - 3 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 2 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 17 candidates

### T17 - Shorten a headline that runs past 80 characters.

- expected: `truncate_text`
- tier-2 query: "characters" - 8 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 7 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 22 candidates

### T18 - Percent-encode a search term before putting it in a URL.

- expected: `url_encode`
- tier-2 query: "encode" - 4 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 3 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 18 candidates

### T19 - Split a long list of items into chunks of twenty.

- expected: `chunk_list`
- tier-2 query: "chunk" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T20 - Take only the first five entries of the list.

- expected: `take_first_n`
- tier-2 query: "first" - 10 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 9 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 2 same-keyword rival(s) listed - two-step HIT over 22 candidates

### T21 - Redact addresses and phone numbers from the ticket text.

- expected: `redact_pii_patterns`
- tier-2 query: "redact" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T22 - Is 2026-03-14 a business day?

- expected: `is_business_day`
- tier-2 query: "business" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T23 - Fill a message template with the values I just computed.

- expected: `template_string_fill`
- tier-2 query: "template" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T24 - Join the summary lines into one block of text.

- expected: `concatenate_strings`
- tier-2 query: "join" - 2 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 1 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 16 candidates

### T25 - Drop duplicate records that share the same id.

- expected: `deduplicate_dict_list`
- tier-2 query: "duplicate" - 2 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 1 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 1 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T26 - Filter the orders down to the ones whose status is 'open'.

- expected: `filter_dict_list`
- tier-2 query: "filter" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T27 - Pull every URL out of the newsletter text.

- expected: `extract_urls`
- tier-2 query: "url" - 4 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 3 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 18 candidates

### T28 - Get the year and the month out of an ISO date.

- expected: `extract_date_parts`
- tier-2 query: "date" - 19 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 18 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 2 same-keyword rival(s) listed - two-step HIT over 31 candidates

### T29 - Clamp the score so it stays between 0 and 100.

- expected: `clamp_value`
- tier-2 query: "clamp" - 1 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 0 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 15 candidates

### T30 - Check the address the user typed is a valid email.

- expected: `is_email_valid`
- tier-2 query: "email" - 3 of 101 bricks match it, expected brick found
- full registry: tier-1 HIT  - 101 listed, 2 same-keyword rival(s) listed - two-step HIT over 101 candidates
- common set:   tier-1 MISS - 14 listed, 0 same-keyword rival(s) listed - two-step HIT over 17 candidates
