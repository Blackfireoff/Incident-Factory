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
import {getTypeColor} from "@/lib/utils";

interface IncidentsTableProps {
    totalCount: number
}

const ITEMS_PER_PAGE = 20

// L'interface Filters reste la même, la logique d'application changera
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
                    // Corrigé: Recherche dans l'objet reporter
                    i.reporter.matricule.toLowerCase().includes(term) ||
                    i.reporter.name.toLowerCase().includes(term) ||
                    i.reporter.family_name.toLowerCase().includes(term) ||
                    i.type.toLowerCase().includes(term) ||
                    i.classification.toLowerCase().includes(term) ||
                    i.description.toLowerCase().includes(term),
            )
        }

        // Apply filters
        if (filters.eventId) {
            // Corrigé: i.id est un nombre, on le convertit en string pour 'includes'
            filtered = filtered.filter((i) => i.id.toString().includes(filters.eventId))
        }
        if (filters.employeeMatricule) {
            // Corrigé: Filtre sur le matricule du reporter
            filtered = filtered.filter((i) =>
                i.reporter.matricule.toLowerCase().includes(filters.employeeMatricule.toLowerCase()),
            )
        }
        if (filters.type) {
            filtered = filtered.filter((i) => i.type === filters.type)
        }
        if (filters.classification) {
            filtered = filtered.filter((i) => i.classification === filters.classification)
        }
        // Corrigé: i.start_date est déjà un objet Date, pas besoin de 'new Date()'
        if (filters.startDate) {
            filtered = filtered.filter((i) => i.start_date >= filters.startDate!)
        }
        if (filters.endDate) {
            filtered = filtered.filter((i) => i.start_date <= filters.endDate!)
        }
        if (filters.startMonth) {
            filtered = filtered.filter((i) => i.start_date >= filters.startMonth!)
        }
        if (filters.endMonth) {
            const endOfMonth = new Date(filters.endMonth)
            endOfMonth.setMonth(endOfMonth.getMonth() + 1)
            endOfMonth.setDate(0)
            filtered = filtered.filter((i) => i.start_date <= endOfMonth)
        }
        if (filters.startYear) {
            // Corrigé: i.start_date.getFullYear()
            filtered = filtered.filter((i) => i.start_date.getFullYear() >= Number.parseInt(filters.startYear))
        }
        if (filters.endYear) {
            // Corrigé: i.start_date.getFullYear()
            filtered = filtered.filter((i) => i.start_date.getFullYear() <= Number.parseInt(filters.endYear))
        }

        // Sort by date descending
        // Corrigé: .start_date est déjà un objet Date
        filtered.sort((a, b) => b.start_date.getTime() - a.start_date.getTime())

        setTotalCount(filtered.length)

        // Paginate
        const start = (currentPage - 1) * ITEMS_PER_PAGE
        const end = start + ITEMS_PER_PAGE
        setIncidents(filtered.slice(start, end))

        setLoading(false)
    }

    const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE)


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
                                        <TableHead>Reporter</TableHead> {/* Libellé changé pour 'Reporter' */}
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
                                            {/* Corrigé: .id est un nombre, .slice() est supprimé */}
                                            <TableCell className="text-xs">{incident.id}</TableCell>

                                            {/* Corrigé: Affiche le nom et le matricule du reporter */}
                                            <TableCell>
                                                <div className="font-medium">{incident.reporter.name} {incident.reporter.family_name}</div>
                                                <div className="text-xs text-muted-foreground">{incident.reporter.matricule}</div>
                                            </TableCell>

                                            <TableCell><Badge variant="outline" className={getTypeColor(incident.type)}>
                                                {incident.type}
                                            </Badge></TableCell>
                                            <TableCell>
                                                <Badge variant="secondary" className="bg-primary/10 text-primary">
                                                    {incident.classification}
                                                </Badge>
                                            </TableCell>

                                            {/* Corrigé: 'start_date' est déjà une Date */}
                                            <TableCell>{format(incident.start_date, "MMM dd, yyyy HH:mm")}</TableCell>

                                            {/* Corrigé: 'end_date' est déjà une Date */}
                                            <TableCell>
                                                {incident.end_date ? format(incident.end_date, "MMM dd, yyyy HH:mm") : "—"}
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
                                    disabled={currentPage === totalPages || totalPages === 0} // Ajout de totalPages === 0
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