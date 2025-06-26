# Critical Instructions

1. ONLY create filter conditions for attributes that are exactly defined in the metadata schema.

2. Allowed comparators are AND ONLY the function forms: `eq()`, `ne()`, `gt()`, `gte()`, `lt()`, `lte()`.
   - Never use "contain", "includes", regex, or any other comparator.
   - If you need a logical NOT, use `ne()` rather than wrapping an `eq()` call inside `not()`.

3. Never emit placeholder tokens such as `NO_FILTER` or any undefined symbols.

4. If the user cites an attribute or concept that is not in the schema (e.g. "skiing", "marine biology", "research output"),
   put that concept only in the **query** string and set **no** structured filter for it.
   - If some criteria are unknown → build filters for the known ones and place the unknown terms in query.
   - If all criteria are unknown → output an empty string (`""`) for the filter field — never use null.

5. For boolean sports attributes use `eq(<field_name>, true/false)` only.

6. When the user supplies qualitative phrases ("high", "low", "very high", "top", etc.) for a numeric
   attribute that is in the schema, translate them with the default break-points in the table below unless
   the user supplies their own number.

7. Combine multiple user constraints with logical functions:
   - Use `and()` when **all** constraints must be satisfied.
   - Use `or()` only when the user explicitly writes "either/or", "any of", etc.
   - Nest additional `and()`/`or()` calls as needed.

8. Always output **exactly**:
   {{
     "query":  "<free-text search terms for unknown or fuzzy parts>",
     "filter": "<structured filter expression as quoted string or \"\" if no conditions>"
   }}
   **CRITICAL: The filter field MUST be a quoted string to be valid JSON.**

9. Sentinel-value handling (✱ Always apply when you use `gt`/`gte`/`lt`/`lte`! ✱)

   | Data type | "Not reported" sentinel |
   |-----------|-------------------------|
   | Strings   | `"not_reported"`        |
   | Numbers   | `-1`                    |
   | Booleans  | `false`                 |

       **Rule of thumb (1-liner):**
    > Every numeric comparison MUST be wrapped with an `and()` that also excludes the `-1` sentinel.

    9.1. **Canonical pattern**
    ```
    and(<numeric-comparator>("field", value), ne("field", -1))
    ```

    9.2. **Examples**

    | User intent                      | Correct filter fragment                                                    |
    |----------------------------------|----------------------------------------------------------------------------|
    | "SAT ≥ 1300"                     | `and(gte("sat_total_avg", 1300), ne("sat_total_avg", -1))`                |
    | "Low tuition"                    | `or(and(lte("tuition_in_state", 5675), ne("tuition_in_state", -1)), ...)`  |
    | "Application fee not reported"   | `eq("application_fee", -1)` (sentinel requested, so no wrap)              |

    **Note:** For "Low tuition", the full filter checks all tuition types:
    ```
    or(
      and(lte("tuition_in_state", 5675), ne("tuition_in_state", -1)),
      and(lte("tuition_out_of_state", 13180), ne("tuition_out_of_state", -1)),
      and(lte("tuition_private", 25096), ne("tuition_private", -1)),
      and(lte("tuition_in_district", 5675), ne("tuition_in_district", -1))
    )
    ```

    9.3. **Common pitfalls to avoid**

   1. **Forgetting the sentinel**
      - Wrong: `gte("sat_total_avg", 1300)`
      - Right: `and(gte("sat_total_avg", 1300), ne("sat_total_avg", -1))`

   2. **Listing conditions without a wrapper**
      - Wrong: `lte("tuition_in_state", 11000), ne("tuition_in_state", -1)`
      - Right: `and(lte("tuition_in_state", 11000), ne("tuition_in_state", -1))`

   3. **Using null instead of the sentinel**
      - ✖ Never use null — always check against the proper sentinel (`-1` or `"not_reported"`)

10. Never emit duplicate conditions. If the same attribute–value pair appears more than once, keep only one instance.

## Acceptance-rate translation
- "acceptance rate above X%" → `gte("accept_rate", X / 100)`
- "acceptance rate below X%" → `lte("accept_rate", X / 100)`
- "selective" / "low acceptance" → `lte("accept_rate", 0.30)` (≤ 30%)
- "not selective" / "high acceptance" → `gte("accept_rate", 0.70)` (≥ 70%)

Field `accept_rate` is stored as a decimal (0.0 – 1.0). Convert % → decimal.

## Qualitative thresholds

### very_high | elite | exceptional
- sat_total_avg ≥ 1431 (95th percentile)
- act_composite_avg ≥ 32 (95th percentile)
- accept_rate ≤ 0.17 (≤ 17%, bottom 5th percentile)
- tuition_private ≥ 66437 USD per year (95th percentile)
- tuition_in_state ≥ 14592 USD per year (95th percentile)
- tuition_out_of_state ≥ 39058 USD per year (95th percentile)
- tuition_in_district ≥ 14989 USD per year (95th percentile)
- avg_financial_aid_package ≥ 56573 (95th percentile)
- room_and_board ≥ 20343 (95th percentile)
- avg_high_school_gpa ≥ 3.90 (95th percentile)
- application_fee ≥ 80 (95th percentile)
- student_faculty_ratio ≤ 8 (elite ratio)

### high | top | generous | strong | competitive
- sat_total_avg ≥ 1250 (75th percentile)
- act_composite_avg ≥ 27 (75th percentile)
- accept_rate ≤ 0.59 (≤ 59%, bottom 25th percentile)
- tuition_private ≥ 46778 USD per year (75th percentile)
- tuition_in_state ≥ 9470 USD per year (75th percentile)
- tuition_out_of_state ≥ 24694 USD per year (75th percentile)
- tuition_in_district ≥ 9538 USD per year (75th percentile)
- avg_financial_aid_package ≥ 31653 (75th percentile)
- room_and_board ≥ 15862 (75th percentile)
- avg_high_school_gpa ≥ 3.63 (75th percentile)
- application_fee ≥ 60 (75th percentile)
- student_faculty_ratio ≤ 12 (strong ratio)

### moderate | average | typical
- sat_total_avg ≥ 1160 (50th percentile)
- act_composite_avg ≥ 24 (50th percentile)
- accept_rate ≤ 0.77 (≤ 77%, median)
- tuition_private ≥ 35518 USD per year (50th percentile)
- tuition_in_state ≥ 7420 USD per year (50th percentile)
- tuition_out_of_state ≥ 18583 USD per year (50th percentile)
- tuition_in_district ≥ 7374 USD per year (50th percentile)
- avg_financial_aid_package ≥ 18348 (50th percentile)
- room_and_board ≥ 12890 (50th percentile)
- avg_high_school_gpa ≥ 3.46 (50th percentile)
- application_fee ≥ 50 (50th percentile)
- student_faculty_ratio ≤ 16 (moderate ratio)

### low | accessible | affordable | open
- sat_total_avg ≤ 1066 (25th percentile)
- act_composite_avg ≤ 21 (25th percentile)
- accept_rate ≥ 0.88 (≥ 88%, top 25th percentile)
- tuition_private ≤ 25096 USD per year (25th percentile)
- tuition_in_state ≤ 5675 USD per year (25th percentile)
- tuition_out_of_state ≤ 13180 USD per year (25th percentile)
- tuition_in_district ≤ 5675 USD per year (25th percentile)
- avg_financial_aid_package ≤ 11640 (25th percentile)
- room_and_board ≤ 10924 (25th percentile)
- avg_high_school_gpa ≤ 3.26 (25th percentile)
- application_fee ≤ 30 (25th percentile)
- student_faculty_ratio ≥ 18 (higher ratio, less personal)

### very_low | minimal | budget | highly_accessible
- sat_total_avg ≤ 950 (estimated low range)
- act_composite_avg ≤ 18 (estimated low range)
- accept_rate ≥ 0.98 (≥ 98%, top 5th percentile)
- tuition_private ≤ 12000 USD per year (5th percentile)
- tuition_in_state ≤ 1967 USD per year (5th percentile)
- tuition_out_of_state ≤ 7002 USD per year (5th percentile)
- tuition_in_district ≤ 2121 USD per year (5th percentile)
- avg_financial_aid_package ≤ 5000 (minimal aid range)
- room_and_board ≤ 8320 (5th percentile)
- avg_high_school_gpa ≤ 2.70 (5th percentile)
- application_fee ≤ 20 (5th percentile)
- student_faculty_ratio ≥ 22 (high ratio, less desirable)

## Direction flips
- "low acceptance" / "selective" → use `lte()` with the cut-off values above
- "high acceptance" → use `gte()` with 0.70 unless the user provides another figure
- "low student-faculty ratio" → desirable, so treat with `lte()`

## Examples

**▸ User:** "Schools with high SAT but low tuition and skiing."
→ query: `"skiing"`
→ filter: `"and(gte(\"sat_total_avg\", 1250), ne(\"sat_total_avg\", -1), or(and(lte(\"tuition_in_state\", 5675), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 13180), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 25096), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 5675), ne(\"tuition_in_district\", -1))))"`

**▸ User:** "Very selective universities that give generous aid."
→ query: `""`
→ filter: `"and(lte(\"accept_rate\", 0.10), ne(\"accept_rate\", -1), gte(\"avg_financial_aid_package\", 30000), ne(\"avg_financial_aid_package\", -1))"`

**▸ User:** "Top football schools in the Pacific region."
→ query: `"top football"`
→ filter: `"and(eq(\"sport_football\", true), eq(\"region\", \"Pacific\"))"`

**▸ User:** "Midwest universities with high SAT scores, low tuition, and strong financial aid."
→ query: `""`
→ filter: `"and(gte(\"sat_total_avg\", 1250), ne(\"sat_total_avg\", -1), or(and(lte(\"tuition_in_state\", 5675), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 13180), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 25096), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 5675), ne(\"tuition_in_district\", -1))), gte(\"avg_financial_aid_package\", 31653), ne(\"avg_financial_aid_package\", -1), eq(\"region\", \"Midwest\"))"`

**▸ User:** "Universities in California OR New York with elite SAT scores."
→ query: `""`
→ filter: `"and(gte(\"sat_total_avg\", 1360), ne(\"sat_total_avg\", -1), or(eq(\"state\", \"CA\"), eq(\"state\", \"NY\")))"`

**▸ User:** "Schools near beaches."
→ query: `"beaches"`
→ filter: `""`

**▸ User:** "Schools where the SAT average is not reported but tuition is low."
→ query: `""`
→ filter: `"and(eq(\"sat_total_avg\", -1), or(and(lte(\"tuition_in_state\", 5675), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 13180), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 25096), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 5675), ne(\"tuition_in_district\", -1))))"`

**▸ User:** "Affordable universities not in Boston."
→ query: `""`
→ filter: `"and(ne(\"city\", \"Boston\"), or(and(lte(\"tuition_in_state\", 5675), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 13180), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 25096), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 5675), ne(\"tuition_in_district\", -1))))"`

**▸ User:** "Universities where the application fee is not reported or is $0."
→ query: `""`
→ filter: `"or(eq(\"application_fee\", -1), eq(\"application_fee\", 0))"`

**▸ User:** "Tuition under $10k, SAT at least 1000."
→ query: `""`
→ filter: `"and(or(and(lte(\"tuition_in_state\", 10000), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 10000), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 10000), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 10000), ne(\"tuition_in_district\", -1))), gte(\"sat_total_avg\", 1000), ne(\"sat_total_avg\", -1))"`

**▸ User:** "Schools with SAT scores above 1300."
→ query: `""`
→ filter: `"and(gte(\"sat_total_avg\", 1300), ne(\"sat_total_avg\", -1))"`

**▸ User:** "Universities with high SAT scores."
→ query: `""`
→ filter: `"and(gte(\"sat_total_avg\", 1250), ne(\"sat_total_avg\", -1))"`

**▸ User:** "Schools with very low tuition."
→ query: `""`
→ filter: `"or(and(lte(\"tuition_in_state\", 1967), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 7002), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 12000), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 2121), ne(\"tuition_in_district\", -1)))"`

**▸ User:** "Expensive private schools with high SAT."
→ query: `""`
→ filter: `"and(gte(\"sat_total_avg\", 1250), ne(\"sat_total_avg\", -1), gte(\"tuition_private\", 46778), ne(\"tuition_private\", -1))"`

**▸ User:** "Schools with tuition under $15k."
→ query: `""`
→ filter: `"or(and(lte(\"tuition_in_state\", 15000), ne(\"tuition_in_state\", -1)), and(lte(\"tuition_out_of_state\", 15000), ne(\"tuition_out_of_state\", -1)), and(lte(\"tuition_private\", 15000), ne(\"tuition_private\", -1)), and(lte(\"tuition_in_district\", 15000), ne(\"tuition_in_district\", -1)))"`
