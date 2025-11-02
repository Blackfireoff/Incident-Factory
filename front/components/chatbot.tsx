"use client"

import { useState } from "react"
import { MessageCircle, X, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
type ChatMode = "query" | "graphic" | "summary"

export function Chatbot() {
    const [isOpen, setIsOpen] = useState(false)
    const [messages, setMessages] = useState<{ role: "user" | "bot"; content: string }[]>([
        { role: "bot", content: "Hello! I'm here to help you with incident reporting. How can I assist you today?" },
    ])
    const [input, setInput] = useState("")
    const [mode, setMode] = useState<ChatMode>("query")
    const [isLoading, setIsLoading] = useState(false)

    const handleSend = async () => {
        if (!input.trim() || isLoading) return

        const userMessage = input.trim()
        setMessages((prev) => [...prev, { role: "user", content: userMessage }])
        setInput("")

        if (mode !== "query") {
            const upcomingFeatureMessage =
                mode === "graphic"
                    ? "La génération de graphiques sera disponible prochainement."
                    : "La synthèse automatique sera disponible prochainement."
            setMessages((prev) => [...prev, { role: "bot", content: upcomingFeatureMessage }])
            return
        }

        setIsLoading(true)
        try {
            const response = await fetch(`${API_BASE_URL}/ai/query`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    accept: "application/json",
                },
                body: JSON.stringify({ query: userMessage }),
            })

            let answerText = "Je n'ai pas pu obtenir de réponse pour le moment."
            let payload: unknown

            try {
                payload = await response.json()
            } catch (parseError) {
                console.error("Failed to parse chatbot response:", parseError)
            }

            const body = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : null

            if (body && typeof body.response === "string") {
                answerText = body.response
            } else if (!response.ok && body && typeof body.message === "string") {
                answerText = `Erreur API: ${body.message}`
            } else if (!response.ok) {
                answerText = `Erreur API: statut ${response.status}`
            }

            setMessages((prev) => [...prev, { role: "bot", content: answerText }])
        } catch (error) {
            console.error("Error calling chatbot API:", error)
            setMessages((prev) => [
                ...prev,
                {
                    role: "bot",
                    content: "Une erreur est survenue lors de la communication avec l'API. Veuillez réessayer.",
                },
            ])
        } finally {
            setIsLoading(false)
        }
    }

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
                    "fixed bottom-6 right-6 w-96 shadow-2xl transition-all z-50 !p-0", // 🔥 supprime le padding global du Card
                    "overflow-hidden rounded-lg gap-0",
                    isOpen ? "scale-100 opacity-100" : "scale-0 opacity-0",
                )}
            >
                {/* Header sans aucun espace en haut */}
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
                    <div className="mb-3 flex items-center justify-between gap-3 text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">Type de requête</span>
                        <Select value={mode} onValueChange={(value) => setMode(value as ChatMode)}>
                            <SelectTrigger className="w-40">
                                <SelectValue placeholder="Choisissez un mode" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="query">Query</SelectItem>
                                <SelectItem value="graphic">Graphic</SelectItem>
                                <SelectItem value="summary">Summary</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="h-80 overflow-y-auto mb-4 space-y-3">
                        {messages.map((message, index) => (
                            <div key={index} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                                <div
                                    className={cn(
                                        "max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-line",
                                        message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                                    )}
                                >
                                    {message.content}
                                </div>
                            </div>
                        ))}
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
                    </div>

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
                </CardContent>
            </Card>
        </>
    )
}
