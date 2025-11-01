-- Add status column to incidents table
alter table public.incidents 
add column if not exists status text not null default 'open';

-- Add check constraint for valid status values
alter table public.incidents
add constraint incidents_status_check 
check (status in ('open', 'in_progress', 'resolved', 'closed'));

-- Create index for status column
create index if not exists incidents_status_idx on public.incidents(status);

-- Update existing records to have varied statuses for demo purposes
update public.incidents
set status = case 
  when classification = 'critical' then 'open'
  when classification = 'high' and random() > 0.5 then 'in_progress'
  when classification = 'medium' and random() > 0.3 then 'resolved'
  when classification = 'low' and random() > 0.6 then 'closed'
  else 'open'
end;
