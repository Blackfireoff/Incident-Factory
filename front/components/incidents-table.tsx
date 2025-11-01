"use client"

import { useState, useEffect } from "react"
import { createClient } from "@/lib/supabase/client"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Search, ChevronLeft, ChevronRight, Filter } from "lucide-react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"
import { AdvancedFilters } from "@/components/advanced-filters"

interface Incident {
  id: string
  employee_matricule: string
  type: string
  classification: string
  start_date: string
  end_date: string | null
  description: string
}

interface IncidentsTableProps {
  totalCount: number
}

const ITEMS_PER_PAGE = 20

interface Filters {
  eventId: string
  employeeMatricule: string
  type: string
  classification: string
  startDate: Date | undefined
  endDate: Date | undefined
  startMonth: Date | undefined
  endMonth: Date | undefined
  startYear: string
  endYear: string
}

export function IncidentsTable({ totalCount: initialCount }: IncidentsTableProps) {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(initialCount)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<Filters>({
    eventId: "",
    employeeMatricule: "",
    type: "",
    classification: "",
    startDate: undefined,
    endDate: undefined,
    startMonth: undefined,
    endMonth: undefined,
    startYear: "",
    endYear: "",
  })
  const router = useRouter()

  useEffect(() => {
    fetchIncidents()
  }, [currentPage, searchTerm, filters])

  async function fetchIncidents() {
    setLoading(true)
    const supabase = createClient()

    let query = supabase
      .from("incidents")
      .select("*", { count: "exact" })
      .order("start_date", { ascending: false })
      .range((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE - 1)

    if (searchTerm) {
      query = query.or(
        `employee_matricule.ilike.%${searchTerm}%,type.ilike.%${searchTerm}%,classification.ilike.%${searchTerm}%,description.ilike.%${searchTerm}%`,
      )
    }

    if (filters.eventId) {
      query = query.ilike("id", `%${filters.eventId}%`)
    }
    if (filters.employeeMatricule) {
      query = query.ilike("employee_matricule", `%${filters.employeeMatricule}%`)
    }
    if (filters.type) {
      query = query.eq("type", filters.type)
    }
    if (filters.classification) {
      query = query.eq("classification", filters.classification)
    }
    if (filters.startDate) {
      query = query.gte("start_date", filters.startDate.toISOString())
    }
    if (filters.endDate) {
      query = query.lte("start_date", filters.endDate.toISOString())
    }
    if (filters.startMonth) {
      query = query.gte("start_date", filters.startMonth.toISOString())
    }
    if (filters.endMonth) {
      const endOfMonth = new Date(filters.endMonth)
      endOfMonth.setMonth(endOfMonth.getMonth() + 1)
      endOfMonth.setDate(0)
      query = query.lte("start_date", endOfMonth.toISOString())
    }
    if (filters.startYear) {
      query = query.gte("start_date", `${filters.startYear}-01-01`)
    }
    if (filters.endYear) {
      query = query.lte("start_date", `${filters.endYear}-12-31`)
    }

    const { data, error, count } = await query

    if (error) {
      console.error("[v0] Error fetching incidents:", error)
    } else {
      setIncidents(data || [])
      setTotalCount(count || 0)
    }
    setLoading(false)
  }

  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE)

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

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setCurrentPage(1)
  }

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters)
    setCurrentPage(1)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Incident Reports</CardTitle>
        <CardDescription>View and manage all incident reports from the facility</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-6 space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by employee, type, classification, or description..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
              <Filter className="h-4 w-4 mr-2" />
              {showFilters ? "Hide Filters" : "Show Filters"}
            </Button>
          </div>

          {showFilters && <AdvancedFilters filters={filters} onFilterChange={handleFilterChange} />}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-muted-foreground">Loading incidents...</div>
          </div>
        ) : incidents.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-muted-foreground">No incidents found</div>
          </div>
        ) : (
          <>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">ID</TableHead>
                    <TableHead>Employee</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Classification</TableHead>
                    <TableHead>Start Date</TableHead>
                    <TableHead>End Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {incidents.map((incident) => (
                    <TableRow
                      key={incident.id}
                      className="cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => router.push(`/incident/${incident.id}`)}
                    >
                      <TableCell className="font-mono text-xs">{incident.id.slice(0, 8)}...</TableCell>
                      <TableCell className="font-medium">{incident.employee_matricule}</TableCell>
                      <TableCell>{incident.type}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={getClassificationColor(incident.classification)}>
                          {incident.classification}
                        </Badge>
                      </TableCell>
                      <TableCell>{format(new Date(incident.start_date), "MMM dd, yyyy HH:mm")}</TableCell>
                      <TableCell>
                        {incident.end_date ? format(new Date(incident.end_date), "MMM dd, yyyy HH:mm") : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-muted-foreground">
                Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to {Math.min(currentPage * ITEMS_PER_PAGE, totalCount)}{" "}
                of {totalCount} incidents
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                <div className="text-sm font-medium">
                  Page {currentPage} of {totalPages}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
