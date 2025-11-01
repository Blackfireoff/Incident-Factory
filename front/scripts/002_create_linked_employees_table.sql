-- Create linked employees table (victims, responders, etc.)
create table if not exists public.linked_employees (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  employee_name text not null,
  employee_matricule text not null,
  role text not null, -- 'victim', 'responder', 'witness', etc.
  notes text,
  created_at timestamptz default now()
);

-- Enable RLS
alter table public.linked_employees enable row level security;

-- Create policies
create policy "linked_employees_select_all"
  on public.linked_employees for select
  using (true);

create policy "linked_employees_insert_all"
  on public.linked_employees for insert
  with check (true);

create policy "linked_employees_update_all"
  on public.linked_employees for update
  using (true);

create policy "linked_employees_delete_all"
  on public.linked_employees for delete
  using (true);

-- Create index
create index if not exists linked_employees_incident_id_idx on public.linked_employees(incident_id);
