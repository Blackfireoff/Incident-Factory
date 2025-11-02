import { notFound } from "next/navigation"
import { IncidentDetail } from "@/components/incident-detail"
import {
    type Incident
} from "@/lib/data/incidents-data"

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ?? process.env.API_BASE_URL ?? "http://localhost:8000"

interface PageProps {
    params: Promise<{ id: string }>
}

async function fetchIncidentDetail(incidentId: number): Promise<Incident | null> {
    try {
        const response = await fetch(`${API_BASE_URL}/${incidentId}/details`, {
            headers: { accept: "application/json" },
            cache: "no-store",
        })

        if (response.status === 404) {
            return null
        }

        if (!response.ok) {
            console.error(`Failed to fetch incident ${incidentId}:`, await response.text())
            return null
        }

        const data = (await response.json()) as { status?: string; event?: Incident }
        return data.event ?? null
    } catch (error) {
        console.error("Error fetching incident detail:", error)
        return null
    }
}

export default async function IncidentPage({ params }: PageProps) {
    const { id } = await params
    const incidentId = Number.parseInt(id, 10)

    if (Number.isNaN(incidentId)) {
        notFound()
    }

    const [incident] = await Promise.all([
        fetchIncidentDetail(incidentId),
    ])

    if (!incident) {
        notFound()
    }

    const incidentRisks = (incident?.risks ?? []).sort((a, b) => {
        const order = { critical: 0, high: 1, medium: 2, low: 3, unknown: 4 }
        const gravityA = a.gravity?.toLowerCase() ?? "unknown"
        const gravityB = b.gravity?.toLowerCase() ?? "unknown"
        return order[gravityA as keyof typeof order] - order[gravityB as keyof typeof order]
    })

    return (
        <IncidentDetail
            incident={incident}
            linkedEmployees={incident.employees??[]}
            risks={incidentRisks}
            correctiveMeasures={incident.corrective_measures??[]}
        />
    )
}
