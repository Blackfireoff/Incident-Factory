"use client"

import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Search, ChevronLeft, ChevronRight, Filter, CalendarIcon, X } from "lucide-react"
import { useRouter } from "next/navigation" // Importation problématique
import { format } from "date-fns"

import { ClassificationEvent, TypeEvent, type Incident } from "@/lib/data/incidents-data"
import { getTypeColor, getClassificationString } from "@/lib/utils"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"



const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

const ITEMS_PER_PAGE = 20

// --- Interface de Filtres ---
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

// --- Fonctions Helper (inchangées) ---
const normalizeFilters = (raw: Filters): Filters => ({
    ...raw,
    eventId: raw.eventId.trim(),
    employeeMatricule: raw.employeeMatricule.trim(),
    type: raw.type.trim(),
    classification: raw.classification.trim(),
    startYear: raw.startYear.trim(),
    endYear: raw.endYear.trim(),
})

const createInitialFilters = (): Filters => ({
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
const formatDateForApi = (value?: Date) => (value ? format(value, "yyyy-MM-dd") : undefined)


// ==================================================================
// --- COMPOSANT ADVANCEDFILTERS (Intégré) ---
// ==================================================================
interface AdvancedFiltersProps {
    filters: Filters
    onFilterChange: (filters: Filters) => void
    onApplyFilters?: () => void
    isApplying?: boolean
}

export function AdvancedFilters({ filters, onFilterChange, onApplyFilters, isApplying = false }: AdvancedFiltersProps) {
    const [types, setTypes] = useState<TypeEvent[]>([])
    const [classifications, setClassifications] = useState<ClassificationEvent[]>([])


    useEffect(() => {
        fetchFilterOptions()
    }, [])

    function fetchFilterOptions() {
        // Utilise les objets simulés
        const uniqueTypes = Object.values(TypeEvent)
        const uniqueClassifications = Object.values(ClassificationEvent)
        setTypes(uniqueTypes)
        setClassifications(uniqueClassifications)
    }

    const handleClearFilters = () => {
        onFilterChange({
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
    }

    const currentYear = new Date().getFullYear()
    const years = Array.from({ length: 10 }, (_, i) => (currentYear - i).toString())

    return (
        <div className="p-4 border rounded-lg bg-muted/50 space-y-4">
            <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm">Advanced Filters</h3>
                <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                    <X className="h-4 w-4 mr-1" />
                    Clear All
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Event ID */}
                <div className="space-y-2">
                    <Label htmlFor="eventId">Event ID</Label>
                    <Input
                        id="eventId"
                        placeholder="Enter event ID..."
                        value={filters.eventId}
                        onChange={(e) => onFilterChange({ ...filters, eventId: e.target.value })}
                    />
                </div>

                {/* Employee Matricule */}
                <div className="space-y-2">
                    <Label htmlFor="employeeMatricule">Employee Matricule</Label>
                    <Input
                        id="employeeMatricule"
                        placeholder="Enter matricule..."
                        value={filters.employeeMatricule}
                        onChange={(e) => onFilterChange({ ...filters, employeeMatricule: e.target.value })}
                    />
                </div>

                {/* Type */}
                <div className="space-y-2">
                    <Label htmlFor="type">Type</Label>
                    <Select value={ filters.type } onValueChange={(value) => onFilterChange({ ...filters, type: value })}>
                        <SelectTrigger id="type">
                            <SelectValue placeholder="Select type..." />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value=" ">All types</SelectItem>
                            {types.map((type) => (
                                <SelectItem key={type} value={type}>
                                    {getClassificationString(type)}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {/* Classification */}
                <div className="space-y-2">
                    <Label htmlFor="classification">Classification</Label>
                    <Select
                        value={filters.classification}
                        onValueChange={(value) => onFilterChange({ ...filters, classification: value })}
                    >
                        <SelectTrigger id="classification">
                            <SelectValue placeholder="Select classification..." />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value=" ">All classifications</SelectItem>
                            {classifications.map((classification) => (
                                <SelectItem key={classification} value={classification}>
                                    {getClassificationString(classification)}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {/* Start Date */}
                <div className="space-y-2">
                    <Label>Start Date</Label>
                    <Popover>
                        <PopoverTrigger asChild>
                            <Button variant="outline" className="w-full justify-start text-left font-normal bg-transparent">
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                {filters.startDate ? format(filters.startDate, "PPP") : "Pick a date"}
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0">
                            <Calendar
                                mode="single"
                                selected={filters.startDate}
                                onSelect={(date) => onFilterChange({ ...filters, startDate: date })}
                                initialFocus
                            />
                        </PopoverContent>
                    </Popover>
                </div>

                {/* End Date */}
                <div className="space-y-2">
                    <Label>End Date</Label>
                    <Popover>
                        <PopoverTrigger asChild>
                            <Button variant="outline" className="w-full justify-start text-left font-normal bg-transparent">
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                {filters.endDate ? format(filters.endDate, "PPP") : "Pick a date"}
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0">
                            <Calendar
                                mode="single"
                                selected={filters.endDate}
                                onSelect={(date) => onFilterChange({ ...filters, endDate: date })}
                                initialFocus
                            />
                        </PopoverContent>
                    </Popover>
                </div>

            </div>

            {onApplyFilters && (
                <div className="flex justify-end">
                    <Button type="button" onClick={onApplyFilters} disabled={isApplying}>
                        Filtrer
                    </Button>
                </div>
            )}
        </div>
    )
}


// ==================================================================
// --- COMPOSANT INCIDENTSTABLE (Mis à jour) ---
// ==================================================================
export function IncidentsTable() {
    const [incidents, setIncidents] = useState<Incident[]>([]) // Ne contiendra que la page actuelle
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [totalAvailable, setTotalAvailable] = useState(0) // Total des éléments (venant de l'API)
    // SUPPRIMÉ: searchTerm
    const [currentPage, setCurrentPage] = useState(1)

    // ****** MODIFICATION ICI ******
    // Les filtres sont maintenant visibles par défaut
    const [showFilters, setShowFilters] = useState(true)
    // ****** FIN DE LA MODIFICATION ******

    const [filters, setFilters] = useState<Filters>(() => createInitialFilters())
    const [appliedFilters, setAppliedFilters] = useState<Filters>(() => createInitialFilters())
    const router = useRouter()

    // SUPPRIMÉ: debouncedSearchTerm

    useEffect(() => {
        let ignore = false
        const controller = new AbortController()

        // RENOMMÉ: N'obtient que la page actuelle
        const fetchIncidentsPage = async () => {
            setLoading(true)
            setError(null)

            try {
                // MODIFIÉ: L'offset est calculé basé sur la page actuelle
                const offset = (currentPage - 1) * ITEMS_PER_PAGE

                const buildQueryParams = (offsetValue: number) => {
                    const params = new URLSearchParams()
                    params.set("offset", offsetValue.toString())
                    params.set("limit", ITEMS_PER_PAGE.toString())

                    // SUPPRIMÉ: Logique de recherche (searchTerm)

                    // Vos filtres avancés (appliedFilters) sont conservés
                    const { eventId, employeeMatricule, type, classification, startDate, endDate } = appliedFilters

                    if (eventId) {
                        const parsedEventId = Number.parseInt(eventId, 10)
                        if (!Number.isNaN(parsedEventId)) {
                            params.set("event_id", parsedEventId.toString())
                        }
                    }
                    if (employeeMatricule) {
                        params.set("employee_matricule", employeeMatricule)
                    }
                    if (type) {
                        params.set("type", type)
                    }
                    if (classification) {
                        params.set("classification", classification)
                    }
                    const formattedStart = formatDateForApi(startDate)
                    if (formattedStart) {
                        params.set("start_date", formattedStart)
                    }
                    const formattedEnd = formatDateForApi(endDate)
                    if (formattedEnd) {
                        params.set("end_date", formattedEnd)
                    }

                    return params
                }

                // MODIFIÉ: Plus de boucle 'while'. Un seul appel.
                const params = buildQueryParams(offset)
                const response = await fetch(`${API_BASE_URL}/get_events?${params.toString()}`, {
                    headers: { accept: "application/json" },
                    cache: "no-store",
                    signal: controller.signal,
                })

                if (!response.ok) {
                    const message = await response.text()
                    throw new Error(`Failed to fetch incidents (status ${response.status}): ${message}`)
                }

                const data = (await response.json()) as {
                    events?: Incident[]
                    count?: number
                    total_count?: number
                }

                const events = Array.isArray(data.events) ? data.events : []

                // +++ CONSOLE LOGS (ÉTAPE 1) +++
                console.log("--- ÉTAPE 1: RÉPONSE API ---");
                console.log(`Nombre d'événements reçus: ${events.length}`);
                if (events.length > 0) {
                    console.log("events[0] brut de l'API:", events[0]);
                    console.log("events[0].person brut de l'API:", events[0].person);
                }
                // +++ FIN DES LOGS +++

                // La logique de transformation est correcte et conservée
                const transformedIncidents = events.map<Incident>((event) => {

                    // +++ CONSOLE LOGS (ÉTAPE 2) +++
                    console.log(`--- ÉTAPE 2: TRANSFORMATION (ID: ${event.id}) ---`);
                    console.log("event.person reçu par le .map():", event.person);
                    // +++ FIN DES LOGS +++

                    const asType = (value: string | null): TypeEvent | null => { return event.type ?? null }
                    const asClassification = (value: string | null): ClassificationEvent | null => { return event.classification ?? null }

                    const newPersonObject = event.person
                        ? {
                            id: event.person?.id,
                            matricule: event.person.matricule ?? "",
                            name: event.person.name ?? "",
                            family_name: event.person.family_name ?? "",
                            role: event.person.role ?? null,
                        }
                        : null;

                    // +++ CONSOLE LOGS (ÉTAPE 3) +++
                    console.log(`Nouvel objet 'person' créé (ID: ${event.id}):`, newPersonObject);
                    // +++ FIN DES LOGS +++

                    return {
                        id: event.id,
                        type: asType(event.type),
                        classification: asClassification(event.classification),
                        start_datetime: event.start_datetime ? new Date(event.start_datetime) : null,
                        end_datetime: event.end_datetime ? new Date(event.end_datetime) : null,
                        description: event.description ?? null,
                        person: newPersonObject, // Utilise l'objet tracé
                        employees: null,
                        corrective_measures: null,
                        organizational_unit: null,
                        risks: null,
                    }
                })

                // +++ CONSOLE LOGS (ÉTAPE 4) +++
                console.log("--- ÉTAPE 4: APRÈS TRANSFORMATION ---");
                if (transformedIncidents.length > 0) {
                    console.log("Premier incident transformé (complet):", transformedIncidents[0]);
                    console.log("person du premier incident transformé:", transformedIncidents[0].person);
                }
                // +++ FIN DES LOGS +++

                if (!ignore) {
                    // MODIFIÉ: On sauvegarde la page actuelle
                    setIncidents(transformedIncidents)
                    // MODIFIÉ: On sauvegarde le total de l'API
                    setTotalAvailable(data.total_count ?? 0)
                }

            } catch (fetchError) {
                if (!ignore) {
                    console.error("Error fetching incidents:", fetchError)
                    setError("Une erreur est survenue lors de la récupération des incidents.")
                    setIncidents([])
                    setTotalAvailable(0) // Réinitialiser en cas d'erreur
                }
            } finally {
                if (!ignore) {
                    setLoading(false)
                }
            }
        }

        void fetchIncidentsPage()

        return () => {
            ignore = true
            controller.abort()
        }
        // MODIFIÉ: Dépendances mises à jour
    }, [appliedFilters, currentPage]) // SUPPRIMÉ: debouncedSearchTerm

    // MODIFIÉ: Logique de comptage simplifiée
    const totalCount = totalAvailable // Le total vient de l'API
    const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE) || 1
    const rangeStart = totalCount === 0 ? 0 : (currentPage - 1) * ITEMS_PER_PAGE + 1
    const rangeEnd = totalCount === 0 ? 0 : Math.min(currentPage * ITEMS_PER_PAGE, totalCount)

    // MODIFIÉ: Logique de correction de page
    useEffect(() => {
        if (currentPage > totalPages && totalPages > 0) {
            setCurrentPage(totalPages)
        }
    }, [currentPage, totalPages])

    // SUPPRIMÉ: handleSearch

    const handleFilterChange = (newFilters: Filters) => {
        setFilters(newFilters)
        // On ne change pas de page ici, on attend 'Apply'
    }

    // MODIFIÉ: handleApplyFilters applique les filtres et réinitialise la page
    const handleApplyFilters = () => {
        setCurrentPage(1)
        setAppliedFilters(normalizeFilters(filters))
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
                        {/* SUPPRIMÉ: Barre de recherche (Input) */}
                        <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
                            <Filter className="h-4 w-4 mr-2" />
                            {showFilters ? "Hide Filters" : "Show Filters"}
                        </Button>
                    </div>

                    {showFilters && (
                        <AdvancedFilters
                            filters={filters}
                            onFilterChange={handleFilterChange}
                            onApplyFilters={handleApplyFilters}
                            isApplying={loading}
                        />
                    )}
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="text-muted-foreground">Loading incidents...</div>
                    </div>
                ) : error ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="text-muted-foreground">{error}</div>
                    </div>
                ) : totalCount === 0 ? (
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
                                        <TableHead>Reporter</TableHead>
                                        <TableHead>Type</TableHead>
                                        <TableHead>Classification</TableHead>
                                        <TableHead>Start Date</TableHead>
                                        <TableHead>End Date</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {/* MODIFIÉ: Map directement sur 'incidents' */}
                                    {incidents.map((incident) => {

                                        // +++ CONSOLE LOGS (ÉTAPE 5) +++
                                        console.log(`--- ÉTAPE 5: RENDU (ID: ${incident.id}) ---`);
                                        console.log("incident.person au moment du rendu:", incident.person);
                                        // +++ FIN DES LOGS +++

                                        return (
                                            <TableRow
                                                key={incident.id}
                                                className="cursor-pointer hover:bg-accent/50 transition-colors"
                                                onClick={() => router.push(`/incident/${incident.id}`)}
                                            >
                                                <TableCell className="text-xs">{incident.id}</TableCell>
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
                                                        {getClassificationString(incident.classification)}
                                                    </Badge>
                                                </TableCell>
                                                {incident.start_datetime && <TableCell>{format(new Date(incident.start_datetime), "MMM dd, yyyy HH:mm")}</TableCell>}
                                                <TableCell>
                                                    {incident.end_datetime ? format(new Date(incident.end_datetime), "MMM dd, yyyy HH:mm") : "—"}
                                                </TableCell>
                                            </TableRow>
                                        )
                                    })}
                                </TableBody>
                            </Table>
                        </div>

                        <div className="flex items-center justify-between mt-6">
                            <div className="text-sm text-muted-foreground">
                                {totalCount === 0 ? (
                                    "Showing 0 incidents"
                                ) : (
                                    <>
                                        {/* MODIFIÉ: Utilise les nouvelles variables de comptage */}
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
                                    disabled={currentPage === totalPages} // Simplifié
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

