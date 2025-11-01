"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, Calendar, MapPin, User, Shield, Wrench, DollarSign, Briefcase, Clock } from "lucide-react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"
import { CorrectiveMeasure, Incident, LinkedEmployee, Risk } from "@/lib/data/incidents-data"
import { getTypeColor } from "@/lib/utils"

interface IncidentDetailProps {
    incident: Incident
    linkedEmployees: LinkedEmployee[]
    risks: Risk[]
    correctiveMeasures: CorrectiveMeasure[]
}

export function IncidentDetail({ incident, linkedEmployees, risks, correctiveMeasures }: IncidentDetailProps) {
    const router = useRouter()

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

    const totalCost = correctiveMeasures.reduce((sum, measure) => sum + measure.cost, 0)

    return (
        <main className="min-h-screen bg-background">
            <div className="container mx-auto py-8 px-4">
                <Button variant="ghost" onClick={() => router.push("/reports")} className="mb-6">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Reports
                </Button>

                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-start justify-between mb-4">
                        <div>
                            <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">
                                Report #{incident.id}
                            </h1>
                            <Badge variant="secondary" className="bg-primary/10 text-primary">
                                {incident.classification}
                            </Badge>
                        </div>
                        <Badge variant="outline" className={`${getTypeColor(incident.type)} text-lg px-4 py-2`}>
                            {incident.type}
                        </Badge>
                    </div>
                </div>

                {/* Main Information Card */}
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
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
                                    <div className="font-medium">{format(incident.start_date, "MMMM dd, yyyy 'at' HH:mm")}</div>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <Calendar className="h-5 w-5 text-muted-foreground mt-1" />
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground mb-1">End Date</div>
                                    <div className="font-medium">
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
                                    <div className="font-semibold text-lg">{incident.reporter.name} {incident.reporter.family_name}</div>
                                    <div className="text-sm text-muted-foreground mt-1">
                                        <span className="font-medium">Matricule:</span> {incident.reporter.matricule}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <Briefcase className="h-5 w-5 text-muted-foreground mt-1" />
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground mb-1">Organizational Unit</div>
                                    <div className="font-medium">{incident.organization_unit?.name ?? "Unknown"}</div>
                                    <div className="text-sm text-muted-foreground mt-1 flex items-center gap-1">
                                        <MapPin className="h-4 w-4" /> {incident.organization_unit?.location ?? "Unknown"}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Corrective Measures — Horizontal Scroll */}
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle className="flex flex-row items-center gap-2">
                            <Wrench className="h-5 w-5" />
                            Corrective Measures
                        </CardTitle>
                    </CardHeader>

                    <CardContent>
                        {correctiveMeasures.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No corrective measures</p>
                        ) : (
                            <div className="relative">
                                <div className="flex gap-4 overflow-x-auto pb-4">
                                    {correctiveMeasures.map((measure) => (
                                        <div
                                            key={measure.id}
                                            className="min-w-[280px] max-w-xs flex-shrink-0 p-4 rounded-lg border bg-card shadow-sm"
                                        >
                                            <div className="font-semibold text-foreground mb-2">{measure.name}</div>
                                            <p className="text-sm text-foreground leading-relaxed mb-3">{measure.description}</p>
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                                <Clock className="h-4 w-4" />
                                                <span>Due: {format(measure.implementation_date, "MMMM dd, yyyy")}</span>
                                            </div>
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                                                <Briefcase className="h-4 w-4" />
                                                <span>Unit: {measure.organization_unit.name}</span>
                                            </div>
                                            <Separator className="my-3" />
                                            <div className="flex items-center justify-between text-sm">
                                                <div>
                                                    <span className="text-muted-foreground">Owner: </span>
                                                    <span className="font-medium">{measure.owner.name} {measure.owner.family_name}</span>
                                                </div>
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

                                {/* Total fixed below */}
                                <div className="border-t pt-4 mt-2 flex items-center justify-between bg-background/60 backdrop-blur-sm rounded-b-lg p-3">
                                    <span className="font-semibold text-foreground">Total Cost</span>
                                    <span className="text-xl font-bold text-primary flex items-center gap-1">
                    <DollarSign className="h-5 w-5" />
                                        {totalCost.toLocaleString("en-US", {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2,
                                        })}
                  </span>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Below: Linked Employees + Risks */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                                        <div key={index} className="p-4 rounded-lg border bg-card">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="font-semibold text-foreground">
                                                    {employee.linked_person.name} {employee.linked_person.family_name}
                                                </div>
                                                <Badge variant="outline" className={getRoleColor(employee.involvement_type)}>
                                                    {employee.involvement_type.charAt(0).toUpperCase() + employee.involvement_type.slice(1)}
                                                </Badge>

                                            </div>
                                            <div className="text-sm text-muted-foreground mb-2">{employee.linked_person.matricule}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Risk Assessment */}
                    <Card className="flex flex-col">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="h-5 w-5" />
                                Risk Assessment
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 overflow-y-auto">
                            {risks.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No risks identified</p>
                            ) : (
                                <div className="space-y-4">
                                    {risks.map((risk) => (
                                        <div key={risk.id} className="p-4 rounded-lg border bg-card">
                                            <Badge className={`${getRiskGravityColor(risk.gravity)} mb-3`}>
                                                {risk.gravity.toUpperCase()}
                                            </Badge>
                                            <p className="text-sm text-foreground leading-relaxed mb-2">{risk.name}</p>
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
                </div>
            </div>
        </main>
    )
}
