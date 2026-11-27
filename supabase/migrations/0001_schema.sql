-- Saffron AI schema. Safe to run repeatedly.
--
-- Tables live in the "app" schema, which Supabase does not expose through its
-- public Data API. The backend is the only client, so memory rules cannot be
-- bypassed by calling the database API with a user token. Row Level Security
-- still applies to every backend query made on behalf of a user.

create schema if not exists app;

create table if not exists app.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    display_name text not null check (char_length(display_name) between 1 and 80),
    created_at timestamptz not null default now()
);

create table if not exists app.menu_items (
    id text primary key,
    name text not null unique,
    category text not null check (category in ('starter', 'main', 'dessert', 'drink')),
    cuisine text not null,
    price numeric(8, 2) not null check (price > 0),
    spice_level smallint not null check (spice_level between 0 and 3),
    description text not null,
    ingredients text[] not null check (cardinality(ingredients) > 0),
    allergens text[] not null default '{}',
    may_contain text[] not null default '{}',
    diets text[] not null default '{}',
    available boolean not null default true,
    allergen_info_complete boolean not null default true
);

create table if not exists app.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app.profiles (id) on delete cascade,
    title text not null check (char_length(title) <= 80),
    context jsonb not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (id, user_id)
);
create index if not exists conversations_user_recent
    on app.conversations (user_id, updated_at desc);

create table if not exists app.messages (
    id bigint generated always as identity primary key,
    conversation_id uuid not null,
    user_id uuid not null,
    role text not null check (role in ('user', 'assistant')),
    content text not null check (char_length(content) <= 4000),
    payload jsonb not null default '{}',
    created_at timestamptz not null default now(),
    -- The composite key stops a message being attached to another user's chat.
    foreign key (conversation_id, user_id)
        references app.conversations (id, user_id) on delete cascade
);
create index if not exists messages_conversation on app.messages (conversation_id, id);

create table if not exists app.preferences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app.profiles (id) on delete cascade,
    category text not null check (category in (
        'allergy', 'diet', 'like', 'dislike', 'cuisine', 'spice', 'budget', 'favorite_dish')),
    value text not null check (char_length(value) between 1 and 60),
    status text not null check (status in ('active', 'pending', 'superseded', 'retracted')),
    certainty text not null check (certainty in ('confirmed', 'inferred')),
    removal_requested boolean not null default false,
    source_text text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (id, user_id)
);
-- At most one live record per fact. Older records remain as history.
create unique index if not exists preferences_one_live
    on app.preferences (user_id, category, value) where status in ('active', 'pending');

create table if not exists app.memory_events (
    id bigint generated always as identity primary key,
    user_id uuid not null,
    preference_id uuid not null,
    event_type text not null check (event_type in (
        'created', 'proposed', 'confirmed', 'reinforced', 'reaffirmed',
        'superseded', 'retracted', 'removal_requested', 'dismissed')),
    category text not null,
    value text not null,
    reason text not null,
    source_text text not null default '',
    created_at timestamptz not null default now(),
    foreign key (preference_id, user_id)
        references app.preferences (id, user_id) on delete cascade
);
create index if not exists memory_events_user on app.memory_events (user_id, id desc);

alter table app.profiles enable row level security;
alter table app.menu_items enable row level security;
alter table app.conversations enable row level security;
alter table app.messages enable row level security;
alter table app.preferences enable row level security;
alter table app.memory_events enable row level security;

drop policy if exists own_profile on app.profiles;
create policy own_profile on app.profiles to authenticated
    using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists read_menu on app.menu_items;
create policy read_menu on app.menu_items for select to authenticated using (true);

drop policy if exists own_conversations on app.conversations;
create policy own_conversations on app.conversations to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists own_messages on app.messages;
create policy own_messages on app.messages to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists own_preferences on app.preferences;
create policy own_preferences on app.preferences to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists own_memory_events on app.memory_events;
create policy own_memory_events on app.memory_events to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Least privilege: preferences cannot be deleted and history cannot be edited.
revoke all on all tables in schema app from authenticated;
grant usage on schema app to authenticated;
grant select on app.menu_items to authenticated;
grant select, insert, update on app.profiles to authenticated;
grant select, insert, update, delete on app.conversations to authenticated;
grant select, insert on app.messages to authenticated;
grant select, insert, update on app.preferences to authenticated;
grant select, insert on app.memory_events to authenticated;
