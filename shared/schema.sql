-- LocalLift schema. Applied at web startup; every statement is idempotent.
-- Contract: see CLAUDE.md. Additions beyond the contract are marked "added".

create table if not exists reps (
  code text primary key, name text not null, upi_id text,
  commission_pct int not null default 30, active boolean default true,
  created_at timestamptz default now());

create table if not exists shops (
  id serial primary key, name text not null, phone text, city text,
  created_at timestamptz default now());

create table if not exists orders (
  id serial primary key,
  shop_id int references shops(id),
  rep_code text references reps(code),
  festival text not null,
  languages text[] not null,
  offer_text text not null,
  logo bytea, logo_mime text,
  plan text not null,
  amount_inr int not null,
  status text not null default 'preview',
  payment_ref text,
  download_token text unique,
  is_sample boolean not null default false,
  created_at timestamptz default now(), paid_at timestamptz);

-- added: unguessable token for the preview page, so order pages are not enumerable by id
alter table orders add column if not exists view_token text unique;

create table if not exists pack_items (
  id serial primary key,
  order_id int references orders(id),
  kind text not null,
  language text not null,
  size text not null default '',
  template_id text not null default '',  -- messages use it as the slot: wa1 | wa2 | wa3 | review
  body text,
  mime text, file_bytes bytea, preview_bytes bytea,
  qa_status text not null default 'pending',
  qa_notes text,
  created_at timestamptz default now(),
  unique (order_id, kind, language, size, template_id));

create table if not exists ledger (
  id serial primary key, order_id int references orders(id),
  rep_code text references reps(code), amount_inr int not null,
  status text not null default 'pending',
  created_at timestamptz default now());

-- added: one commission row per order, so approving twice cannot pay twice
create unique index if not exists ledger_order_uniq on ledger(order_id);

create table if not exists events (
  id bigserial primary key, ts timestamptz default now(),
  kind text not null,
  order_id int, rep_code text, meta jsonb);

create index if not exists events_kind_idx on events(kind);
