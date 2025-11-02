"use client"

import { useState } from "react"
import { MessageCircle, X, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"

// --- IMPORTS POUR LES GRAPHIQUES ---
import {
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
// --- CHATMODE MIS À JOUR ---
type ChatMode = "query" | "graphic" | "report"

// --- INTERFACES (INCHANGÉES) ---
interface ChartAnalysis {
    chart_type: "bar" | "pie" | "line" | "list"
    title: string
    insight: string
}
interface ChartData {
    columns: string[]
    rows: Record<string, any>[]
}
interface ChartResponse {
    analysis: ChartAnalysis
    data: ChartData
}
type MessageContent = string | { type: "chart"; payload: ChartResponse }

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#FF0000"]

export function Chatbot() {
    const [isOpen, setIsOpen] = useState(false)
    const [messages, setMessages] = useState<{ role: "user" | "bot"; content: MessageContent }[]>([
        { role: "bot", content: "Bonjour! Je suis prêt à analyser vos données. Posez-moi une question." },
    ])
    const [input, setInput] = useState("")
    const [mode, setMode] = useState<ChatMode>("query")
    const [isLoading, setIsLoading] = useState(false)

    // --- HANDLESEND MIS À JOUR ---
    const handleSend = async () => {
        if (!input.trim() || isLoading) return

        const userMessage = input.trim()
        setMessages((prev) => [...prev, { role: "user", content: userMessage }])
        setInput("")
        setIsLoading(true)

        try {
            if (mode === "query") {
                await handleQueryMode(userMessage)
            } else if (mode === "graphic") {
                await handleGraphicMode(userMessage)
            } else if (mode === "report") {
                await handleReportMode(userMessage) // <-- Nouvelle fonction
            } else {
                setMessages((prev) => [...prev, { role: "bot", content: "Mode non reconnu." }])
            }
        } catch (error) {
            console.error("Error in handleSend:", error)
            setMessages((prev) => [
                ...prev,
                { role: "bot", content: "Une erreur de communication est survenue. Veuillez réessayer." },
            ])
        } finally {
            setIsLoading(false)
        }
    }

    const handleQueryMode = async (userMessage: string) => {
        setIsLoading(true)
        try {
            const response = await fetch(`${API_BASE_URL}/ai/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json", accept: "application/json" },
                body: JSON.stringify({ query: userMessage }),
            })
            const body = (await response.json()) as Record<string, unknown>
            let answerText = "Je n'ai pas pu obtenir de réponse."

            if (body && typeof body.response === "string") {
                answerText = body.response
            } else if (!response.ok) {
                answerText = `Erreur API: statut ${response.status}`
            }
            setMessages((prev) => [...prev, { role: "bot", content: answerText }])
        } catch (error) {
            console.error("Error calling /ai/query:", error)
            throw error 
        } finally {
            setIsLoading(false) 
        }
    }

    const handleGraphicMode = async (userMessage: string) => {
        setIsLoading(true)
        try {
            const response = await fetch(`${API_BASE_URL}/ai/chart`, {
                method: "POST",
                headers: { "Content-Type": "application/json", accept: "application/json" },
                body: JSON.stringify({ query: userMessage }),
            })
            
            if (!response.ok) {
                setMessages((prev) => [...prev, { role: "bot", content: `Erreur API: statut ${response.status}` }])
                return
            }

            const body = (await response.json()) as { analysis: ChartAnalysis; data: ChartData; type: string, query: string }

            if (body.type === "chart" && body.analysis && body.data) {
                setMessages((prev) => [
                    ...prev,
                    { role: "bot", content: { type: "chart", payload: { analysis: body.analysis, data: body.data } } },
                ])
            } else if (body.type === "error" && body.analysis?.insight) {
                setMessages((prev) => [...prev, { role: "bot", content: `Erreur de graphique : ${body.analysis.insight}` }])
            } else {
                setMessages((prev) => [...prev, { role: "bot", content: "La réponse du graphique était dans un format inattendu." }])
            }
        } catch (error) {
            console.error("Error calling /ai/chart:", error)
            throw error 
        } finally {
            setIsLoading(false) 
        }
    }
    
    // --- NOUVELLE FONCTION POUR GÉRER LE TÉLÉCHARGEMENT DE PDF ---
    const handleReportMode = async (userMessage: string) => {
        try {
            const response = await fetch(`${API_BASE_URL}/ai/report`, {
                method: "POST",
                headers: { "Content-Type": "application/json", accept: "application/pdf" },
                body: JSON.stringify({ query: userMessage }),
            })

            if (!response.ok) {
                // Essayer de lire l'erreur JSON
                try {
                     const err = await response.json();
                     setMessages((prev) => [...prev, { role: "bot", content: `Erreur de rapport: ${err.detail}` }])
                } catch (e) {
                     setMessages((prev) => [...prev, { role: "bot", content: `Erreur de rapport: statut ${response.status}` }])
                }
                return;
            }

            // Gérer le téléchargement du fichier
            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement("a")
            a.href = url
            a.download = "incident_report.pdf"
            document.body.appendChild(a)
            a.click()
            
            // Nettoyage
            a.remove()
            window.URL.revokeObjectURL(url)

            setMessages((prev) => [...prev, { role: "bot", content: "Votre rapport 'incident_report.pdf' est prêt et le téléchargement a commencé." }])

        } catch (error) {
            console.error("Error calling /ai/report:", error)
            throw error
        } finally {
            setIsLoading(false)
        }
    }
    // --- FIN DE LA NOUVELLE FONCTION ---

    return (
        <>
            <Button
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    "fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg transition-all z-50",
                    isOpen && "scale-0",
                )}
                size="icon"
            >
                <MessageCircle className="h-6 w-6" />
            </Button>

            <Card
                className={cn(
                    "fixed bottom-6 right-6 w-[450px] shadow-2xl transition-all z-50 !p-0", // Largeur augmentée
                    "overflow-hidden rounded-lg gap-0",
                    isOpen ? "scale-100 opacity-100" : "scale-0 opacity-0",
                )}
            >
                {/* Header inchangé */}
                <CardHeader className="p-0 gap-0">
                    <div className="flex flex-row items-center justify-between px-4 py-3 bg-primary text-primary-foreground m-0">
                        <CardTitle className="text-lg font-semibold">Support Assistant</CardTitle>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setIsOpen(false)}
                            className="h-8 w-8 text-primary-foreground hover:bg-primary-foreground/20"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </CardHeader>

                <CardContent className="p-4">
                    {/* Selecteur de mode MIS À JOUR */}
                    <div className="mb-3 flex items-center justify-between gap-3 text-sm text-muted-foreground">
                         <span className="font-medium text-foreground">Type de requête</span>
                        <Select value={mode} onValueChange={(value) => setMode(value as ChatMode)}>
                            <SelectTrigger className="w-40">
                                <SelectValue placeholder="Choisissez un mode" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="query">Query</SelectItem>
                                <SelectItem value="graphic">Graphic</SelectItem>
                                <SelectItem value="report">Report</SelectItem> {/* <-- NOUVELLE OPTION */}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Logique de rendu (inchangée, gère déjà les nouveaux messages texte) */}
                    <div className="h-80 overflow-y-auto mb-4 space-y-3">
                        {messages.map((message, index) => (
                            <div key={index} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                                <div
                                    className={cn(
                                        "max-w-[95%] rounded-lg px-4 py-2 text-sm", 
                                        message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                                    )}
                                >
                                    {typeof message.content === "string" ? (
                                        <div className="whitespace-pre-line">{message.content}</div>
                                    ) : (
                                        <BotChartMessage 
                                            analysis={message.content.payload.analysis} 
                                            data={message.content.payload.data}
                                        />
                                    )}
                                </div>
                            </div>
                        ))}
                        
                        {/* --- CORRECTION : Indicateur de chargement restauré --- */}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="max-w-[80%] rounded-lg px-4 py-2 text-sm bg-muted text-foreground">
                                    <div className="flex items-center gap-2 py-1">
                                        <span className="typing-dot" />
                                        <span className="typing-dot" />
                                        <span className="typing-dot" />
                                    </div>
                                </div>
                            </div>
                        )}
                        {/* --- FIN DE LA CORRECTION --- */}
                    </div>

                    {/* --- CORRECTION : Barre de saisie et bouton restaurés --- */}
                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault()
                                    void handleSend()
                                }
                            }}
                            placeholder="Type your message..."
                            className="flex-1"
                            disabled={isLoading}
                        />
                        <Button onClick={() => void handleSend()} size="icon" disabled={isLoading}>
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                    {/* --- FIN DE LA CORRECTION --- */}
                    
                </CardContent>
            </Card>
        </>
    )
}

// --- COMPOSANT DE RENDU GRAPHIQUE (INCHANGÉ) ---
function BotChartMessage({ analysis, data }: { analysis: ChartAnalysis; data: ChartData }) {
    
    const valueFormatter = (value: any) => (typeof value === 'number' ? value.toLocaleString("fr") : value);

    const indexKey = (data.columns && data.columns.length > 0) ? data.columns[0] : "index";
    const categoryKeys = (data.columns && data.columns.length > 1) ? data.columns.slice(1) : [];
    
    const chartType = (analysis.chart_type === 'list' || !data.rows || data.rows.length === 0) 
        ? "list" 
        : analysis.chart_type;

    const renderChart = () => {
        const chartHeight = 250

        switch (chartType) { 
            case "bar":
                return (
                    <ResponsiveContainer width="100%" height={chartHeight}>
                        <BarChart data={data.rows} margin={{ top: 5, right: 0, left: -20, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis 
                                dataKey={indexKey} 
                                angle={-10} 
                                textAnchor="end" 
                                height={60} 
                                interval={0} 
                                fontSize={10} 
                                tick={{ fill: 'hsl(var(--foreground))' }} 
                            />
                            <YAxis fontSize={10} tick={{ fill: 'hsl(var(--foreground))' }} />
                            <Tooltip formatter={valueFormatter} wrapperClassName="text-xs !bg-popover !border-border" />
                            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                            {categoryKeys.map((category, i) => ( 
                                <Bar key={category} dataKey={category} name={category} fill={COLORS[i % COLORS.length]} />
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                )
            
            case "pie":
                return (
                    <ResponsiveContainer width="100%" height={chartHeight}>
                        <PieChart>
                            <Pie
                                data={data.rows}
                                dataKey={categoryKeys[0]} 
                                nameKey={indexKey} 
                                cx="50%"
                                cy="50%"
                                innerRadius="50%"
                                outerRadius="70%"
                                paddingAngle={2}
                            >
                                {data.rows.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip formatter={valueFormatter} wrapperClassName="text-xs !bg-popover !border-border" />
                            <Legend wrapperStyle={{ fontSize: "12px" }} />
                        </PieChart>
                    </ResponsiveContainer>
                )
            
            case "line":
                 return (
                    <ResponsiveContainer width="100%" height={chartHeight}>
                        <LineChart data={data.rows} margin={{ top: 5, right: 10, left: -20, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis 
                                dataKey={indexKey} 
                                fontSize={10} 
                                tick={{ fill: 'hsl(var(--foreground))' }} 
                                angle={-10} 
                                textAnchor="end" 
                                height={60}
                            />
                            <YAxis fontSize={10} tick={{ fill: 'hsl(var(--foreground))' }} />
                            <Tooltip formatter={valueFormatter} wrapperClassName="text-xs !bg-popover !border-border" />
                            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                            {categoryKeys.map((category, i) => ( 
                                <Line key={category} type="monotone" dataKey={category} name={category} stroke={COLORS[i % COLORS.length]} />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                )
            
            default: // "list"
                return null;
        }
    }

    return (
        <div className="p-1 w-full text-foreground"> 
            <h4 className="font-semibold">{analysis.title || "Résultats"}</h4>
            <p className="text-xs text-muted-foreground mb-2">{analysis.insight || "Voici les données extraites."}</p>
            {renderChart()}
        </div>
    )
}

// --- STYLES (INCHANGÉS) ---
const style = document.createElement('style');
style.innerHTML = `
    .typing-dot {
        width: 6px;
        height: 6px;
        background-color: hsl(var(--muted-foreground));
        border-radius: 50%;
        display: inline-block;
        animation: typing 1s infinite;
    }
    .typing-dot:nth-child(2) {
        animation-delay: 0.15s;
    }
    .typing-dot:nth-child(3) {
        animation-delay: 0.3s;
    }
    @keyframes typing {
        0%, 80%, 100% {
            transform: scale(0);
        }
        40% {
            transform: scale(1.0);
        }
    }
    .bg-background-inset {
        background-color: #f1f5f9; /* Valeur par défaut pour light mode */
    }
    .text-foreground-inset {
        color: #020817; /* Valeur par défaut pour light mode */
    }
    html.dark .bg-background-inset {
        background-color: #020817; /* Mode dark */
    }
    html.dark .text-foreground-inset {
        color: #f8fafc; /* Mode dark */
    }
    .recharts-cartesian-axis-tick-value {
        fill: hsl(var(--foreground)) !important;
    }
`;
if (!document.getElementById('chatbot-styles')) {
    style.id = 'chatbot-styles';
    document.head.appendChild(style);
}
