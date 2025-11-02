import { IncidentsTable } from "@/components/incidents-table"

export default function ReportsPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">Incident Reports</h1>
          <p className="text-muted-foreground text-lg">View and manage all incident reports</p>
        </div>
        <IncidentsTable />
      </div>
    </main>
  )
}
