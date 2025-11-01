-- Create risks table
create table if not exists public.risks (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  level text not null check (level in ('critical', 'high', 'medium', 'low')),
  description text not null,
  created_at timestamptz default now()
);

-- Enable RLS
alter table public.risks enable row level security;

-- Create policies
create policy "risks_select_all"
  on public.risks for select
  using (true);

create policy "risks_insert_all"
  on public.risks for insert
  with check (true);

create policy "risks_update_all"
  on public.risks for update
  using (true);

create policy "risks_delete_all"
  on public.risks for delete
  using (true);

-- Create index
create index if not exists risks_incident_id_idx on public.risks(incident_id);
