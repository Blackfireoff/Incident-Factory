import { createClient } from "@/lib/supabase/server"
import { notFound } from "next/navigation"
import { IncidentDetail } from "@/components/incident-detail"

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function IncidentPage({ params }: PageProps) {
  const { id } = await params
  const supabase = await createClient()

  // Fetch incident with all related data
  const { data: incident, error: incidentError } = await supabase.from("incidents").select("*").eq("id", id).single()

  if (incidentError || !incident) {
    notFound()
  }

  // Fetch linked employees
  const { data: linkedEmployees } = await supabase
    .from("linked_employees")
    .select("*")
    .eq("incident_id", id)
    .order("created_at", { ascending: true })

  // Fetch risks
  const { data: risks } = await supabase
    .from("risks")
    .select("*")
    .eq("incident_id", id)
    .order("level", { ascending: true })

  // Fetch corrective measures
  const { data: correctiveMeasures } = await supabase
    .from("corrective_measures")
    .select("*")
    .eq("incident_id", id)
    .order("created_at", { ascending: true })

  return (
    <IncidentDetail
      incident={incident}
      linkedEmployees={linkedEmployees || []}
      risks={risks || []}
      correctiveMeasures={correctiveMeasures || []}
    />
  )
}
