-- Create corrective measures table
create table if not exists public.corrective_measures (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  name text not null,
  description text not null,
  responsible_person text not null,
  cost numeric(10, 2) not null default 0,
  created_at timestamptz default now()
);

-- Enable RLS
alter table public.corrective_measures enable row level security;

-- Create policies
create policy "corrective_measures_select_all"
  on public.corrective_measures for select
  using (true);

create policy "corrective_measures_insert_all"
  on public.corrective_measures for insert
  with check (true);

create policy "corrective_measures_update_all"
  on public.corrective_measures for update
  using (true);

create policy "corrective_measures_delete_all"
  on public.corrective_measures for delete
  using (true);

-- Create index
create index if not exists corrective_measures_incident_id_idx on public.corrective_measures(incident_id);
