import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle, AlertTriangle, DollarSign, FileText } from "lucide-react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import IncidentsByTypeDonut, { DonutDatum } from "@/components/IncidentsByTypeDonut"
import { getTypeColor, getClassificationString } from "@/lib/utils"
import { ClassificationEvent, Incident, OrganizationalUnit, Person, TypeEvent } from "@/lib/data/incidents-data"


const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ?? process.env.API_BASE_URL ?? "http://localhost:8000"

interface BasicInfoResponse {
    status?: string
    data?: {
        total_event_count: number
        total_critical_risk_count: number
        total_no_corrective_measure_count: number
        total_corrective_measure_cost: number
    }
    message?: string
}

interface MostRecentIncidentsResponse {
    incidents?: Incident[]
    status?: string
    message?: string
}

interface TopOrganizationEntry {
    organization: OrganizationalUnit
    value: number
}

interface TopOrganizationResponse {
    top_organization?: TopOrganizationEntry[]
    status?: string
    message?: string
}

interface IncidentTypeCountItem {
    type: TypeEvent
    value: number
}

interface IncidentByTypeResponse {
    incidents_by_type?: IncidentTypeCountItem[]
    status?: string
    message?: string
}

interface IncidentClassificationCountItem {
    classification: ClassificationEvent
    value: number
}

interface IncidentByClassificationResponse {
    incidents?: IncidentClassificationCountItem[]
    status?: string
    message?: string
}

interface RecentIncidentCardItem {
    id: number
    reporter: Person | null
    classification: string
    startDate: Date | null
    type: TypeEvent | null
}

interface OrganizationListItem {
    key: string
    label: string
    location: string
    count: number
}

async function fetchFromApi<T>(path: string): Promise<T | null> {
    try {
        const response = await fetch(`${API_BASE_URL}${path}`, {
            headers: { accept: "application/json" },
            cache: "no-store",
        })

        if (!response.ok) {
            console.error(`Failed to fetch ${path}: ${response.status} ${response.statusText}`)
            return null
        }

        return (await response.json()) as T
    } catch (error) {
        console.error(`Error fetching ${path}:`, error)
        return null
    }
}

function parseTypeEvent(type: string | null): TypeEvent | null {
    if (!type) return null
    return (Object.values(TypeEvent) as string[]).includes(type) ? (type as TypeEvent) : null
}

export default async function Dashboard() {
    const [basicInfoRes, recentIncidentsRes, topOrganizationRes, incidentsByTypeRes, incidentsByClassificationRes] =
        await Promise.all([
            fetchFromApi<BasicInfoResponse>("/get_basic_info"),
            fetchFromApi<MostRecentIncidentsResponse>("/get_most_recent_incidents"),
            fetchFromApi<TopOrganizationResponse>("/get_top_organization"),
            fetchFromApi<IncidentByTypeResponse>("/get_incident_by_type"),
            fetchFromApi<IncidentByClassificationResponse>("/get_incident_by_classification"),
        ])

    const basicInfo = basicInfoRes?.data
    const totalIncidents = basicInfo?.total_event_count ?? 0
    const criticalIncidentsCount = basicInfo?.total_critical_risk_count ?? 0
    const incidentsWithoutMeasures = basicInfo?.total_no_corrective_measure_count ?? 0
    const totalCost = basicInfo?.total_corrective_measure_cost ?? 0

    const recentIncidents: RecentIncidentCardItem[] = (recentIncidentsRes?.incidents ?? []).map(
        (incident) => ({
            id: incident.id,
            reporter: incident.person ?? null,
            classification: incident.classification ?? "Unclassified",
            startDate: incident.start_datetime ? new Date(incident.start_datetime) : null,
            type: parseTypeEvent(incident.type),
        }),
    )

    const sectorsByOrganization: OrganizationListItem[] = (topOrganizationRes?.top_organization ?? []).map(
        (entry) => ({
            key: entry.organization.identifier ?? entry.organization.name ?? `org-${entry.organization.id}`,
            label: entry.organization.name ?? entry.organization.identifier ?? "Unknown sector",
            location: entry.organization.location ?? "Location unknown",
            count: entry.value ?? 0,
        }),
    )

    const totalSectorCounts = sectorsByOrganization.reduce((sum, item) => sum + item.count, 0)
    const sectorPercentageBase = totalIncidents > 0 ? totalIncidents : totalSectorCounts || 1

    const typeData: DonutDatum[] =
        (incidentsByTypeRes?.incidents_by_type ?? []).map((item) => ({
            name: item.type ?? "Unknown",
            value: item.value ?? 0,
        })) || []

    const classificationEntries = (incidentsByClassificationRes?.incidents ?? []).map((item) => ({
        name: item.classification ?? "Unclassified",
        value: item.value ?? 0,
    }))
    const topClassifications = classificationEntries.slice(0, 5)

    return (
        <main className="min-h-screen bg-background">
            <div className="container mx-auto py-8 px-4">
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">Dashboard</h1>
                    <p className="text-muted-foreground text-lg">Overview of incident reports and key metrics</p>
                </div>

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
                            <div className="text-3xl font-bold text-red-600">
                                ${Number(totalCost || 0).toLocaleString()}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">Across all measures</p>
                        </CardContent>
                    </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-2 mb-8">
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Incidents</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {recentIncidents.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No recent incidents available.</p>
                            ) : (
                                <div className="flex flex-col gap-4">
                                    {recentIncidents.map((incident) => (
                                        <Link key={incident.id} href={`/incident/${incident.id}`}>
                                            <div className="flex items-start justify-between border-b border-border last:border-0 hover:bg-accent/50 transition-colors rounded-lg p-2 -m-2 cursor-pointer">
                                                <div className="flex flex-col flex-1 gap-1">
                                                    <p className="flex gap-4 text-sm font-medium text-foreground"><span className="font-bold">#{incident.id}</span> {incident.reporter?.name} {incident.reporter?.family_name}</p>
                                                    <Badge variant="secondary" className="bg-primary/10 text-primary">
                                                        {getClassificationString(incident.classification)}
                                                    </Badge>
                                                </div>
                                                <div className="flex flex-col items-end gap-1">
                                                    <span className="text-sm text-muted-foreground">
                                                        {incident.startDate
                                                            ? incident.startDate.toLocaleDateString()
                                                            : "Date unavailable"}
                                                    </span>
                                                    {incident.type && (
                                                        <Badge variant="outline" className={getTypeColor(incident.type)}>
                                                            {incident.type}
                                                        </Badge>
                                                    )}
                                                </div>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Incidents by Organization Sector</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {sectorsByOrganization.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No organization data available.</p>
                            ) : (
                                <ul className="flex flex-col gap-3">
                                    {sectorsByOrganization.map(({ key, label, location, count }) => (
                                        <li
                                            key={key}
                                            className="flex items-center justify-between rounded-lg border bg-card p-4"
                                        >
                                            <span className="text-sm font-medium text-foreground">
                                                {label}<br></br>
                                                <span className="ml-2 text-xs text-muted-foreground">({location})</span>
                                            </span>
                                            <div className="flex items-center gap-3">
                                                <div className="w-24 h-2 bg-muted rounded-full overflow-hidden" aria-hidden>
                                                    <div
                                                        className="h-full bg-primary rounded-full"
                                                        style={{
                                                            width: `${Math.min(
                                                                100,
                                                                (count / sectorPercentageBase) * 100,
                                                            ).toFixed(0)}%`,
                                                        }}
                                                    />
                                                </div>
                                                <span className="text-lg font-bold text-foreground">{count}</span>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </CardContent>
                    </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-2 mb-8">
                    <Card>
                        <CardHeader>
                            <CardTitle>Incidents by Type</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {typeData.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No incident type data available.</p>
                            ) : (
                                <IncidentsByTypeDonut data={typeData} />
                            )}
                        </CardContent>
                    </Card>

                    <Card className="gap-2">
                        <CardHeader>
                            <CardTitle>Incidents by Classification</CardTitle>
                            <p className="text-sm text-muted-foreground">Top classifications by total incidents</p>
                        </CardHeader>
                        <CardContent>
                            {topClassifications.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No classification data available.</p>
                            ) : (
                                <>
                                    <ul className="flex flex-col gap-3">
                                        {topClassifications.map(({ name, value }) => (
                                            <li
                                                key={name}
                                                className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
                                            >
                                                <span className="font-medium text-foreground">{getClassificationString(name)}</span>
                                                <span className="text-lg font-semibold text-primary">{value}</span>
                                            </li>
                                        ))}
                                    </ul>
                                    {(incidentsByClassificationRes?.incidents?.length ?? 0) > topClassifications.length ? (
                                        <p className="mt-3 text-xs text-muted-foreground">
                                            Showing top {topClassifications.length} classifications. More data may add new
                                            entries.
                                        </p>
                                    ) : null}
                                </>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </main>
    )
}
