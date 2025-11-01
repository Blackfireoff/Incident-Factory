import { notFound } from "next/navigation"
import { IncidentDetail } from "@/components/incident-detail"
// On importe SEULEMENT 'incidents', car tout est dedans
import { incidents } from "@/lib/data/incidents-data"

interface PageProps {
    // Les 'params' ne sont pas une Promise, Next.js les résout pour vous
    params: { id: string }
}

// La page n'a plus besoin d'être 'async' car les données sont locales
export default function IncidentPage({ params }: PageProps) {

    // 1. Convertir l'ID de l'URL (string) en nombre (number)
    const incidentId = parseInt(params.id, 10)

    // 2. Trouver l'incident en comparant les nombres
    const incident = incidents.find((i) => i.id === incidentId)

    // Si l'ID n'est pas un nombre ou si l'incident n'est pas trouvé
    if (isNaN(incidentId) || !incident) {
        notFound()
    }

    // 3. Extraire les données directement depuis l'objet 'incident'
    // Plus besoin de filter() !
    const incidentLinkedEmployees = incident.linked_employees
    const incidentCorrectiveMeasures = incident.corrective_measures

    // On peut toujours trier les risques, comme avant
    const incidentRisks = incident.risks.sort((a, b) => {
        const order = { critical: 0, high: 1, medium: 2, low: 3 }
        // J'ai corrigé 'level' en 'gravity' pour coller à votre interface
        return order[a.gravity as keyof typeof order] - order[b.gravity as keyof typeof order]
    })

    // 4. Passer les données au composant de détail
    return (
        <IncidentDetail
            incident={incident}
            linkedEmployees={incidentLinkedEmployees}
            risks={incidentRisks}
            correctiveMeasures={incidentCorrectiveMeasures}
        />
    )
}