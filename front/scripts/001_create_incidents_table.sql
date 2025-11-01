-- Create incidents table
create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  employee_matricule text not null,
  type text not null,
  classification text not null,
  start_date timestamptz not null,
  end_date timestamptz,
  description text not null,
  reporter_name text not null,
  reporter_email text,
  reporter_phone text,
  location text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Enable RLS
alter table public.incidents enable row level security;

-- Create policies for public access (adjust based on your auth requirements)
create policy "incidents_select_all"
  on public.incidents for select
  using (true);

create policy "incidents_insert_all"
  on public.incidents for insert
  with check (true);

create policy "incidents_update_all"
  on public.incidents for update
  using (true);

create policy "incidents_delete_all"
  on public.incidents for delete
  using (true);

-- Create index for faster queries
create index if not exists incidents_employee_matricule_idx on public.incidents(employee_matricule);
create index if not exists incidents_type_idx on public.incidents(type);
create index if not exists incidents_classification_idx on public.incidents(classification);
create index if not exists incidents_start_date_idx on public.incidents(start_date);
