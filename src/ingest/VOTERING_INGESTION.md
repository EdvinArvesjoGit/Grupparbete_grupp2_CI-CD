# Voting Ingestion

## Overview

Voting data is fetched from Riksdagens öppna data API using two endpoints:

- `https://data.riksdagen.se/voteringlista/`
- `https://data.riksdagen.se/votering/{votering_id}`

The ingestion uses `votering_id` as the unit for detecting and fetching new voting events.

The first endpoint is used to discover voting events for each riksmöte (`rm`). The second endpoint returns the detailed member voting records for one specific voting event in XML format.

## API Strategy

The ingestion is performed in two steps for each riksmöte (`rm`).

### Step 1: Fetch voting events

The first request uses:

```text
rm=<riksmöte>
gruppering=votering_id
sz=10000
utformat=json
```

This returns one grouped result for each `votering_id`.

For example, each result contains the voting event identifier together with aggregated vote counts such as:

```text
votering_id
Ja
Nej
Avstår
Frånvarande
```

The vote counts are also used to calculate the expected number of detailed member records for the voting event.

Existing `votering_id` values in `stg.votering` are compared with the API result so that only new voting events are fetched.

### Step 2: Fetch detailed voting records

For each new `votering_id`, the detailed records are fetched from:

```text
https://data.riksdagen.se/votering/{votering_id}
```

This endpoint returns XML.

The individual voting records are located under:

```xml
<dokvotering>
    <votering>
        ...
    </votering>
</dokvotering>
```

Each outer `<votering>` element represents one member's record in the voting event.

The XML fields are parsed and loaded into `stg.votering`.

The XML source field `<källa>` is mapped to the database column `kalla`.

The audit column `_kalla` stores the API endpoint used to fetch the voting event, for example:

```text
https://data.riksdagen.se/votering/{votering_id}
```

## Why Use `votering_id` for Ingestion?

Earlier testing used:

```text
gruppering=bet
```

where `bet` represents a `beteckning + punkt` combination.

This approach could be used to fetch groups and then retrieve detailed records using:

```text
rm + bet + punkt
```

However, SQL validation showed that one `rm + beteckning + punkt` combination can contain more than one `votering_id`.

Therefore, `beteckning + punkt` represents an issue/group and must not be treated as the identifier of an individual voting event.

Further API testing showed that:

```text
gruppering=votering_id
```

can be used to discover the individual voting events, and the dedicated endpoint:

```text
/votering/{votering_id}
```

can then be used to retrieve the detailed member records for each event.

This provides a more direct ingestion flow:

```text
riksmöte
    -> grouped votering_id values
    -> new votering_id values
    -> /votering/{votering_id}
    -> member voting records
    -> stg.votering
```

## Validation

### Expected row count

The grouped `voteringlista` response contains counts for:

- `Ja`
- `Nej`
- `Avstår`
- `Frånvarande`

These values are summed to calculate the expected number of member records.

After the XML response is parsed, the number of detailed records is compared with this expected count.

If the counts do not match, the ingestion raises an error instead of silently loading an incomplete voting event.

### Voting event identifier

The parsed XML records are also checked to verify that their `votering_id` matches the voting event requested from the API.

### Voting groups

SQL validation shows that one `rm + beteckning + punkt` combination can contain multiple `votering_id` values.

This confirms that:

- `rm + beteckning + punkt` represents a voting issue/group.
- `votering_id` identifies an individual voting event.
- `(votering_id, intressent_id)` identifies an individual member's vote.

## Identifiers

The ingestion uses the identifiers for different purposes:

- `rm` identifies the riksmöte.
- `beteckning + punkt` describes the voting issue/group.
- `votering_id` identifies an individual voting event.
- `intressent_id` identifies a member.
- `(votering_id, intressent_id)` identifies an individual member's vote.

The staging table enforces uniqueness with:

```sql
UNIQUE (votering_id, intressent_id)
```

The insert also uses:

```sql
ON CONFLICT (votering_id, intressent_id)
DO NOTHING;
```

This prevents duplicate member voting records from being inserted.

## Incremental Loading

For each riksmöte, the ingestion reads the existing `votering_id` values from `stg.votering`.

These are compared with the grouped `votering_id` values returned by the API.

Only voting events that do not already exist in the staging table are fetched from the XML endpoint and inserted.

This allows the ingestion script to be run repeatedly without reloading voting events that have already been stored.
