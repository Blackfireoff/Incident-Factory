-- Add organization_sector column to incidents table
alter table public.incidents
add column if not exists organization_sector text;

-- Update existing records with sample organization sectors
update public.incidents
set organization_sector = case
  when location like '%Production Line%' then 'Production'
  when location like '%Quality%' then 'Quality Control'
  when location like '%Warehouse%' or location like '%Loading%' then 'Logistics'
  when location like '%Chemical%' then 'Chemical Processing'
  when location like '%Electrical%' or location like '%HVAC%' or location like '%Cooling%' then 'Maintenance'
  when location like '%Storage%' then 'Storage'
  else 'General Operations'
end
where organization_sector is null;

-- Create index for faster queries
create index if not exists incidents_organization_sector_idx on public.incidents(organization_sector);
