"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { CalendarIcon, X } from "lucide-react"
import { format } from "date-fns"
import { createClient } from "@/lib/supabase/client"

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

interface AdvancedFiltersProps {
  filters: Filters
  onFilterChange: (filters: Filters) => void
}

export function AdvancedFilters({ filters, onFilterChange }: AdvancedFiltersProps) {
  const [types, setTypes] = useState<string[]>([])
  const [classifications, setClassifications] = useState<string[]>([])

  useEffect(() => {
    fetchFilterOptions()
  }, [])

  async function fetchFilterOptions() {
    const supabase = createClient()

    const { data: incidentData } = await supabase.from("incidents").select("type, classification")

    if (incidentData) {
      const uniqueTypes = Array.from(new Set(incidentData.map((i) => i.type)))
      const uniqueClassifications = Array.from(new Set(incidentData.map((i) => i.classification)))
      setTypes(uniqueTypes)
      setClassifications(uniqueClassifications)
    }
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
          <Select value={filters.type} onValueChange={(value) => onFilterChange({ ...filters, type: value })}>
            <SelectTrigger id="type">
              <SelectValue placeholder="Select type..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=" ">All Types</SelectItem>
              {types.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
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
              <SelectItem value=" ">All Classifications</SelectItem>
              {classifications.map((classification) => (
                <SelectItem key={classification} value={classification}>
                  {classification}
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

        {/* Start Month */}
        <div className="space-y-2">
          <Label>Start Month</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-full justify-start text-left font-normal bg-transparent">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {filters.startMonth ? format(filters.startMonth, "MMMM yyyy") : "Pick a month"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0">
              <Calendar
                mode="single"
                selected={filters.startMonth}
                onSelect={(date) => onFilterChange({ ...filters, startMonth: date })}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* End Month */}
        <div className="space-y-2">
          <Label>End Month</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-full justify-start text-left font-normal bg-transparent">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {filters.endMonth ? format(filters.endMonth, "MMMM yyyy") : "Pick a month"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0">
              <Calendar
                mode="single"
                selected={filters.endMonth}
                onSelect={(date) => onFilterChange({ ...filters, endMonth: date })}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* Start Year */}
        <div className="space-y-2">
          <Label htmlFor="startYear">Start Year</Label>
          <Select value={filters.startYear} onValueChange={(value) => onFilterChange({ ...filters, startYear: value })}>
            <SelectTrigger id="startYear">
              <SelectValue placeholder="Select year..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=" ">All Years</SelectItem>
              {years.map((year) => (
                <SelectItem key={year} value={year}>
                  {year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* End Year */}
        <div className="space-y-2">
          <Label htmlFor="endYear">End Year</Label>
          <Select value={filters.endYear} onValueChange={(value) => onFilterChange({ ...filters, endYear: value })}>
            <SelectTrigger id="endYear">
              <SelectValue placeholder="Select year..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=" ">All Years</SelectItem>
              {years.map((year) => (
                <SelectItem key={year} value={year}>
                  {year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )
}
