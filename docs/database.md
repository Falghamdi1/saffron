# Database schema

The source of truth is
[`supabase/migrations/0001_schema.sql`](../supabase/migrations/0001_schema.sql).

```mermaid
erDiagram
    AUTH_USERS ||--|| PROFILES : has
    PROFILES ||--o{ CONVERSATIONS : owns
    CONVERSATIONS ||--o{ MESSAGES : contains
    PROFILES ||--o{ PREFERENCES : owns
    PREFERENCES ||--o{ MEMORY_EVENTS : records

    PROFILES {
        uuid id PK
        text display_name
    }
    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        text title
        jsonb context "request state for this chat"
    }
    MESSAGES {
        bigint id PK
        uuid conversation_id FK
        uuid user_id FK
        text role
        text content
        jsonb payload "cards and memory notes"
    }
    PREFERENCES {
        uuid id PK
        uuid user_id FK
        text category
        text value
        text status "active pending superseded retracted"
        text certainty "confirmed inferred"
        bool removal_requested
        text source_text
        timestamptz created_at
        timestamptz updated_at
    }
    MEMORY_EVENTS {
        bigint id PK
        uuid user_id
        uuid preference_id FK
        text event_type
        text reason
        text source_text
        timestamptz created_at
    }
    MENU_ITEMS {
        text id PK
        text name
        text category
        numeric price
        smallint spice_level
        text_array ingredients
        text_array allergens
        text_array may_contain
        text_array diets
        bool available
        bool allergen_info_complete
    }
```

## Integrity rules enforced by the database

| Rule | Mechanism |
| --- | --- |
| One live record per user, category and value | partial unique index |
| A message cannot join another user's conversation | composite key `(conversation_id, user_id)` |
| A history event cannot point at another user's preference | composite key `(preference_id, user_id)` |
| History cannot be edited or deleted | only `select` and `insert` granted |
| Preferences are never deleted, only re-statused | no `delete` grant |
| Users see and change only their own rows | Row Level Security on every table |
| The menu is read-only to users | `select` grant and policy only |

The composite keys matter because foreign key checks bypass Row Level Security.

## Provenance

Each preference keeps the sentence that created it. Each change adds an event with its type,
reason, triggering sentence and time. That history is what the "How it changed" panel shows.
