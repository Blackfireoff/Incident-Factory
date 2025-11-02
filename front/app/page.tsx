import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, FileText, AlertCircle, DollarSign, PieChart, Donut } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
// Corrigé: On importe 'incidents' et les types (pas les listes de données)
import { incidents, type Risk, type CorrectiveMeasure, TypeEvent, Incident, OrganizationalUnit, ClassificationEvent } from "@/lib/data/incidents-data"
import { getTypeColor } from "@/lib/utils"
import IncidentsByTypeDonut, { DonutDatum } from "@/components/IncidentsByTypeDonut"

export interface BasicInformation {
    total_event_count: number,
    total_critical_risk_count: number,
    total_no_corrective_measure_count: number,
    total_corrective_measure_cost: number
}

export interface MostRecentIncidents {
    incidents: Incident[]
}

export interface TopOrganizationCount {
    top_organization: [
        organization: OrganizationalUnit,
        value: number
    ]
}

export interface IncidentByType {
    incidents: [
        type: TypeEvent,
        value: number
    ]
}

export interface IncidentByClassification {
    incidents: [
        type: ClassificationEvent,
        value: number
    ]
}

export default function Dashboard() {
    const totalIncidents = incidents.length

    // Corrigé: On filtre les incidents qui ont au moins un risque critique
    const criticalIncidentsCount = incidents.filter(
        (i) => i.risks?.some((r) => r.gravity.toLowerCase() === "critical")
    ).length

    // Corrigé: On filtre les incidents qui n'ont aucune mesure corrective
    const incidentsWithoutMeasures = incidents.filter(
        (i) => i.corrective_measures?.length === 0
    ).length

    // Corrigé: On "aplatit" toutes les mesures de tous les incidents, PUIS on somme les coûts
    const totalCost = incidents
        .flatMap((i) => i.corrective_measures ?? []) // Gère si le tableau 'corrective_measures' est null
        .reduce((sum, m) => sum + (m.cost ?? 0), 0) // Gère si 'm.cost' est null ou undefined

    // Corrigé: 'start_date' est déjà un objet Date, pas besoin de 'new Date()'
    const recentIncidents = [...incidents]
        .sort((a, b) => b.start_date.getTime() - a.start_date.getTime())
        .slice(0, 5)

    const typeCounts = incidents.reduce(
        (acc, incident) => {
            acc[incident.type] = (acc[incident.type] || 0) + 1
            return acc
        },
        {} as Record<TypeEvent, number>,
    )

    const sectorCounts = incidents.reduce(
        (acc, incident) => {
            const unit = incident.organization_unit
            const key = unit?.identifier ?? "Unknown"

            if (!acc[key]) {
                acc[key] = {
                    key,
                    label: unit?.name ?? unit?.identifier ?? "Unknown sector",
                    location: unit?.location ?? "Location unknown",
                    count: 0,
                }
            }

            acc[key].count += 1

            if (unit?.location) {
                if (acc[key].location === "Location unknown") {
                    acc[key].location = unit.location
                } else if (acc[key].location !== unit.location) {
                    acc[key].location = "Multiple locations"
                }
            }

            return acc
        },
        {} as Record<
            string,
            {
                key: string
                label: string
                location: string
                count: number
            }
        >,
    )

    const sectorsByOrganization = Object.values(sectorCounts)

    const classificationCounts = incidents.reduce(
        (acc, incident) => {
            const key = incident.classification || "Unclassified"
            acc[key] = (acc[key] || 0) + 1
            return acc
        },
        {} as Record<string, number>,
    )

    const classifications = Object.entries(classificationCounts).sort((a, b) => b[1] - a[1])
    const topClassifications = classifications.slice(0, 5)

    const typeData: DonutDatum[] = (Object.values(TypeEvent) as TypeEvent[]).map(type => ({
        name: type,
        value: typeCounts[type] ?? 0,
    }))


    return (
        <main className="min-h-screen bg-background">
            <div className="container mx-auto py-8 px-4">
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">Dashboard</h1>
                    <p className="text-muted-foreground text-lg">Overview of incident reports and key metrics</p>
                </div>

                {/* Key Metrics */}
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
                    <Card className="gap-4">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Total Incidents</CardTitle>
                            <FileText className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-primary">{totalIncidents}</div>
                            <p className="text-xs text-muted-foreground mt-1">All time reports</p>
                        </CardContent>
                    </Card>

                    <Card className="gap-4">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Critical Risks</CardTitle>
                            <AlertCircle className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            {/* Corrigé: Utilisation de la nouvelle variable */}
                            <div className="text-3xl font-bold text-red-600">{criticalIncidentsCount}</div>
                            <p className="text-xs text-muted-foreground mt-1">Incidents with critical risks</p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">No Corrective Measures</CardTitle>
                            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-orange-600">{incidentsWithoutMeasures}</div>
                            <p className="text-xs text-muted-foreground mt-1">Requires action plan</p>
                        </CardContent>
                    </Card>

                    <Card className="gap-4">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Total Corrective Cost</CardTitle>
                            <DollarSign className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-green-600">${totalCost.toLocaleString()}</div>
                            <p className="text-xs text-muted-foreground mt-1">Across all measures</p>
                        </CardContent>
                    </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-2 mb-8">
                    {/* Recent Incidents */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Incidents</CardTitle>
                        </CardHeader>
                            <CardContent>
                                <div className="flex flex-col gap-4">
                                    {recentIncidents.map((incident) => (
                                        <Link key={incident.id} href={`/incident/${incident.id}`}>
                                            <div className="flex items-start justify-between border-b border-border last:border-0 hover:bg-accent/50 transition-colors rounded-lg p-2 -m-2 cursor-pointer">
                                                <div className="flex flex-col flex-1 gap-1">
                                                    <p className="text-sm font-medium text-foreground">#{incident.id}</p>
                                                    <Badge variant="secondary" className="bg-primary/10 text-primary">
                                                        {incident.classification}
                                                    </Badge>
                                                </div>
                                                <div className="flex flex-col items-end gap-1">
                                                    <span className="text-sm text-muted-foreground">
                                                        {incident.start_date.toLocaleDateString()}
                                                    </span>
                                                    <Badge variant="outline" className={`${getTypeColor(incident.type)}`}>
                                                        {incident.type}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Incidents by Organization Sector</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ul className="flex flex-col gap-3">
                                    {sectorsByOrganization.map(({ key, label, location, count }) => (
                                        <li
                                            key={key}
                                            className="flex items-center justify-between rounded-lg border bg-card p-4"
                                        >
                                            <span className="text-sm font-medium text-foreground">
                                                {label}
                                                <span className="ml-2 text-xs text-muted-foreground">({location})</span>
                                            </span>
                                            <div className="flex items-center gap-3">
                                                <div className="w-24 h-2 bg-muted rounded-full overflow-hidden" aria-hidden>
                                                    <div
                                                        className="h-full bg-primary rounded-full"
                                                        style={{ width: `${(count / totalIncidents) * 100}%` }}
                                                    />
                                                </div>
                                                <span className="text-lg font-bold text-foreground">{count}</span>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>
                        </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-2 mb-8">
                    <Card className="gap-2">
                        <CardHeader>
                            <CardTitle>Incidents by Type</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <IncidentsByTypeDonut data={typeData} />
                        </CardContent>
                    </Card>

                    <Card className="gap-2">
                        <CardHeader>
                            <CardTitle>Incidents by Classification</CardTitle>
                            <p className="text-sm text-muted-foreground">
                                Top classifications by total incidents
                            </p>
                        </CardHeader>
                        <CardContent>
                            <ul className="flex flex-col gap-3">
                                {topClassifications.map(([classification, count]) => (
                                    <li
                                        key={classification}
                                        className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
                                    >
                                        <span className="font-medium text-foreground">{classification}</span>
                                        <span className="text-lg font-semibold text-primary">{count}</span>
                                    </li>
                                ))}
                            </ul>
                            {classifications.length > topClassifications.length ? (
                                <p className="mt-3 text-xs text-muted-foreground">
                                    Showing top {topClassifications.length} classifications. More data may add new entries.
                                </p>
                            ) : null}
                        </CardContent>
                    </Card>
                </div>

                
            </div>
        </main>
    )
}
