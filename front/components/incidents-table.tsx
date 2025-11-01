"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Search, ChevronLeft, ChevronRight, Filter } from "lucide-react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"
import { AdvancedFilters } from "@/components/advanced-filters"
import { incidents as allIncidents, type Incident } from "@/lib/data/incidents-data"

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

  function fetchIncidents() {
    setLoading(true)

    let filtered = [...allIncidents]

    // Apply search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        (i) =>
          i.employee_matricule.toLowerCase().includes(term) ||
          i.type.toLowerCase().includes(term) ||
          i.classification.toLowerCase().includes(term) ||
          i.description.toLowerCase().includes(term),
      )
    }

    // Apply filters
    if (filters.eventId) {
      filtered = filtered.filter((i) => i.id.toLowerCase().includes(filters.eventId.toLowerCase()))
    }
    if (filters.employeeMatricule) {
      filtered = filtered.filter((i) =>
        i.employee_matricule.toLowerCase().includes(filters.employeeMatricule.toLowerCase()),
      )
    }
    if (filters.type) {
      filtered = filtered.filter((i) => i.type === filters.type)
    }
    if (filters.classification) {
      filtered = filtered.filter((i) => i.classification === filters.classification)
    }
    if (filters.startDate) {
      filtered = filtered.filter((i) => new Date(i.start_date) >= filters.startDate!)
    }
    if (filters.endDate) {
      filtered = filtered.filter((i) => new Date(i.start_date) <= filters.endDate!)
    }
    if (filters.startMonth) {
      filtered = filtered.filter((i) => new Date(i.start_date) >= filters.startMonth!)
    }
    if (filters.endMonth) {
      const endOfMonth = new Date(filters.endMonth)
      endOfMonth.setMonth(endOfMonth.getMonth() + 1)
      endOfMonth.setDate(0)
      filtered = filtered.filter((i) => new Date(i.start_date) <= endOfMonth)
    }
    if (filters.startYear) {
      filtered = filtered.filter((i) => new Date(i.start_date).getFullYear() >= Number.parseInt(filters.startYear))
    }
    if (filters.endYear) {
      filtered = filtered.filter((i) => new Date(i.start_date).getFullYear() <= Number.parseInt(filters.endYear))
    }

    // Sort by date descending
    filtered.sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())

    setTotalCount(filtered.length)

    // Paginate
    const start = (currentPage - 1) * ITEMS_PER_PAGE
    const end = start + ITEMS_PER_PAGE
    setIncidents(filtered.slice(start, end))

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
