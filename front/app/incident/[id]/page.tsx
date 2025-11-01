import { notFound } from "next/navigation"
import { IncidentDetail } from "@/components/incident-detail"
import { incidents, linkedEmployees, risks, correctiveMeasures } from "@/lib/data/incidents-data"

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function IncidentPage({ params }: PageProps) {
  const { id } = await params

  const incident = incidents.find((i) => i.id === id)

  if (!incident) {
    notFound()
  }

  const incidentLinkedEmployees = linkedEmployees.filter((e) => e.incident_id === id)
  const incidentRisks = risks
    .filter((r) => r.incident_id === id)
    .sort((a, b) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 }
      return order[a.level as keyof typeof order] - order[b.level as keyof typeof order]
    })
  const incidentCorrectiveMeasures = correctiveMeasures.filter((m) => m.incident_id === id)

  return (
    <IncidentDetail
      incident={incident}
      linkedEmployees={incidentLinkedEmployees}
      risks={incidentRisks}
      correctiveMeasures={incidentCorrectiveMeasures}
    />
  )
}
