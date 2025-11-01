import { notFound } from "next/navigation"
import { IncidentDetail } from "@/components/incident-detail"
import { incidents } from "@/lib/data/incidents-data"

// 1. Assurez-vous que votre interface est comme ceci (PAS de Promise)
interface PageProps {
    params: Promise<{ id: string }>
}

// 2. Assurez-vous qu'il n'y a PAS 'async' ici
export default async function IncidentPage({ params }: PageProps) {

const { id } = await params
    // 3. Cette ligne (ligne 15) fonctionnera maintenant
    const incidentId = parseInt(id, 10)

    const incident = incidents.find((i) => i.id === incidentId)

    if (isNaN(incidentId) || !incident) {
        notFound()
    }

    const incidentLinkedEmployees = incident.linked_employees ?? []
    const incidentCorrectiveMeasures = incident.corrective_measures ?? []

    const incidentRisks = (incident.risks ?? []).sort((a, b) => {
        const order = { critical: 0, high: 1, medium: 2, low: 3 }
        return order[a.gravity as keyof typeof order] - order[b.gravity as keyof typeof order]
    })

    return (
        <IncidentDetail
            incident={incident}
            linkedEmployees={incidentLinkedEmployees}
            risks={incidentRisks}
            correctiveMeasures={incidentCorrectiveMeasures}
        />
    )
}