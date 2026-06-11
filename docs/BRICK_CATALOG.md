# Brick Catalog (Auto-Generated)

Generated: 2026-04-05

This catalog documents all 100 available stdlib bricks. Each brick returns a dictionary with a `result` key.

## Data Transformation

### calculate_aggregates

Aggregate a numeric field across a list of dicts. Returns {result: aggregated_value}.

    Args:
        items: List of dicts.
        field: Numeric field to aggregate.
        operation: One of ``"sum"``, ``"avg"``, ``"min"``, ``"max"``, ``"count"``.

    Returns:
        dict with key ``result`` containing the aggregated value.

    Raises:
        ValueError: If operation is not recognized.


**Tags:** `aggregate`, `data`, `math`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts. field: Numeric field to aggregate. operation: One of ``"sum"``, ``"avg"``, ``"min"``, ``"max"``, ``"count"``.
- `field` (str): Numeric field to aggregate. operation: One of ``"sum"``, ``"avg"``, ``"min"``, ``"max"``, ``"count"``.
- `operation` (str): One of ``"sum"``, ``"avg"``, ``"min"``, ``"max"``, ``"count"``.

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the aggregated value.


### cast_data_types

Cast dict values to specified types. Returns {result: cast_dict}.

    Args:
        data: Input dictionary.
        type_map: Maps field names to type names: ``"int"``, ``"float"``, ``"str"``, ``"bool"``.

    Returns:
        dict with key ``result`` containing the dict with cast values.


**Tags:** `casting`, `data`, `types`

**Input:**

- `data` (dict[str, Any]): Input dictionary. type_map: Maps field names to type names: ``"int"``, ``"float"``, ``"str"``, ``"bool"``.
- `type_map` (dict[str, str]): Maps field names to type names: ``"int"``, ``"float"``, ``"str"``, ``"bool"``.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the dict with cast values.


### convert_to_csv_str

Convert a list of dicts to a CSV string. Returns {result: csv_string}.

    Args:
        items: List of dicts (must all have the same keys).

    Returns:
        dict with key ``result`` containing the CSV text.


**Tags:** `csv`, `data`, `export`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts (must all have the same keys).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the CSV text.


### count_dict_list

Return the number of items in a list of dicts. Returns {result: count}.

    Args:
        items: List of dicts.

    Returns:
        dict with key ``result`` containing the count.


**Tags:** `count`, `data`, `list`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts.

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing the count.


### deduplicate_dict_list

Remove duplicate dicts keeping the first occurrence of each key value. Returns {result: deduped}.

    Args:
        items: List of dicts.
        key: Field to use as the deduplication key.

    Returns:
        dict with key ``result`` containing deduplicated list (first occurrence kept).


**Tags:** `data`, `dedup`, `list`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts. key: Field to use as the deduplication key.
- `key` (str): Field to use as the deduplication key.

**Output:**

- `result` (dict[str, list[dict[str, Any]]]): dict with key ``result`` containing deduplicated list (first occurrence kept).


### dict_to_json_str

Serialize a dict to a JSON string. Returns {result: json_string}.

    Args:
        data: Dictionary to serialize.

    Returns:
        dict with key ``result`` containing the JSON string.


**Tags:** `data`, `json`, `serialization`

**Input:**

- `data` (dict[str, Any]): Dictionary to serialize.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the JSON string.


### diff_dict_objects

Compute the diff between two dicts. Returns {result: diff}.

    Args:
        old: Original dictionary.
        new: Updated dictionary.

    Returns:
        dict with key ``result`` containing a dict with ``added``, ``removed``,
        and ``changed`` entries.


**Tags:** `data`, `dict`, `diff`

**Input:**

- `old` (dict[str, Any]): Original dictionary. new: Updated dictionary.
- `new` (dict[str, Any]): Updated dictionary.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing a dict with ``added``, ``removed``, and ``changed`` entries.


### extract_dict_field

Extract a single field from a dict. Returns {result: field_value}.

    Args:
        data: Source dictionary.
        field: Key to extract.

    Returns:
        dict with key ``result`` containing the field value, or None if missing.


**Tags:** `data`, `dict`, `extraction`

**Input:**

- `data` (dict[str, Any]): Source dictionary. field: Key to extract.
- `field` (str): Key to extract.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the field value, or None if missing.


### extract_json_from_str

Extract JSON from a string, stripping markdown code fences if present. Returns {result: parsed}.

    Args:
        text: String containing JSON, optionally wrapped in markdown fences.

    Returns:
        dict with key ``result`` containing the parsed JSON value.

    Raises:
        ValueError: If no valid JSON is found.


**Tags:** `data`, `json`, `parsing`

**Input:**

- `text` (str): String containing JSON, optionally wrapped in markdown fences.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the parsed JSON value.


### filter_dict_list

Filter a list of dicts keeping only items where items[key] == value. Returns {result: filtered}.

    Args:
        items: List of dicts to filter.
        key: Dict key to test.
        value: Value to match (equality check).

    Returns:
        dict with key ``result`` containing matching dicts.


**Tags:** `data`, `filter`, `list`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts to filter. key: Dict key to test. value: Value to match (equality check).
- `key` (str): Dict key to test. value: Value to match (equality check).
- `value` (Any): Value to match (equality check).

**Output:**

- `result` (dict[str, list[dict[str, Any]]]): dict with key ``result`` containing matching dicts.


### flatten_nested_dict

Flatten a nested dict using dot-separated keys. Returns {result: flat_dict}.

    Args:
        data: Nested dictionary to flatten.
        separator: Key separator (default ``"."``).

    Returns:
        dict with key ``result`` containing the flattened dict.


**Tags:** `data`, `dict`, `flatten`

**Input:**

- `data` (dict[str, Any]): Nested dictionary to flatten. separator: Key separator (default ``"."``).
- `separator` (str) (default: .): Key separator (default ``"."``).

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the flattened dict.


### group_by_key

Group a list of dicts by a field value. Returns {result: grouped_dict}.

    Args:
        items: List of dicts.
        key: Field to group by.

    Returns:
        dict with key ``result`` where each value is a list of matching dicts.


**Tags:** `data`, `group`, `list`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts. key: Field to group by.
- `key` (str): Field to group by.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` where each value is a list of matching dicts.


### join_lists_on_key

Inner-join two lists of dicts on a shared key. Returns {result: joined_list}.

    Args:
        left: Left list of dicts.
        right: Right list of dicts.
        key: Field name used as the join key.

    Returns:
        dict with key ``result`` containing merged dicts for matching keys.


**Tags:** `data`, `join`, `list`

**Input:**

- `left` (list[dict[str, Any]]): Left list of dicts. right: Right list of dicts. key: Field name used as the join key.
- `right` (list[dict[str, Any]]): Right list of dicts. key: Field name used as the join key.
- `key` (str): Field name used as the join key.

**Output:**

- `result` (dict[str, list[dict[str, Any]]]): dict with key ``result`` containing merged dicts for matching keys.


### mask_sensitive_data

Replace specified field values with '***'. Returns {result: masked_dict}.

    Args:
        data: Input dictionary.
        fields: List of field names to mask.

    Returns:
        dict with key ``result`` containing the dict with sensitive values masked.


**Tags:** `data`, `masking`, `security`

**Input:**

- `data` (dict[str, Any]): Input dictionary. fields: List of field names to mask.
- `fields` (list[str]): List of field names to mask.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the dict with sensitive values masked.


### merge_dictionaries

Merge two dicts; override values take precedence. Returns {result: merged}.

    Args:
        base: The base dictionary.
        override: Keys from this dict overwrite base.

    Returns:
        dict with key ``result`` containing the merged dict.


**Tags:** `data`, `dict`, `merge`

**Input:**

- `base` (dict[str, Any]): The base dictionary. override: Keys from this dict overwrite base.
- `override` (dict[str, Any]): Keys from this dict overwrite base.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the merged dict.


### parse_xml_to_dict

Parse XML text into a nested dict. Returns {result: dict}.

    Args:
        xml_text: Valid XML string.

    Returns:
        dict with key ``result`` containing the parsed XML as a nested dict.


**Tags:** `data`, `parsing`, `xml`

**Input:**

- `xml_text` (str): Valid XML string.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the parsed XML as a nested dict.


### pivot_data_structure

Pivot a list of dicts into {index_value: value}. Returns {result: pivoted}.

    Args:
        items: List of dicts.
        index_key: Field to use as the output key.
        value_key: Field to use as the output value.

    Returns:
        dict with key ``result`` mapping index_key values to value_key values.


**Tags:** `data`, `pivot`, `transform`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts. index_key: Field to use as the output key. value_key: Field to use as the output value.
- `index_key` (str): Field to use as the output key. value_key: Field to use as the output value.
- `value_key` (str): Field to use as the output value.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` mapping index_key values to value_key values.


### remove_null_values

Remove keys with None values from a dict. Returns {result: cleaned}.

    Args:
        data: Input dictionary.

    Returns:
        dict with key ``result`` containing only non-None entries.


**Tags:** `cleaning`, `data`, `dict`

**Input:**

- `data` (dict[str, Any]): Input dictionary.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing only non-None entries.


### rename_dict_keys

Rename dict keys according to a mapping. Returns {result: renamed}.

    Args:
        data: Source dictionary.
        rename_map: Maps old key names to new key names.

    Returns:
        dict with key ``result`` containing the dict with renamed keys.


**Tags:** `data`, `dict`, `rename`

**Input:**

- `data` (dict[str, Any]): Source dictionary. rename_map: Maps old key names to new key names.
- `rename_map` (dict[str, str]): Maps old key names to new key names.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the dict with renamed keys.


### select_dict_keys

Return a new dict containing only the specified keys. Returns {result: subset}.

    Args:
        data: Source dictionary.
        keys: Keys to include in the output.

    Returns:
        dict with key ``result`` containing only the selected keys.


**Tags:** `data`, `dict`, `select`

**Input:**

- `data` (dict[str, Any]): Source dictionary. keys: Keys to include in the output.
- `keys` (list[str]): Keys to include in the output.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing only the selected keys.


### set_dict_field

Set a field in a dict, returning the updated copy. Returns {result: updated_dict}.

    Args:
        data: Source dictionary.
        field: Key to set.
        value: Value to assign.

    Returns:
        dict with key ``result`` containing the updated dict.


**Tags:** `data`, `dict`, `set`

**Input:**

- `data` (dict[str, Any]): Source dictionary. field: Key to set. value: Value to assign.
- `field` (str): Key to set. value: Value to assign.
- `value` (Any): Value to assign.

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the updated dict.


### slice_dict_list

Return a slice of a list of dicts. Returns {result: sliced_list}.

    Args:
        items: Source list.
        start: Start index (inclusive).
        end: End index (exclusive).

    Returns:
        dict with key ``result`` containing the sliced list.


**Tags:** `data`, `list`, `slice`

**Input:**

- `items` (list[dict[str, Any]]): Source list. start: Start index (inclusive). end: End index (exclusive).
- `start` (int): Start index (inclusive). end: End index (exclusive).
- `end` (int): End index (exclusive).

**Output:**

- `result` (dict[str, list[dict[str, Any]]]): dict with key ``result`` containing the sliced list.


### sort_dict_list

Sort a list of dicts by a field. Returns {result: sorted_list}.

    Args:
        items: List of dicts to sort.
        key: Field name to sort by.
        reverse: If True, sort in descending order.

    Returns:
        dict with key ``result`` containing the sorted list.


**Tags:** `data`, `list`, `sort`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts to sort. key: Field name to sort by. reverse: If True, sort in descending order.
- `key` (str): Field name to sort by. reverse: If True, sort in descending order.
- `reverse` (bool) (default: False): If True, sort in descending order.

**Output:**

- `result` (dict[str, list[dict[str, Any]]]): dict with key ``result`` containing the sorted list.


### unflatten_dict

Unflatten a dot-separated flat dict into a nested dict. Returns {result: nested}.

    Args:
        data: Flat dictionary with dot-separated keys.
        separator: Key separator (default ``"."``).

    Returns:
        dict with key ``result`` containing the nested dict.


**Tags:** `data`, `dict`, `unflatten`

**Input:**

- `data` (dict[str, Any]): Flat dictionary with dot-separated keys. separator: Key separator (default ``"."``).
- `separator` (str) (default: .): Key separator (default ``"."``).

**Output:**

- `result` (dict[str, Any]): dict with key ``result`` containing the nested dict.


### validate_json_schema

Validate that data contains all required keys defined in schema. Returns {result: bool}.

    Args:
        data: The dict to validate.
        schema: Dict with a ``required`` list of key names.

    Returns:
        dict with key ``result`` — True if all required keys are present.


**Tags:** `data`, `schema`, `validation`

**Input:**

- `data` (dict[str, Any]): The dict to validate. schema: Dict with a ``required`` list of key names.
- `schema` (dict[str, Any]): Dict with a ``required`` list of key names.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if all required keys are present.


## Date

### days_until

Calculate the number of days from today until a target date. Returns {result: int}.

    Args:
        target_date: Target date in ``YYYY-MM-DD`` format.

    Returns:
        dict with key ``result`` containing the number of days (negative if in the past).

    Raises:
        ValueError: If ``target_date`` is not in ``YYYY-MM-DD`` format.


**Tags:** `calculation`, `date`

**Input:**

- `target_date` (str): Target date in ``YYYY-MM-DD`` format.

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing the number of days (negative if in the past).


## Date Time

### add_days

Add a number of days to an ISO 8601 date. Returns {result: new_date}.

    Args:
        iso_date: Starting date (YYYY-MM-DD).
        days: Number of days to add (negative to subtract).

    Returns:
        dict with key ``result`` containing the resulting ISO date string.


**Tags:** `arithmetic`, `date`

**Input:**

- `iso_date` (str): Starting date (YYYY-MM-DD). days: Number of days to add (negative to subtract).
- `days` (int): Number of days to add (negative to subtract).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the resulting ISO date string.


### add_hours

Add hours to an ISO 8601 datetime string. Returns {result: new_datetime}.

    Args:
        iso_datetime: Starting datetime (YYYY-MM-DDTHH:MM:SS).
        hours: Hours to add (negative to subtract).

    Returns:
        dict with key ``result`` containing the resulting ISO datetime string.


**Tags:** `arithmetic`, `date`

**Input:**

- `iso_datetime` (str): Starting datetime (YYYY-MM-DDTHH:MM:SS). hours: Hours to add (negative to subtract).
- `hours` (int): Hours to add (negative to subtract).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the resulting ISO datetime string.


### convert_timezone

Convert a datetime from one timezone to another. Returns {result: converted_datetime}.

    Args:
        iso_datetime: Naive datetime string (YYYY-MM-DDTHH:MM:SS).
        from_tz: Source IANA timezone (e.g. ``"UTC"``).
        to_tz: Target IANA timezone (e.g. ``"America/New_York"``).

    Returns:
        dict with key ``result`` containing the converted datetime string.


**Tags:** `date`, `timezone`

**Input:**

- `iso_datetime` (str): Naive datetime string (YYYY-MM-DDTHH:MM:SS). from_tz: Source IANA timezone (e.g. ``"UTC"``). to_tz: Target IANA timezone (e.g. ``"America/New_York"``).
- `from_tz` (str): Source IANA timezone (e.g. ``"UTC"``). to_tz: Target IANA timezone (e.g. ``"America/New_York"``).
- `to_tz` (str): Target IANA timezone (e.g. ``"America/New_York"``).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the converted datetime string.


### date_diff

Return the number of days between two ISO 8601 dates (a - b). Returns {result: days}.

    Args:
        date_a: First ISO date (YYYY-MM-DD).
        date_b: Second ISO date (YYYY-MM-DD).

    Returns:
        dict with key ``result`` containing the signed difference in days.


**Tags:** `date`, `diff`, `math`

**Input:**

- `date_a` (str): First ISO date (YYYY-MM-DD). date_b: Second ISO date (YYYY-MM-DD).
- `date_b` (str): Second ISO date (YYYY-MM-DD).

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing the signed difference in days.


### date_range

Generate a list of ISO 8601 dates from start to end (exclusive). Returns {result: dates}.

    Args:
        start: Start date (YYYY-MM-DD), inclusive.
        end: End date (YYYY-MM-DD), exclusive.
        step_days: Step size in days (default 1).

    Returns:
        dict with key ``result`` containing the list of ISO date strings.


**Tags:** `date`, `list`, `range`

**Input:**

- `start` (str): Start date (YYYY-MM-DD), inclusive. end: End date (YYYY-MM-DD), exclusive. step_days: Step size in days (default 1).
- `end` (str): End date (YYYY-MM-DD), exclusive. step_days: Step size in days (default 1).
- `step_days` (int) (default: 1): Step size in days (default 1).

**Output:**

- `result` (dict[str, list[str]]): dict with key ``result`` containing the list of ISO date strings.


### extract_date_parts

Extract year, month, day, weekday from an ISO 8601 date. Returns {result: {year, month, day, weekday}}.

    Args:
        iso_date: ISO 8601 date string (YYYY-MM-DD).

    Returns:
        dict with key ``result`` containing a dict with ``year``, ``month``, ``day``,
        and ``weekday`` (0=Monday).


**Tags:** `date`, `extraction`, `parts`

**Input:**

- `iso_date` (str): ISO 8601 date string (YYYY-MM-DD).

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing a dict with ``year``, ``month``, ``day``, and ``weekday`` (0=Monday).


### format_date

Format an ISO 8601 date string with strftime format. Returns {result: formatted}.

    Args:
        iso_date: ISO 8601 date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
        fmt: strftime format string (e.g. ``"%d %B %Y"``).

    Returns:
        dict with key ``result`` containing the formatted date string.


**Tags:** `date`, `formatting`

**Input:**

- `iso_date` (str): ISO 8601 date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). fmt: strftime format string (e.g. ``"%d %B %Y"``).
- `fmt` (str): strftime format string (e.g. ``"%d %B %Y"``).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the formatted date string.


### is_business_day

Check if an ISO 8601 date is a business day (Mon-Fri). Returns {result: bool}.

    Args:
        iso_date: ISO 8601 date string (YYYY-MM-DD).

    Returns:
        dict with key ``result`` — True if Monday through Friday.


**Tags:** `business`, `calendar`, `date`

**Input:**

- `iso_date` (str): ISO 8601 date string (YYYY-MM-DD).

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if Monday through Friday.


### now_timestamp

Return the current UTC datetime as ISO 8601. Returns {result: timestamp}.

    Returns:
        dict with key ``result`` containing the current UTC datetime string.


**Tags:** `date`, `now`, `utility`

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the current UTC datetime string.


### parse_date

Parse a date string with a format, return ISO 8601 date. Returns {result: iso_date}.

    Args:
        date_str: Date string to parse.
        fmt: strptime format (e.g. ``"%d/%m/%Y"``).

    Returns:
        dict with key ``result`` containing the ISO 8601 date string (YYYY-MM-DD).


**Tags:** `date`, `parsing`

**Input:**

- `date_str` (str): Date string to parse. fmt: strptime format (e.g. ``"%d/%m/%Y"``).
- `fmt` (str): strptime format (e.g. ``"%d/%m/%Y"``).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the ISO 8601 date string (YYYY-MM-DD).


## Encoding

### mask_string

Mask most characters of a string, keeping only the last N visible. Returns {result: str}.

    Useful for displaying sensitive values like API keys or card numbers without exposing them.

    Args:
        text: Input string to mask.
        visible_chars: Number of trailing characters to leave visible (default 4).
        mask_char: Character to use for masking (default ``"*"``).

    Returns:
        dict with key ``result`` containing the masked string.


**Tags:** `mask`, `security`, `string`

**Input:**

- `text` (str): Input string to mask. visible_chars: Number of trailing characters to leave visible (default 4). mask_char: Character to use for masking (default ``"*"``).
- `visible_chars` (int) (default: 4): Number of trailing characters to leave visible (default 4). mask_char: Character to use for masking (default ``"*"``).
- `mask_char` (str) (default: *): Character to use for masking (default ``"*"``).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the masked string.


## Encoding Security

### base64_decode

Decode a base64 string to UTF-8. Returns {result: decoded}.

    Args:
        encoded: Base64-encoded string.

    Returns:
        dict with key ``result`` containing the decoded string.


**Tags:** `base64`, `encoding`

**Input:**

- `encoded` (str): Base64-encoded string.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the decoded string.


### base64_encode

Encode a UTF-8 string to base64. Returns {result: encoded}.

    Args:
        data: String to encode.

    Returns:
        dict with key ``result`` containing the base64-encoded string.


**Tags:** `base64`, `encoding`

**Input:**

- `data` (str): String to encode.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the base64-encoded string.


### compute_hash

Compute a hash digest of a string. Returns {result: hex_digest}.

    Args:
        data: String to hash.
        algorithm: Hash algorithm name — ``"md5"``, ``"sha1"``, ``"sha256"``, ``"sha512"``.

    Returns:
        dict with key ``result`` containing the hexadecimal digest.

    Raises:
        ValueError: If the algorithm is not supported.


**Tags:** `digest`, `hash`, `security`

**Input:**

- `data` (str): String to hash. algorithm: Hash algorithm name — ``"md5"``, ``"sha1"``, ``"sha256"``, ``"sha512"``.
- `algorithm` (str) (default: sha256): Hash algorithm name — ``"md5"``, ``"sha1"``, ``"sha256"``, ``"sha512"``.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the hexadecimal digest.


### escape_special_chars

Backslash-escape specified characters in a string. Returns {result: escaped}.

    Args:
        text: Input string.
        chars: List of characters to escape with a backslash.

    Returns:
        dict with key ``result`` containing the escaped string.


**Tags:** `encoding`, `escape`, `string`

**Input:**

- `text` (str): Input string. chars: List of characters to escape with a backslash.
- `chars` (list[str]): List of characters to escape with a backslash.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the escaped string.


### generate_uuid

Generate a random UUID v4. Returns {result: uuid_string}.

    Returns:
        dict with key ``result`` containing the UUID string.


**Tags:** `identity`, `security`, `uuid`

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the UUID string.


### html_escape

Escape HTML special characters. Returns {result: escaped}.

    Args:
        text: String that may contain HTML special characters.

    Returns:
        dict with key ``result`` containing the HTML-escaped string.


**Tags:** `encoding`, `escape`, `html`

**Input:**

- `text` (str): String that may contain HTML special characters.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the HTML-escaped string.


### html_unescape

Unescape HTML entities back to plain text. Returns {result: unescaped}.

    Args:
        text: String containing HTML entities.

    Returns:
        dict with key ``result`` containing the unescaped string.


**Tags:** `encoding`, `escape`, `html`

**Input:**

- `text` (str): String containing HTML entities.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the unescaped string.


### random_string

Generate a cryptographically secure random string. Returns {result: random_str}.

    Args:
        length: Number of characters to generate.
        charset: Character set — ``"alphanumeric"``, ``"hex"``, ``"alpha"``, ``"digits"``.

    Returns:
        dict with key ``result`` containing the random string.

    Raises:
        ValueError: If charset is not recognized or length < 1.


**Tags:** `random`, `security`, `token`

**Input:**

- `length` (int): Number of characters to generate. charset: Character set — ``"alphanumeric"``, ``"hex"``, ``"alpha"``, ``"digits"``.
- `charset` (str) (default: alphanumeric): Character set — ``"alphanumeric"``, ``"hex"``, ``"alpha"``, ``"digits"``.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the random string.


### url_decode

Decode a percent-encoded URL string. Returns {result: decoded}.

    Args:
        encoded: Percent-encoded string.

    Returns:
        dict with key ``result`` containing the decoded string.


**Tags:** `encoding`, `url`

**Input:**

- `encoded` (str): Percent-encoded string.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the decoded string.


### url_encode

Percent-encode a string for use in a URL. Returns {result: encoded}.

    Args:
        text: String to encode.

    Returns:
        dict with key ``result`` containing the percent-encoded string.


**Tags:** `encoding`, `url`

**Input:**

- `text` (str): String to encode.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the percent-encoded string.


## List

### is_empty_list

Check whether a list is empty. Returns {result: bool}.

    Args:
        items: List to check.

    Returns:
        dict with key ``result`` containing ``True`` if the list is empty.


**Tags:** `check`, `list`

**Input:**

- `items` (list[object]): List to check.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` containing ``True`` if the list is empty.


## List Operations

### chunk_list

Split a list into chunks of a given size. Returns {result: chunks}.

    Args:
        items: Input list.
        size: Chunk size (must be >= 1).

    Returns:
        dict with key ``result`` containing the list of chunks.

    Raises:
        ValueError: If size < 1.


**Tags:** `chunk`, `list`, `split`

**Input:**

- `items` (list[Any]): Input list. size: Chunk size (must be >= 1).
- `size` (int): Chunk size (must be >= 1).

**Output:**

- `result` (dict[str, list[list[Any]]]): dict with key ``result`` containing the list of chunks.


### difference_lists

Return elements in a but not in b (set difference). Returns {result: diff}.

    Args:
        a: Source list.
        b: List of items to exclude.

    Returns:
        dict with key ``result`` containing elements in a that are not in b.


**Tags:** `difference`, `list`, `set`

**Input:**

- `a` (list[Any]): Source list. b: List of items to exclude.
- `b` (list[Any]): List of items to exclude.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing elements in a that are not in b.


### flatten_list

Flatten one level of nesting from a list of lists. Returns {result: flat_list}.

    Args:
        nested: List of lists.

    Returns:
        dict with key ``result`` containing the flattened list.


**Tags:** `flatten`, `list`

**Input:**

- `nested` (list[list[Any]]): List of lists.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing the flattened list.


### intersect_lists

Return elements present in both lists (set intersection). Returns {result: common}.

    Args:
        a: First list.
        b: Second list.

    Returns:
        dict with key ``result`` containing elements in both lists (order from a).


**Tags:** `intersection`, `list`, `set`

**Input:**

- `a` (list[Any]): First list. b: Second list.
- `b` (list[Any]): Second list.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing elements in both lists (order from a).


### map_values

Extract a field from each dict in a list. Returns {result: values}.

    Args:
        items: List of dicts.
        key: Field name to extract from each dict.

    Returns:
        dict with key ``result`` containing the extracted values.


**Tags:** `extraction`, `list`, `map`

**Input:**

- `items` (list[dict[str, Any]]): List of dicts. key: Field name to extract from each dict.
- `key` (str): Field name to extract from each dict.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing the extracted values.


### reduce_sum

Sum all numeric values in a list. Returns {result: total}.

    Args:
        values: List of floats.

    Returns:
        dict with key ``result`` containing the sum.


**Tags:** `list`, `math`, `reduce`, `sum`

**Input:**

- `values` (list[float]): List of floats.

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the sum.


### reverse_list

Return a reversed copy of a list. Returns {result: reversed_list}.

    Args:
        items: Input list.

    Returns:
        dict with key ``result`` containing the list in reverse order.


**Tags:** `list`, `reverse`

**Input:**

- `items` (list[Any]): Input list.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing the list in reverse order.


### take_first_n

Return the first n elements of a list. Returns {result: head}.

    Args:
        items: Input list.
        n: Number of elements to take.

    Returns:
        dict with key ``result`` containing the first n items.


**Tags:** `head`, `list`, `slice`

**Input:**

- `items` (list[Any]): Input list. n: Number of elements to take.
- `n` (int): Input list. n: Number of elements to take.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing the first n items.


### unique_values

Return unique values from a list, preserving order. Returns {result: unique_list}.

    Args:
        items: List potentially containing duplicates.

    Returns:
        dict with key ``result`` containing deduplicated list (first occurrence kept).


**Tags:** `dedup`, `list`, `unique`

**Input:**

- `items` (list[Any]): List potentially containing duplicates.

**Output:**

- `result` (dict[str, list[Any]]): dict with key ``result`` containing deduplicated list (first occurrence kept).


### zip_lists

Zip two lists into a list of [a_val, b_val] pairs. Returns {result: pairs}.

    Args:
        a: First list.
        b: Second list.

    Returns:
        dict with key ``result`` containing paired elements (stops at shorter list).


**Tags:** `combine`, `list`, `zip`

**Input:**

- `a` (list[Any]): First list. b: Second list.
- `b` (list[Any]): Second list.

**Output:**

- `result` (dict[str, list[list[Any]]]): dict with key ``result`` containing paired elements (stops at shorter list).


## Math

### absolute_value

Return the absolute value of a number. Returns {result: absolute}.

    Args:
        value: Input number.

    Returns:
        dict with key ``result`` containing the non-negative value.


**Tags:** `arithmetic`, `math`

**Input:**

- `value` (float): Input number.

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the non-negative value.


### ceil_value

Round value up to nearest integer. Returns {result: ceiling}.

    Args:
        value: Input number.

    Returns:
        dict with key ``result`` containing the ceiling integer.


**Tags:** `math`, `rounding`

**Input:**

- `value` (float): Input number.

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing the ceiling integer.


### clamp_value

Clamp value to [minimum, maximum]. Returns {result: clamped}.

    Args:
        value: The input number.
        minimum: Lower bound (inclusive).
        maximum: Upper bound (inclusive).

    Returns:
        dict with key ``result`` containing the clamped value.


**Tags:** `math`, `range`

**Input:**

- `value` (float): The input number. minimum: Lower bound (inclusive). maximum: Upper bound (inclusive).
- `minimum` (float): Lower bound (inclusive). maximum: Upper bound (inclusive).
- `maximum` (float): Upper bound (inclusive).

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the clamped value.


### divide

Divide a by b. Returns {result: quotient}.

    Args:
        a: Dividend.
        b: Divisor (must not be zero).

    Returns:
        dict with key ``result`` containing the quotient.

    Raises:
        ZeroDivisionError: If b is zero.


**Tags:** `arithmetic`, `math`

**Input:**

- `a` (float): Dividend. b: Divisor (must not be zero).
- `b` (float): Divisor (must not be zero).

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the quotient.


### floor_value

Round value down to nearest integer. Returns {result: floor}.

    Args:
        value: Input number.

    Returns:
        dict with key ``result`` containing the floor integer.


**Tags:** `math`, `rounding`

**Input:**

- `value` (float): Input number.

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing the floor integer.


### max_value

Return the larger of two numbers. Returns {result: maximum}.

    Args:
        a: First number.
        b: Second number.

    Returns:
        dict with key ``result`` containing the maximum.


**Tags:** `comparison`, `math`

**Input:**

- `a` (float): First number. b: Second number.
- `b` (float): First number. b: Second number.

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the maximum.


### min_value

Return the smaller of two numbers. Returns {result: minimum}.

    Args:
        a: First number.
        b: Second number.

    Returns:
        dict with key ``result`` containing the minimum.


**Tags:** `comparison`, `math`

**Input:**

- `a` (float): First number. b: Second number.
- `b` (float): First number. b: Second number.

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the minimum.


### modulo

Compute a modulo b. Returns {result: remainder}.

    Args:
        a: Dividend.
        b: Divisor (must not be zero).

    Returns:
        dict with key ``result`` containing the remainder.

    Raises:
        ZeroDivisionError: If b is zero.


**Tags:** `arithmetic`, `math`

**Input:**

- `a` (float): Dividend. b: Divisor (must not be zero).
- `b` (float): Divisor (must not be zero).

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the remainder.


### percentage

Compute (value / total) * 100. Returns {result: percentage}.

    Args:
        value: The part value.
        total: The whole value (must not be zero).

    Returns:
        dict with key ``result`` containing the percentage.

    Raises:
        ZeroDivisionError: If total is zero.


**Tags:** `math`, `percentage`

**Input:**

- `value` (float): The part value. total: The whole value (must not be zero).
- `total` (float): The whole value (must not be zero).

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the percentage.


### power

Raise base to the power of exponent. Returns {result: power}.

    Args:
        base: The base number.
        exponent: The exponent.

    Returns:
        dict with key ``result`` containing base ** exponent.


**Tags:** `arithmetic`, `math`

**Input:**

- `base` (float): The base number. exponent: The exponent.
- `exponent` (float): The exponent.

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing base ** exponent.


### round_number

Round a number to the specified number of decimal places. Returns {result: rounded}.

    Args:
        value: Input number.
        decimal_places: Number of decimal places (default 0 rounds to integer).

    Returns:
        dict with key ``result`` containing the rounded float.


**Tags:** `math`, `rounding`

**Input:**

- `value` (float): Input number. decimal_places: Number of decimal places (default 0 rounds to integer).
- `decimal_places` (int) (default: 0): Number of decimal places (default 0 rounds to integer).

**Output:**

- `result` (dict[str, float]): dict with key ``result`` containing the rounded float.


## String

### truncate_string

Truncate a string to max_length characters, appending suffix if truncated. Returns {result: str}.

    Args:
        text: Input string.
        max_length: Maximum length of the output string (including suffix).
        suffix: String appended when truncation occurs (default ``"..."``).

    Returns:
        dict with key ``result`` containing the truncated string.


**Tags:** `string`, `truncate`

**Input:**

- `text` (str): Input string. max_length: Maximum length of the output string (including suffix). suffix: String appended when truncation occurs (default ``"..."``).
- `max_length` (int): Maximum length of the output string (including suffix). suffix: String appended when truncation occurs (default ``"..."``).
- `suffix` (str) (default: ...): Maximum length of the output string (including suffix). suffix: String appended when truncation occurs (default ``"..."``).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the truncated string.


## String Processing

### clean_whitespace

Strip leading/trailing whitespace and collapse internal runs. Returns {result: cleaned}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing the cleaned string.


**Tags:** `cleaning`, `string`

**Input:**

- `text` (str): Input string.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the cleaned string.


### concatenate_strings

Join a list of strings with a separator. Returns {result: joined}.

    Args:
        parts: List of strings to join.
        separator: String to place between items (default empty string).

    Returns:
        dict with key ``result`` containing the joined string.


**Tags:** `join`, `string`

**Input:**

- `parts` (list[str]): List of strings to join. separator: String to place between items (default empty string).
- `separator` (str) (default: ): String to place between items (default empty string).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the joined string.


### convert_case

Convert string case. Returns {result: converted}.

    Args:
        text: Input string.
        case: Target case: ``"upper"``, ``"lower"``, ``"title"``, ``"snake"``, ``"camel"``.

    Returns:
        dict with key ``result`` containing the converted string.

    Raises:
        ValueError: If case is not recognized.


**Tags:** `case`, `string`, `transform`

**Input:**

- `text` (str): Input string. case: Target case: ``"upper"``, ``"lower"``, ``"title"``, ``"snake"``, ``"camel"``.
- `case` (str): Target case: ``"upper"``, ``"lower"``, ``"title"``, ``"snake"``, ``"camel"``.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the converted string.


### count_words_chars

Count words and characters in text. Returns {result: {words: int, chars: int}}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing a dict with ``words`` and ``chars`` counts.


**Tags:** `count`, `stats`, `string`

**Input:**

- `text` (str): Input string.

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing a dict with ``words`` and ``chars`` counts.


### extract_emails

Extract all email addresses from text. Returns {result: emails}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing a list of found email addresses.


**Tags:** `email`, `extraction`, `string`

**Input:**

- `text` (str): Input string.

**Output:**

- `result` (dict[str, list[str]]): dict with key ``result`` containing a list of found email addresses.


### extract_markdown_fences

Extract the content of the first markdown code fence. Returns {result: content}.

    Args:
        text: String potentially containing a markdown code fence.

    Returns:
        dict with key ``result`` containing the fence content, or empty string if none found.


**Tags:** `extraction`, `markdown`, `string`

**Input:**

- `text` (str): String potentially containing a markdown code fence.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the fence content, or empty string if none found.


### extract_regex_pattern

Find all non-overlapping matches of a regex pattern. Returns {result: matches}.

    Args:
        text: Input string to search.
        pattern: Regular expression pattern.

    Returns:
        dict with key ``result`` containing a list of matched strings.


**Tags:** `extraction`, `regex`, `string`

**Input:**

- `text` (str): Input string to search. pattern: Regular expression pattern.
- `pattern` (str): Regular expression pattern.

**Output:**

- `result` (dict[str, list[str]]): dict with key ``result`` containing a list of matched strings.


### extract_urls

Extract all http/https URLs from text. Returns {result: urls}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing a list of found URLs.


**Tags:** `extraction`, `string`, `url`

**Input:**

- `text` (str): Input string.

**Output:**

- `result` (dict[str, list[str]]): dict with key ``result`` containing a list of found URLs.


### levenshtein_distance

Compute the Levenshtein edit distance between two strings. Returns {result: distance}.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        dict with key ``result`` containing the edit distance.


**Tags:** `distance`, `similarity`, `string`

**Input:**

- `s1` (str): First string. s2: Second string.
- `s2` (str): Second string.

**Output:**

- `result` (dict[str, int]): dict with key ``result`` containing the edit distance.


### pad_string

Left-pad a string to the given width. Returns {result: padded}.

    Args:
        text: Input string.
        width: Target total width.
        pad_char: Character used for padding (default space).

    Returns:
        dict with key ``result`` containing the padded string.


**Tags:** `padding`, `string`

**Input:**

- `text` (str): Input string. width: Target total width. pad_char: Character used for padding (default space).
- `width` (int): Target total width. pad_char: Character used for padding (default space).
- `pad_char` (str) (default:  ): Character used for padding (default space).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the padded string.


### parse_date_string

Parse a date string with strptime format, return ISO 8601. Returns {result: iso_date}.

    Args:
        date_str: Date string to parse.
        input_format: strptime format string (e.g. ``"%d/%m/%Y"``).

    Returns:
        dict with key ``result`` containing the ISO 8601 date string.


**Tags:** `date`, `parsing`, `string`

**Input:**

- `date_str` (str): Date string to parse. input_format: strptime format string (e.g. ``"%d/%m/%Y"``).
- `input_format` (str): strptime format string (e.g. ``"%d/%m/%Y"``).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the ISO 8601 date string.


### redact_pii_patterns

Redact common PII patterns (email, phone, SSN) with [REDACTED]. Returns {result: redacted}.

    Args:
        text: Input string potentially containing PII.

    Returns:
        dict with key ``result`` containing the redacted string.


**Tags:** `privacy`, `redaction`, `string`

**Input:**

- `text` (str): Input string potentially containing PII.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the redacted string.


### remove_html_tags

Remove all HTML tags from a string. Returns {result: plain_text}.

    Args:
        text: String potentially containing HTML markup.

    Returns:
        dict with key ``result`` containing only the text content.


**Tags:** `cleaning`, `html`, `string`

**Input:**

- `text` (str): String potentially containing HTML markup.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing only the text content.


### replace_substring

Replace all occurrences of old with new in text. Returns {result: replaced}.

    Args:
        text: Input string.
        old: Substring to find.
        new: Replacement string.

    Returns:
        dict with key ``result`` containing the modified string.


**Tags:** `replace`, `string`

**Input:**

- `text` (str): Input string. old: Substring to find. new: Replacement string.
- `old` (str): Substring to find. new: Replacement string.
- `new` (str): Replacement string.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the modified string.


### reverse_string

Reverse a string character by character. Returns {result: reversed}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing the reversed string.


**Tags:** `reverse`, `string`

**Input:**

- `text` (str): Input string.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the reversed string.


### split_by_delimiter

Split a string by delimiter. Returns {result: parts}.

    Args:
        text: Input string.
        delimiter: The separator string.

    Returns:
        dict with key ``result`` containing the list of parts.


**Tags:** `split`, `string`

**Input:**

- `text` (str): Input string. delimiter: The separator string.
- `delimiter` (str): The separator string.

**Output:**

- `result` (dict[str, list[str]]): dict with key ``result`` containing the list of parts.


### starts_ends_with

Check if text starts with prefix AND ends with suffix. Returns {result: bool}.

    Args:
        text: Input string.
        prefix: Required prefix (pass empty string to skip).
        suffix: Required suffix (pass empty string to skip).

    Returns:
        dict with key ``result`` — True if both conditions hold.


**Tags:** `check`, `predicate`, `string`

**Input:**

- `text` (str): Input string. prefix: Required prefix (pass empty string to skip). suffix: Required suffix (pass empty string to skip).
- `prefix` (str): Required prefix (pass empty string to skip). suffix: Required suffix (pass empty string to skip).
- `suffix` (str): Required suffix (pass empty string to skip).

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if both conditions hold.


### strip_punctuation

Remove all punctuation characters from text. Returns {result: stripped}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing text with punctuation removed.


**Tags:** `cleaning`, `punctuation`, `string`

**Input:**

- `text` (str): Input string.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing text with punctuation removed.


### template_string_fill

Fill a template string with {key} placeholders. Returns {result: filled}.

    Args:
        template: String with ``{key}`` placeholders.
        values: Dict mapping placeholder names to replacement values.

    Returns:
        dict with key ``result`` containing the filled string.


**Tags:** `string`, `template`

**Input:**

- `template` (str): String with ``{key}`` placeholders. values: Dict mapping placeholder names to replacement values.
- `values` (dict[str, str]): Dict mapping placeholder names to replacement values.

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the filled string.


### truncate_text

Truncate text to max_length characters, appending '...' if cut. Returns {result: truncated}.

    Args:
        text: Input string.
        max_length: Maximum allowed length (including ellipsis).

    Returns:
        dict with key ``result`` containing the truncated string.


**Tags:** `string`, `truncate`

**Input:**

- `text` (str): Input string. max_length: Maximum allowed length (including ellipsis).
- `max_length` (int): Maximum allowed length (including ellipsis).

**Output:**

- `result` (dict[str, str]): dict with key ``result`` containing the truncated string.


## Validation

### compare_values

Compare two values using an operator. Returns {result: bool}.

    Args:
        a: Left-hand value.
        b: Right-hand value.
        operator: Comparison operator: ``"eq"``, ``"ne"``, ``"lt"``, ``"le"``, ``"gt"``, ``"ge"``.

    Returns:
        dict with key ``result`` containing the comparison result.

    Raises:
        ValueError: If operator is not recognized.


**Tags:** `comparison`, `validation`

**Input:**

- `a` (Any): Left-hand value. b: Right-hand value. operator: Comparison operator: ``"eq"``, ``"ne"``, ``"lt"``, ``"le"``, ``"gt"``, ``"ge"``.
- `b` (Any): Right-hand value. operator: Comparison operator: ``"eq"``, ``"ne"``, ``"lt"``, ``"le"``, ``"gt"``, ``"ge"``.
- `operator` (str): Comparison operator: ``"eq"``, ``"ne"``, ``"lt"``, ``"le"``, ``"gt"``, ``"ge"``.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` containing the comparison result.


### has_required_keys

Check that a dict contains all required keys. Returns {result: bool}.

    Args:
        data: Dictionary to validate.
        required_keys: List of keys that must be present.

    Returns:
        dict with key ``result`` — True if all required keys are present.


**Tags:** `dict`, `keys`, `validation`

**Input:**

- `data` (dict[str, Any]): Dictionary to validate. required_keys: List of keys that must be present.
- `required_keys` (list[str]): List of keys that must be present.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if all required keys are present.


### is_email_valid

Check if a string is a valid email address format. Returns {result: bool}.

    Args:
        email: String to validate.

    Returns:
        dict with key ``result`` — True if email matches standard pattern.


**Tags:** `email`, `validation`

**Input:**

- `email` (str): String to validate.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if email matches standard pattern.


### is_in_range

Check if a number is within [minimum, maximum] inclusive. Returns {result: bool}.

    Args:
        value: Number to check.
        minimum: Lower bound (inclusive).
        maximum: Upper bound (inclusive).

    Returns:
        dict with key ``result`` — True if minimum <= value <= maximum.


**Tags:** `numeric`, `range`, `validation`

**Input:**

- `value` (float): Number to check. minimum: Lower bound (inclusive). maximum: Upper bound (inclusive).
- `minimum` (float): Lower bound (inclusive). maximum: Upper bound (inclusive).
- `maximum` (float): Upper bound (inclusive).

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if minimum <= value <= maximum.


### is_iso_date

Check if a string is a valid ISO 8601 date (YYYY-MM-DD). Returns {result: bool}.

    Args:
        text: String to test.

    Returns:
        dict with key ``result`` — True if parseable as YYYY-MM-DD.


**Tags:** `date`, `iso`, `validation`

**Input:**

- `text` (str): String to test.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if parseable as YYYY-MM-DD.


### is_not_empty

Check that a value is not None, empty string, empty list, or empty dict. Returns {result: bool}.

    Args:
        value: Any value to check.

    Returns:
        dict with key ``result`` — True if value has content.


**Tags:** `empty`, `validation`

**Input:**

- `value` (Any): Any value to check.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if value has content.


### is_numeric_string

Check if a string represents a valid number. Returns {result: bool}.

    Args:
        text: String to test.

    Returns:
        dict with key ``result`` — True if the string can be parsed as a float.


**Tags:** `numeric`, `string`, `validation`

**Input:**

- `text` (str): String to test.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if the string can be parsed as a float.


### is_phone_valid

Check if a string looks like a valid E.164 or US phone number. Returns {result: bool}.

    Args:
        phone: Phone number string.

    Returns:
        dict with key ``result`` — True if the number matches basic patterns.


**Tags:** `phone`, `validation`

**Input:**

- `phone` (str): Phone number string.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if the number matches basic patterns.


### is_url_valid

Check if a string is a valid http/https URL. Returns {result: bool}.

    Args:
        url: String to validate.

    Returns:
        dict with key ``result`` — True if URL has a valid scheme and netloc.


**Tags:** `url`, `validation`

**Input:**

- `url` (str): String to validate.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if URL has a valid scheme and netloc.


### matches_pattern

Check if text fully matches a regex pattern. Returns {result: bool}.

    Args:
        text: String to test.
        pattern: Regular expression pattern.

    Returns:
        dict with key ``result`` — True if the full string matches.


**Tags:** `pattern`, `regex`, `validation`

**Input:**

- `text` (str): String to test. pattern: Regular expression pattern.
- `pattern` (str): Regular expression pattern.

**Output:**

- `result` (dict[str, bool]): dict with key ``result`` — True if the full string matches.
