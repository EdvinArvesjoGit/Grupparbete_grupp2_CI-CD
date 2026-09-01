# Voting Ingestion

## Overview

Voting data is fetched from Riksdagens öppna data API using two
endpoints:

-   `https://data.riksdagen.se/voteringlista/`
-   `https://data.riksdagen.se/votering/{votering_id}`

The ingestion stores data at two different granularities:

-   `stg.votering_summary`: one row per voting event (`votering_id`)
-   `stg.votering`: one row per member and voting event

The script supports both an initial load and an incremental load.

## API Strategy

### Step 1: Fetch and store voting summaries

For each riksmöte (`rm`), the first request uses:

``` text
rm=<riksmöte>
gruppering=votering_id
sz=10000
utformat=json
```

This returns one grouped result for each `votering_id`, including
aggregated vote counts:

``` text
votering_id
Ja
Nej
Avstår
Frånvarande
```

These results are stored in `stg.votering_summary`.

The source fields are mapped as follows:

``` text
Ja           -> ja
Nej          -> nej
Frånvarande  -> franvarande
Avstår       -> avstar
```

The summary table has one row per voting event and uses `votering_id` as
its primary key.

The aggregated vote counts are also used to calculate the expected
number of detailed member records for each voting event.

### Step 2: Fetch detailed voting records

Detailed member records are fetched from:

``` text
https://data.riksdagen.se/votering/{votering_id}
```

This endpoint returns XML. Each `<votering>` element under
`<dokvotering>` represents one member's record in the voting event.

The XML fields are parsed and loaded into `stg.votering`.

The XML source field `<källa>` is mapped to the database column `kalla`.

The audit column `_kalla` stores the API endpoint used to fetch the
data. `_korning_id` identifies the ingestion run, and `_laddad_tidpunkt`
records when the row was loaded.

## Initial Load

The initial load is intended for the first population of an empty
staging area.

For every configured riksmöte:

``` text
fetch all voting summaries
    -> upsert stg.votering_summary
    -> fetch XML details for all voting events
    -> insert member voting records into stg.votering
```

In initial mode, all voting events returned by the summary API are
passed to the detailed XML ingestion.

## Incremental Load

The incremental load is intended for repeated or scheduled runs.

For every configured riksmöte:

1.  Fetch the current voting summaries from `voteringlista`.
2.  Read existing `votering_id` values from `stg.votering`.
3.  Identify voting events whose details have not yet been loaded.
4.  Upsert the current summary results into `stg.votering_summary`.
5.  Fetch XML details only for voting events missing from
    `stg.votering`.

The detail table, rather than the summary table, is used as the
checkpoint for detailed ingestion. This prevents a voting event from
being skipped if its summary was stored successfully but its XML detail
load failed.

The ingestion mode is controlled with:

``` text
INGEST_MODE=init
```

or:

``` text
INGEST_MODE=incremental
```

If no mode is specified, the script defaults to `incremental`.

## Why Use `votering_id` for Ingestion?

Earlier testing used `gruppering=bet`, where `bet` represents a
`beteckning + punkt` combination.

However, SQL validation showed that one `rm + beteckning + punkt`
combination can contain more than one `votering_id`.

Therefore, `beteckning + punkt` describes a voting issue/group and must
not be treated as the identifier of an individual voting event.

Using `gruppering=votering_id` provides the individual voting events
directly. The dedicated `/votering/{votering_id}` endpoint can then
retrieve the detailed member records for each event.

The resulting ingestion flow is:

``` text
riksmöte
    -> voteringlista grouped by votering_id
    -> stg.votering_summary
    -> determine missing detail events
    -> /votering/{votering_id}
    -> member voting records
    -> stg.votering
```

## Validation

### Expected row count

The grouped `voteringlista` response contains counts for `Ja`, `Nej`,
`Avstår`, and `Frånvarande`.

These values are summed to calculate the expected number of member
records. After the XML response is parsed, the number of detailed
records is compared with this expected count.

If the counts do not match, the ingestion raises an error instead of
silently loading an incomplete voting event.

### Voting event identifier

The parsed XML records are checked to verify that their `votering_id`
matches the voting event requested from the API.

### Summary and detail data

The summary table contains the official aggregated counts, while the
detail table contains the individual member votes. This preserves both
API levels and makes it possible to compare aggregated detail records
with the summary values during data-quality validation.

## Identifiers and Table Grain

-   `rm` identifies the riksmöte.
-   `beteckning + punkt` describes the voting issue/group.
-   `votering_id` identifies an individual voting event.
-   `intressent_id` identifies a member.
-   `(votering_id, intressent_id)` identifies an individual member's
    vote.

The two staging tables have different grains:

``` text
stg.votering_summary
    one row per votering_id

stg.votering
    one row per votering_id + intressent_id
```

`stg.votering_summary` uses `votering_id` as its primary key and upserts
the latest aggregated result.

`stg.votering` enforces uniqueness with:

``` sql
UNIQUE (votering_id, intressent_id)
```

and uses:

``` sql
ON CONFLICT (votering_id, intressent_id)
DO NOTHING;
```

to prevent duplicate member voting records.
