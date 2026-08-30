# Voting Ingestion

## Overview

Voting data is fetched from the Riksdagen voting API:

`https://data.riksdagen.se/voteringlista/`

The ingestion uses `beteckning + punkt` as the API fetch group.

This decision is based on tests performed in Postman and validation
queries against the staging data.

## API Strategy

The ingestion is performed in two steps for each riksmöte (`rm`).

### Step 1: Fetch voting groups

The first request uses:

``` text
rm=<riksmöte>
gruppering=bet
sz=10000
utformat=json
```

Although the API parameter is named `bet`, the Riksdagen search
interface describes this grouping as:

``` text
Votering (bet + punkt)
```

The returned groups represent combinations of `beteckning` and `punkt`.

For example:

``` text
2025/26:AU10p3
```

represents:

``` text
rm = 2025/26
beteckning = AU10
punkt = 3
```

### Step 2: Fetch detailed voting records

Each returned `beteckning + punkt` combination is then used to fetch the
detailed voting records:

``` text
rm=<riksmöte>
bet=<beteckning>
punkt=<punkt>
sz=10000
utformat=json
```

This request returns the individual member voting records for the
selected group. These records are then loaded into `stg.votering`.

## Why Use `beteckning + punkt` for API Fetching?

Different API approaches were tested in Postman.

### Grouping by `votering_id`

The API supports:

``` text
gruppering=votering_id
```

This successfully returns the voting events for a riksmöte.

For example, `rm=2025/26` returned 794 unique `votering_id` groups.

However, `votering_id` could not be used as a filter in a second
`voteringlista` request to retrieve the detailed member voting records.

When `votering_id` was supplied as a filter, the API did not restrict
the result to that voting event and returned up to the configured
`sz=10000` rows.

Therefore, grouping by `votering_id` cannot be used for the complete
two-step ingestion flow.

### Grouping by `bet`

Using:

``` text
gruppering=bet
```

returns the `beteckning + punkt` groups for a riksmöte.

These values can then be used successfully as filters in the second API
request:

``` text
rm + bet + punkt
```

This returns the detailed member voting records for the selected voting
group.

For this reason, `beteckning + punkt` is used as the API fetch unit.

## SQL Validation

The staging data was checked to compare the number of
`beteckning + punkt` combinations with the number of unique
`votering_id` values.

  rm          beteckning + punkt   votering_id
  --------- -------------------- -------------
  2022/23                    562           565
  2023/24                    589           594
  2024/25                    649           652
  2025/26                    787           794

The number of `beteckning + punkt` groups for every riksmöte is well
below the API limit of 10,000 results.

Therefore, all voting groups for one riksmöte can be fetched in a single
grouped request using:

``` text
gruppering=bet
sz=10000
```

The SQL validation also shows that one `beteckning + punkt` combination
can be associated with more than one `votering_id`.

Therefore, `beteckning + punkt` is used only as the API fetch group. It
is not treated as the unique identifier of a voting event.

## Identifiers

The ingestion uses the fields for different purposes:

-   `rm` identifies the riksmöte.
-   `beteckning + punkt` identifies the group used for API fetching.
-   `votering_id` identifies an individual voting event.
-   `(votering_id, intressent_id)` identifies an individual member's
    vote.

The staging table enforces uniqueness for individual member votes with:

``` sql
UNIQUE (votering_id, intressent_id)
```

The insert also uses:

``` sql
ON CONFLICT (votering_id, intressent_id)
DO NOTHING;
```

This prevents duplicate member voting records from being inserted.
