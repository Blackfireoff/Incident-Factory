"use client"

import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Search, ChevronLeft, ChevronRight, Filter } from "lucide-react"
import { useRouter } from "next/navigation"
import { format } from "date-fns"
import { AdvancedFilters } from "@/components/advanced-filters"
import { ClassificationEvent, TypeEvent, type Incident } from "@/lib/data/incidents-data"
import { getTypeColor } from "@/lib/utils"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

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

interface ApiReporter {
    id: number
    matricule: string | null
    name: string | null
    family_name: string | null
    role: string | null
}

interface ApiEvent {
    id: number
    type: string | null
    classification: string | null
    start_date: string | null
    end_date: string | null
    description: string | null
    reporter: ApiReporter | null
}

export function IncidentsTable() {
    const [incidents, setIncidents] = useState<Incident[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [totalAvailable, setTotalAvailable] = useState(0)
    const [searchTerm, setSearchTerm] = useState("")
    const [currentPage, setCurrentPage] = useState(1)
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
        let ignore = false
        const controller = new AbortController()

        async function fetchAllIncidents() {
            setLoading(true)
            setError(null)

            try {
                const aggregated: Incident[] = []
                let offset = 0
                let hasMore = true
                const maxIterations = 50
                let iteration = 0
                let totalCountFromApi: number | null = null

                while (hasMore && !ignore) {
                    const response = await fetch(`${API_BASE_URL}/get_events?offset=${offset}`, {
                        headers: { accept: "application/json" },
                        cache: "no-store",
                        signal: controller.signal,
                    })

                    if (!response.ok) {
                        const message = await response.text()
                        throw new Error(`Failed to fetch incidents (status ${response.status}): ${message}`)
                    }

                    const data = (await response.json()) as {
                        events?: ApiEvent[]
                        count?: number
                        total_count?: number
                    }

                    if (typeof data.total_count === "number") {
                        totalCountFromApi = data.total_count
                    }

                    const events = Array.isArray(data.events) ? data.events : []
                    aggregated.push(
                        ...events.map<Incident>((event) => {
                            const asType = (value: string | null): TypeEvent | null => {
                                if (!value) return null
                                return (Object.values(TypeEvent) as string[]).includes(value)
                                    ? (value as TypeEvent)
                                    : null
                            }

                            const asClassification = (value: string | null): ClassificationEvent | null => {
                                if (!value) return null
                                return (Object.values(ClassificationEvent) as string[]).includes(value)
                                    ? (value as ClassificationEvent)
                                    : null
                            }

                            return {
                                id: event.id,
                                type: asType(event.type),
                                classification: asClassification(event.classification),
                                start_datetime: event.start_date ? new Date(event.start_date) : null,
                                end_date: event.end_date ? new Date(event.end_date) : null,
                                description: event.description ?? null,
                                person: event.reporter
                                    ? {
                                        id: event.reporter.id,
                                        matricule: event.reporter.matricule ?? "",
                                        name: event.reporter.name ?? "",
                                        family_name: event.reporter.family_name ?? "",
                                        role: event.reporter.role ?? null,
                                    }
                                    : null,
                                employees: null,
                                corrective_measures: null,
                                organizational_unit: null,
                                risks: null,
                            }
                        }),
                    )

                    iteration += 1
                    if (!data.count || data.count < ITEMS_PER_PAGE || iteration >= maxIterations) {
                        hasMore = false
                    } else {
                        offset += ITEMS_PER_PAGE
                    }
                }

                if (!ignore) {
                    setIncidents(aggregated)
                    setTotalAvailable(totalCountFromApi ?? aggregated.length)
                }
            } catch (fetchError) {
                if (!ignore) {
                    console.error("Error fetching incidents:", fetchError)
                    setError("Une erreur est survenue lors de la récupération des incidents.")
                    setIncidents([])
                }
            } finally {
                if (!ignore) {
                    setLoading(false)
                }
            }
        }

        void fetchAllIncidents()

        return () => {
            ignore = true
            controller.abort()
        }
    }, [])

    const filteredIncidents = useMemo(() => {
        let dataset = incidents

        if (searchTerm) {
            const term = searchTerm.toLowerCase()
            dataset = dataset.filter((incident) => {
                const person = incident.person
                const matchesReporter =
                    person &&
                    [
                        person.matricule,
                        person.name,
                        person.family_name,
                    ]
                        .filter(Boolean)
                        .some((value) => value!.toLowerCase().includes(term))

                const matchesType = incident.type?.toLowerCase().includes(term) ?? false
                const matchesClassification = incident.classification?.toLowerCase().includes(term) ?? false
                const matchesDescription = incident.description?.toLowerCase().includes(term) ?? false

                return matchesReporter || matchesType || matchesClassification || matchesDescription
            })
        }

        // Placeholder for future filter logic
        return dataset
    }, [incidents, searchTerm, filters])

    const filteredCount = filteredIncidents.length
    const hasSearch = searchTerm.trim().length > 0
    const hasAdvancedFilters = Object.entries(filters).some(([key, value]) => {
        if (
            key === "startDate" ||
            key === "endDate" ||
            key === "startMonth" ||
            key === "endMonth"
        ) {
            return value instanceof Date
        }
        return typeof value === "string" ? value.trim().length > 0 : false
    })
    const baseTotalCount = totalAvailable || filteredCount
    const totalCount = hasSearch || hasAdvancedFilters ? filteredCount : baseTotalCount
    const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE) || 1
    const paginatedIncidents = useMemo(() => {
        const start = (currentPage - 1) * ITEMS_PER_PAGE
        return filteredIncidents.slice(start, start + ITEMS_PER_PAGE)
    }, [filteredIncidents, currentPage])
    const rangeStart = totalCount === 0 ? 0 : (currentPage - 1) * ITEMS_PER_PAGE + 1
    const rangeEndBase = hasSearch || hasAdvancedFilters ? filteredCount : totalCount
    const rangeEnd = totalCount === 0 ? 0 : Math.min(currentPage * ITEMS_PER_PAGE, rangeEndBase)

    useEffect(() => {
        if (currentPage > totalPages) {
            setCurrentPage(Math.max(1, totalPages))
        }
    }, [currentPage, totalPages])

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
                    <div className="flex flex-col gap-2 md:flex-row md:items-center">
                        <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
                            <Filter className="h-4 w-4 mr-2" />
                            {showFilters ? "Hide Filters" : "Show Filters"}
                        </Button>
                        <div className="relative w-full md:ml-auto md:max-w-sm">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                value={searchTerm}
                                onChange={(event) => handleSearch(event.target.value)}
                                placeholder="Search by reporter, type, classification or description"
                                className="pl-9"
                                aria-label="Search incidents"
                            />
                        </div>
                    </div>

                    {showFilters && <AdvancedFilters filters={filters} onFilterChange={handleFilterChange} />}
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="text-muted-foreground">Loading incidents...</div>
                    </div>
                ) : error ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="text-muted-foreground">{error}</div>
                    </div>
                ) : filteredCount === 0 ? (
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
                                    {paginatedIncidents.map((incident) => (
                                        <TableRow
                                            key={incident.id}
                                            className="cursor-pointer hover:bg-accent/50 transition-colors"
                                            onClick={() => router.push(`/incident/${incident.id}`)}
                                        >
                                            {/* Corrigé: .id est un nombre, .slice() est supprimé */}
                                            <TableCell className="text-xs">{incident.id}</TableCell>

                                            {/* Corrigé: Affiche le nom et le matricule du reporter */}
                                            <TableCell>
                                                <div className="font-medium">{incident.person?.name} {incident.person?.family_name}</div>
                                                <div className="text-xs text-muted-foreground">{incident.person?.matricule}</div>
                                            </TableCell>

                                            <TableCell>
                                                {incident.type &&
                                                <Badge variant="outline" className={getTypeColor(incident.type)}>
                                                    {incident.type}
                                                </Badge>}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="secondary" className="bg-primary/10 text-primary">
                                                    {incident.classification}
                                                </Badge>
                                            </TableCell>

                                            {/* Corrigé: 'start_date' est déjà une Date */}
                                            {incident.start_datetime && <TableCell>{format(incident.start_datetime, "MMM dd, yyyy HH:mm")}</TableCell>}

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
                                {filteredCount === 0 ? (
                                    "Showing 0 incidents"
                                ) : (
                                    <>
                                        Showing {rangeStart} to {rangeEnd} of {totalCount} incidents
                                    </>
                                )}
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
