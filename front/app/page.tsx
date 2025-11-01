import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, FileText, AlertCircle, DollarSign } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
// Corrigé: On importe 'incidents' et les types (pas les listes de données)
import { incidents, type Risk, type CorrectiveMeasure } from "@/lib/data/incidents-data"
import { getTypeColor } from "@/lib/utils"

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
        {} as Record<string, number>,
    )

    const sectorCounts = incidents.reduce(
        (acc, incident) => {
            // Corrigé: Ajout du chaînage optionnel '?' pour plus de sécurité
            const sector = incident.organization_unit?.identifier ?? "Unknown"
            acc[sector] = (acc[sector] || 0) + 1
            return acc
        },
        {} as Record<string, number>,
    )

    const getClassificationColor = (classification: string) => {
        switch (classification.toLowerCase()) {
            case "critical":
                return "bg-red-100 text-red-800 border-red-300"
            case "major":
                return "bg-orange-100 text-orange-800 border-orange-300"
            case "minor":
                return "bg-yellow-100 text-yellow-800 border-yellow-300"
            default:
                return "bg-gray-100 text-gray-800 border-gray-300"
        }
    }

    return (
        <main className="min-h-screen bg-background">
            <div className="container mx-auto py-8 px-4">
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">Dashboard</h1>
                    <p className="text-muted-foreground text-lg">Overview of incident reports and key metrics</p>
                </div>

                {/* Key Metrics */}
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Total Incidents</CardTitle>
                            <FileText className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-primary">{totalIncidents}</div>
                            <p className="text-xs text-muted-foreground mt-1">All time reports</p>
                        </CardContent>
                    </Card>

                    <Card>
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

                    <Card>
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

                    {/* Incidents by Type */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Incidents by Type</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {Object.entries(typeCounts).map(([type, count]) => (
                                    <div key={type} className="flex items-center justify-between">
                                        <span className="text-sm font-medium text-foreground">{type}</span>
                                        <div className="flex items-center gap-3">
                                            <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-primary rounded-full"
                                                    style={{ width: `${(count / totalIncidents) * 100}%` }}
                                                />
                                            </div>
                                            <span className="text-sm font-bold text-foreground w-8 text-right">{count}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>Incidents by Organization Sector</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {Object.entries(sectorCounts).map(([sector, count]) => (
                                <div key={sector} className="flex items-center justify-between p-4 rounded-lg border bg-card">
                                    <span className="text-sm font-medium text-foreground">{sector}</span>
                                    <div className="flex items-center gap-3">
                                        <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-primary rounded-full"
                                                style={{ width: `${(count / totalIncidents) * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-lg font-bold text-foreground">{count}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </main>
    )
}