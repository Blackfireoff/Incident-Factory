-- Insert sample incidents
insert into public.incidents (id, employee_matricule, type, classification, start_date, end_date, description, reporter_name, reporter_email, reporter_phone, location)
values
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'EMP001', 'Equipment Failure', 'Major', '2024-01-15 08:30:00+00', '2024-01-15 12:00:00+00', 'Injection molding machine malfunction causing production halt', 'John Smith', 'john.smith@factory.com', '+1-555-0101', 'Production Line A - Station 3'),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'EMP002', 'Safety Incident', 'Critical', '2024-01-20 14:15:00+00', '2024-01-20 14:45:00+00', 'Worker exposed to chemical fumes due to ventilation system failure', 'Sarah Johnson', 'sarah.johnson@factory.com', '+1-555-0102', 'Chemical Storage Area B'),
  ('c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f', 'EMP003', 'Quality Issue', 'Minor', '2024-01-25 10:00:00+00', '2024-01-25 11:30:00+00', 'Batch of plastic containers failed quality inspection due to improper cooling', 'Michael Chen', 'michael.chen@factory.com', '+1-555-0103', 'Quality Control Lab'),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'EMP004', 'Environmental', 'Major', '2024-02-01 16:00:00+00', '2024-02-01 18:30:00+00', 'Plastic pellet spill in loading dock area', 'Emily Rodriguez', 'emily.rodriguez@factory.com', '+1-555-0104', 'Loading Dock 2'),
  ('e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b', 'EMP005', 'Equipment Failure', 'Minor', '2024-02-05 09:45:00+00', '2024-02-05 10:15:00+00', 'Conveyor belt motor overheating', 'David Lee', 'david.lee@factory.com', '+1-555-0105', 'Production Line B - Station 1'),
  ('f6a7b8c9-d0e1-4f5a-3b4c-5d6e7f8a9b0c', 'EMP006', 'Safety Incident', 'Major', '2024-02-10 13:20:00+00', '2024-02-10 14:00:00+00', 'Near-miss incident with forklift in warehouse', 'Lisa Wang', 'lisa.wang@factory.com', '+1-555-0106', 'Warehouse Section C'),
  ('a7b8c9d0-e1f2-4a5b-4c5d-6e7f8a9b0c1d', 'EMP007', 'Quality Issue', 'Minor', '2024-02-15 11:30:00+00', '2024-02-15 12:00:00+00', 'Color inconsistency in plastic bottles', 'Robert Taylor', 'robert.taylor@factory.com', '+1-555-0107', 'Production Line C - Station 2'),
  ('b8c9d0e1-f2a3-4b5c-5d6e-7f8a9b0c1d2e', 'EMP008', 'Equipment Failure', 'Critical', '2024-02-20 07:00:00+00', '2024-02-20 15:00:00+00', 'Main power transformer failure affecting entire facility', 'Jennifer Martinez', 'jennifer.martinez@factory.com', '+1-555-0108', 'Electrical Room - Main Building'),
  ('c9d0e1f2-a3b4-4c5d-6e7f-8a9b0c1d2e3f', 'EMP009', 'Safety Incident', 'Minor', '2024-02-25 15:45:00+00', '2024-02-25 16:00:00+00', 'Minor hand injury from sharp edge on equipment', 'Thomas Anderson', 'thomas.anderson@factory.com', '+1-555-0109', 'Production Line A - Station 5'),
  ('d0e1f2a3-b4c5-4d5e-7f8a-9b0c1d2e3f4a', 'EMP010', 'Environmental', 'Minor', '2024-03-01 12:00:00+00', '2024-03-01 13:00:00+00', 'Excessive noise levels detected in production area', 'Amanda White', 'amanda.white@factory.com', '+1-555-0110', 'Production Line B'),
  ('e1f2a3b4-c5d6-4e5f-8a9b-0c1d2e3f4a5b', 'EMP011', 'Quality Issue', 'Major', '2024-03-05 08:15:00+00', '2024-03-05 10:30:00+00', 'Contamination found in raw material batch', 'Christopher Brown', 'christopher.brown@factory.com', '+1-555-0111', 'Raw Material Storage'),
  ('f2a3b4c5-d6e7-4f5a-9b0c-1d2e3f4a5b6c', 'EMP012', 'Equipment Failure', 'Minor', '2024-03-10 14:30:00+00', '2024-03-10 15:00:00+00', 'Cooling system pressure drop', 'Patricia Garcia', 'patricia.garcia@factory.com', '+1-555-0112', 'Cooling Tower 1'),
  ('a3b4c5d6-e7f8-4a5b-0c1d-2e3f4a5b6c7d', 'EMP013', 'Safety Incident', 'Major', '2024-03-15 10:00:00+00', '2024-03-15 11:30:00+00', 'Chemical spill during transfer operation', 'Daniel Wilson', 'daniel.wilson@factory.com', '+1-555-0113', 'Chemical Processing Area'),
  ('b4c5d6e7-f8a9-4b5c-1d2e-3f4a5b6c7d8e', 'EMP014', 'Quality Issue', 'Minor', '2024-03-20 09:00:00+00', '2024-03-20 09:30:00+00', 'Dimensional variance in molded parts', 'Michelle Davis', 'michelle.davis@factory.com', '+1-555-0114', 'Quality Control - Inspection Station'),
  ('c5d6e7f8-a9b0-4c5d-2e3f-4a5b6c7d8e9f', 'EMP015', 'Environmental', 'Major', '2024-03-25 16:30:00+00', '2024-03-25 18:00:00+00', 'Air filtration system malfunction', 'Kevin Moore', 'kevin.moore@factory.com', '+1-555-0115', 'HVAC System - Building A'),
  ('d6e7f8a9-b0c1-4d5e-3f4a-5b6c7d8e9f0a', 'EMP016', 'Equipment Failure', 'Minor', '2024-03-30 11:15:00+00', '2024-03-30 11:45:00+00', 'Hydraulic pump leak', 'Nancy Thompson', 'nancy.thompson@factory.com', '+1-555-0116', 'Production Line C - Station 4'),
  ('e7f8a9b0-c1d2-4e5f-4a5b-6c7d8e9f0a1b', 'EMP017', 'Safety Incident', 'Critical', '2024-04-01 13:00:00+00', '2024-04-01 14:30:00+00', 'Fire alarm triggered due to overheated equipment', 'Steven Jackson', 'steven.jackson@factory.com', '+1-555-0117', 'Production Line A - Station 7'),
  ('f8a9b0c1-d2e3-4f5a-5b6c-7d8e9f0a1b2c', 'EMP018', 'Quality Issue', 'Minor', '2024-04-05 10:30:00+00', '2024-04-05 11:00:00+00', 'Surface defects on finished products', 'Laura Martin', 'laura.martin@factory.com', '+1-555-0118', 'Final Inspection Area'),
  ('a9b0c1d2-e3f4-4a5b-6c7d-8e9f0a1b2c3d', 'EMP019', 'Equipment Failure', 'Major', '2024-04-10 07:30:00+00', '2024-04-10 12:00:00+00', 'Extrusion machine temperature control failure', 'Brian Lee', 'brian.lee@factory.com', '+1-555-0119', 'Extrusion Department'),
  ('b0c1d2e3-f4a5-4b5c-7d8e-9f0a1b2c3d4e', 'EMP020', 'Environmental', 'Minor', '2024-04-15 15:00:00+00', '2024-04-15 15:30:00+00', 'Water usage exceeding normal levels', 'Karen Harris', 'karen.harris@factory.com', '+1-555-0120', 'Water Treatment Facility'),
  ('c1d2e3f4-a5b6-4c5d-8e9f-0a1b2c3d4e5f', 'EMP021', 'Safety Incident', 'Minor', '2024-04-20 12:45:00+00', '2024-04-20 13:00:00+00', 'Slip hazard from spilled coolant', 'George Clark', 'george.clark@factory.com', '+1-555-0121', 'Production Line B - Station 6'),
  ('d2e3f4a5-b6c7-4d5e-9f0a-1b2c3d4e5f6a', 'EMP022', 'Quality Issue', 'Major', '2024-04-25 08:00:00+00', '2024-04-25 10:00:00+00', 'Batch failure due to incorrect material mixture', 'Sandra Lewis', 'sandra.lewis@factory.com', '+1-555-0122', 'Mixing Department');

-- Insert linked employees for first few incidents
insert into public.linked_employees (incident_id, employee_name, employee_matricule, role, notes)
values
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'Mike Johnson', 'EMP101', 'responder', 'Maintenance technician who repaired the machine'),
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'Lisa Brown', 'EMP102', 'witness', 'Operator on duty during malfunction'),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'Tom Wilson', 'EMP201', 'victim', 'Worker exposed to fumes, received medical attention'),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'Anna Davis', 'EMP202', 'responder', 'Safety officer who coordinated response'),
  ('c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f', 'James Miller', 'EMP301', 'responder', 'Quality inspector who identified the issue'),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'Maria Garcia', 'EMP401', 'responder', 'Environmental coordinator who managed cleanup');

-- Insert risks for first few incidents
insert into public.risks (incident_id, level, description)
values
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'high', 'Production delays affecting customer orders'),
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'medium', 'Potential damage to other equipment if not addressed'),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'critical', 'Worker health and safety - respiratory exposure'),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'high', 'Regulatory compliance violation'),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'medium', 'Potential for similar incidents in other areas'),
  ('c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f', 'medium', 'Customer satisfaction impact from defective products'),
  ('c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f', 'low', 'Material waste from rejected batch'),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'high', 'Environmental contamination'),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'medium', 'Cleanup costs and disposal requirements');

-- Insert corrective measures for first few incidents
insert into public.corrective_measures (incident_id, name, description, responsible_person, cost)
values
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'Machine Repair', 'Replace faulty hydraulic pump and test all systems', 'Mike Johnson (Maintenance)', 3500.00),
  ('a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d', 'Preventive Maintenance Schedule', 'Implement weekly inspection protocol for all injection molding machines', 'Tom Anderson (Maintenance Manager)', 1200.00),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'Ventilation System Upgrade', 'Install backup ventilation system and improve air monitoring', 'Anna Davis (Safety Officer)', 15000.00),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'Safety Training', 'Conduct emergency response training for all chemical area workers', 'Sarah Johnson (Training Coordinator)', 2500.00),
  ('b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e', 'PPE Enhancement', 'Provide upgraded respiratory protection equipment', 'Anna Davis (Safety Officer)', 4200.00),
  ('c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f', 'Cooling System Calibration', 'Recalibrate cooling parameters and add monitoring sensors', 'James Miller (Quality Manager)', 1800.00),
  ('c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f', 'Process Documentation Update', 'Revise cooling procedures and operator guidelines', 'Michael Chen (Process Engineer)', 500.00),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'Spill Cleanup', 'Professional cleanup and disposal of spilled materials', 'Maria Garcia (Environmental Coordinator)', 8500.00),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'Containment System Installation', 'Install spill containment barriers in loading dock area', 'David Wilson (Facilities Manager)', 6200.00),
  ('d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a', 'Loading Procedures Review', 'Update material handling procedures and train staff', 'Emily Rodriguez (Operations Supervisor)', 1500.00);
