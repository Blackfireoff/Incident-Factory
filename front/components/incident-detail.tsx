"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, Calendar, MapPin, User, AlertTriangle, Shield, Wrench, DollarSign } from "lucide-react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"

interface Incident {
  id: string
  employee_matricule: string
  type: string
  classification: string
  start_date: string
  end_date: string | null
  description: string
  reporter_name: string
  reporter_email: string | null
  reporter_phone: string | null
  location: string
  created_at: string
}

interface LinkedEmployee {
  id: string
  employee_name: string
  employee_matricule: string
  role: string
  notes: string | null
}

interface Risk {
  id: string
  level: string
  description: string
}

interface CorrectiveMeasure {
  id: string
  name: string
  description: string
  responsible_person: string
  cost: number
}

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

  const getRiskLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
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

  const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
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

  const totalCost = correctiveMeasures.reduce((sum, measure) => sum + Number(measure.cost), 0)

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
                Report #{incident.id.slice(0, 8)}
              </h1>
              <p className="text-muted-foreground text-sm">Full ID: {incident.id}</p>
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
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="text-sm font-medium text-muted-foreground mb-1">Type</div>
                <div className="text-lg font-semibold">{incident.type}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground mb-1">Classification</div>
                <Badge variant="outline" className={getClassificationColor(incident.classification)}>
                  {incident.classification}
                </Badge>
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-muted-foreground mt-1" />
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Start Date</div>
                  <div className="font-medium">{format(new Date(incident.start_date), "MMMM dd, yyyy 'at' HH:mm")}</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-muted-foreground mt-1" />
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">End Date</div>
                  <div className="font-medium">
                    {incident.end_date ? format(new Date(incident.end_date), "MMMM dd, yyyy 'at' HH:mm") : "Ongoing"}
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Description</div>
              <p className="text-foreground leading-relaxed">{incident.description}</p>
            </div>

            <Separator />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex items-start gap-3">
                <User className="h-5 w-5 text-muted-foreground mt-1" />
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Reported By</div>
                  <div className="font-semibold text-lg">{incident.reporter_name}</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    <span className="font-medium">Matricule:</span> {incident.employee_matricule}
                  </div>
                  {incident.reporter_email && (
                    <div className="text-sm text-muted-foreground mt-1">
                      <span className="font-medium">Email:</span> {incident.reporter_email}
                    </div>
                  )}
                  {incident.reporter_phone && (
                    <div className="text-sm text-muted-foreground mt-1">
                      <span className="font-medium">Phone:</span> {incident.reporter_phone}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-start gap-3">
                <MapPin className="h-5 w-5 text-muted-foreground mt-1" />
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Location</div>
                  <div className="font-medium">{incident.location}</div>
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
                  {linkedEmployees.map((employee) => (
                    <div key={employee.id} className="p-4 rounded-lg border bg-card">
                      <div className="flex items-start justify-between mb-2">
                        <div className="font-semibold text-foreground">{employee.employee_name}</div>
                        <Badge variant="outline" className={getRoleColor(employee.role)}>
                          {employee.role}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mb-2">{employee.employee_matricule}</div>
                      {employee.notes && <p className="text-sm text-foreground leading-relaxed">{employee.notes}</p>}
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
                      <Badge className={`${getRiskLevelColor(risk.level)} mb-3`}>{risk.level.toUpperCase()}</Badge>
                      <p className="text-sm text-foreground leading-relaxed">{risk.description}</p>
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
                        <div className="flex items-center justify-between text-sm">
                          <div>
                            <span className="text-muted-foreground">Responsible: </span>
                            <span className="font-medium">{measure.responsible_person}</span>
                          </div>
                        </div>
                        <div className="mt-2 flex items-center gap-1 text-sm font-semibold text-primary">
                          <DollarSign className="h-4 w-4" />
                          {Number(measure.cost).toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
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
