"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, Calendar, MapPin, User, AlertTriangle, Shield, Wrench, DollarSign, Briefcase, Clock, FileText } from "lucide-react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"
// Importez vos types
import { CorrectiveMeasure, Incident, LinkedEmployee, Risk, Person, OrganizationalUnit } from "@/lib/data/incidents-data"

// Définissez l'interface pour les props du composant
interface IncidentDetailProps {
    incident: Incident
    linkedEmployees: LinkedEmployee[]
    risks: Risk[]
    correctiveMeasures: CorrectiveMeasure[]
}

export function IncidentDetail({ incident, linkedEmployees, risks, correctiveMeasures }: IncidentDetailProps) {
    const router = useRouter()

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

    // Corrigé: renommé en 'getRiskGravityColor' et utilise 'gravity'
    const getRiskGravityColor = (gravity: string) => {
        switch (gravity.toLowerCase()) {
            case "critical":
                return "bg-red-500 text-white"
            case "high":
                return "bg-orange-500 text-white"
            case "medium":
                return "bg-yellow-500 text-white"
            case "low":
                return "bg-green-500 text-white"
            default:
                return "bg-gray-500 text-white"
        }
    }

    // Corrigé: le paramètre est 'involvement_type'
    const getRoleColor = (involvement_type: string) => {
        switch (involvement_type.toLowerCase()) {
            case "victim":
                return "bg-red-100 text-red-800 border-red-300"
            case "responder":
                return "bg-blue-100 text-blue-800 border-blue-300"
            case "witness":
                return "bg-purple-100 text-purple-800 border-purple-300"
            default:
                return "bg-gray-100 text-gray-800 border-gray-300"
        }
    }

    // Corrigé: 'measure.cost' est déjà un nombre
    const totalCost = correctiveMeasures.reduce((sum, measure) => sum + measure.cost, 0)

    return (
        <main className="min-h-screen bg-background">
            <div className="container mx-auto py-8 px-4 max-w-7xl">
                <Button variant="ghost" onClick={() => router.push("/reports")} className="mb-6">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Reports
                </Button>

                {/* Header Section */}
                <div className="mb-8">
                    <div className="flex items-start justify-between mb-4">
                        <div>
                            <h1 className="text-4xl font-bold text-foreground mb-2 text-balance font-mono">
                                {/* Corrigé: 'id' est un nombre, .slice() supprimé */}
                                Report #{incident.id}
                            </h1>
                            <p className="text-muted-foreground text-sm">Type: {incident.type}</p>
                        </div>
                        <Badge variant="outline" className={`${getClassificationColor(incident.classification)} text-lg px-4 py-2`}>
                            {incident.classification}
                        </Badge>
                    </div>
                </div>

                {/* Main Information Card */}
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5" />
                            Incident Information
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">

                        <div>
                            <div className="text-sm font-medium text-muted-foreground mb-2">Description</div>
                            <p className="text-foreground leading-relaxed">{incident.description}</p>
                        </div>

                        <Separator />

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="flex items-start gap-3">
                                <Calendar className="h-5 w-5 text-muted-foreground mt-1" />
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground mb-1">Start Date</div>
                                    {/* Corrigé: 'start_date' est déjà un objet Date */}
                                    <div className="font-medium">{format(incident.start_date, "MMMM dd, yyyy 'at' HH:mm")}</div>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <Calendar className="h-5 w-5 text-muted-foreground mt-1" />
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground mb-1">End Date</div>
                                    <div className="font-medium">
                                        {/* Corrigé: 'end_date' est déjà un objet Date */}
                                        {incident.end_date ? format(incident.end_date, "MMMM dd, yyyy 'at' HH:mm") : "Ongoing"}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <Separator />

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="flex items-start gap-3">
                                <User className="h-5 w-5 text-muted-foreground mt-1" />
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground mb-1">Reported By</div>
                                    {/* Corrigé: Utilisation de l'objet 'reporter' (Person) */}
                                    <div className="font-semibold text-lg">{incident.reporter.name} {incident.reporter.family_name}</div>
                                    <div className="text-sm text-muted-foreground mt-1">
                                        <span className="font-medium">Matricule:</span> {incident.reporter.matricule}
                                    </div>
                                    {incident.reporter.role && (
                                        <div className="text-sm text-muted-foreground mt-1">
                                            <span className="font-medium">Role:</span> {incident.reporter.role}
                                        </div>
                                    )}
                                    {/* Les champs email et phone n'existent pas sur 'Person' */}
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <Briefcase className="h-5 w-5 text-muted-foreground mt-1" />
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground mb-1">Organizational Unit</div>
                                    {/* Corrigé: Utilisation de 'organization_unit' */}
                                    <div className="font-medium">{incident.organization_unit?.name ?? "Unknown"}</div>
                                    <div className="text-sm text-muted-foreground mt-1 flex items-center gap-1">
                                        <MapPin className="h-4 w-4" /> {incident.organization_unit?.location ?? "Unknown"}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Three Column Layout for Additional Information */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Linked Employees */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <User className="h-5 w-5" />
                                Linked Employees
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {linkedEmployees.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No linked employees</p>
                            ) : (
                                <div className="space-y-4">
                                    {linkedEmployees.map((employee, index) => (
                                        // Utiliser un index ou un id unique si disponible
                                        <div key={index} className="p-4 rounded-lg border bg-card">
                                            <div className="flex items-start justify-between mb-2">
                                                {/* Corrigé: 'linked_person' (Person) */}
                                                <div className="font-semibold text-foreground">{employee.linked_person.name} {employee.linked_person.family_name}</div>
                                                {/* Corrigé: 'involvement_type' */}
                                                <Badge variant="outline" className={getRoleColor(employee.involvement_type)}>
                                                    {employee.involvement_type}
                                                </Badge>
                                            </div>
                                            {/* Corrigé: 'linked_person.matricule' */}
                                            <div className="text-sm text-muted-foreground mb-2">{employee.linked_person.matricule}</div>
                                            {/* Le champ 'notes' n'existe pas sur 'LinkedEmployee' */}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Risks */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="h-5 w-5" />
                                Risk Assessment
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {risks.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No risks identified</p>
                            ) : (
                                <div className="space-y-4">
                                    {risks.map((risk) => (
                                        <div key={risk.id} className="p-4 rounded-lg border bg-card">
                                            {/* Corrigé: 'gravity' et 'getRiskGravityColor' */}
                                            <Badge className={`${getRiskGravityColor(risk.gravity)} mb-3`}>{risk.gravity.toUpperCase()}</Badge>
                                            {/* Corrigé: 'risk.name' au lieu de 'description' */}
                                            <p className="text-sm text-foreground leading-relaxed mb-2">{risk.name}</p>
                                            {/* Ajouté: 'probability' */}
                                            {risk.probability && (
                                                <div className="text-xs text-muted-foreground font-medium">
                                                    Probability: <span className="font-semibold text-foreground">{risk.probability}</span>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Corrective Measures */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Wrench className="h-5 w-5" />
                                Corrective Measures
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {correctiveMeasures.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No corrective measures</p>
                            ) : (
                                <>
                                    <div className="space-y-4 mb-6">
                                        {correctiveMeasures.map((measure) => (
                                            <div key={measure.id} className="p-4 rounded-lg border bg-card">
                                                <div className="font-semibold text-foreground mb-2">{measure.name}</div>
                                                <p className="text-sm text-foreground leading-relaxed mb-3">{measure.description}</p>

                                                {/* Ajouté: 'implementation_date' */}
                                                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                                    <Clock className="h-4 w-4" />
                                                    <span>Due: {format(measure.implementation_date, "MMMM dd, yyyy")}</span>
                                                </div>

                                                {/* Ajouté: 'organization_unit' */}
                                                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                                                    <Briefcase className="h-4 w-4" />
                                                    <span>Unit: {measure.organization_unit.name}</span>
                                                </div>

                                                <Separator className="my-3" />

                                                <div className="flex items-center justify-between text-sm">
                                                    <div>
                                                        <span className="text-muted-foreground">Owner: </span>
                                                        {/* Corrigé: 'owner' (Person) */}
                                                        <span className="font-medium">{measure.owner.name} {measure.owner.family_name}</span>
                                                    </div>
                                                    {/* Corrigé: 'cost' est déjà un nombre */}
                                                    <div className="flex items-center gap-1 text-sm font-semibold text-primary">
                                                        <DollarSign className="h-4 w-4" />
                                                        {measure.cost.toLocaleString("en-US", {
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 2,
                                                        })}
                                                    </div>
                                                </div>

                                            </div>
                                        ))}
                                    </div>
                                    <Separator className="mb-4" />
                                    <div className="flex items-center justify-between p-4 rounded-lg bg-primary/10 border border-primary/20">
                                        <span className="font-semibold text-foreground">Total Cost</span>
                                        <span className="text-xl font-bold text-primary flex items-center gap-1">
                      <DollarSign className="h-5 w-5" />
                                            {totalCost.toLocaleString("en-US", {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                    </span>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </main>
    )
}