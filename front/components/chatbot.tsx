"use client"

import { useState } from "react"
import { MessageCircle, X, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

export function Chatbot() {
    const [isOpen, setIsOpen] = useState(false)
    const [messages, setMessages] = useState<{ role: "user" | "bot"; content: string }[]>([
        { role: "bot", content: "Hello! I'm here to help you with incident reporting. How can I assist you today?" },
    ])
    const [input, setInput] = useState("")

    const handleSend = () => {
        if (!input.trim()) return

        const userMessage = input.trim()
        setMessages((prev) => [...prev, { role: "user", content: userMessage }])
        setInput("")

        setTimeout(() => {
            let botResponse = "I'm here to help! You can ask me about:"

            if (userMessage.toLowerCase().includes("report") || userMessage.toLowerCase().includes("incident")) {
                botResponse =
                    "To create a new incident report, please navigate to the Reports page and click the 'New Report' button. You'll need to fill in details like incident type, location, and description."
            } else if (userMessage.toLowerCase().includes("dashboard")) {
                botResponse =
                    "The Dashboard shows key metrics including total incidents, open cases, critical risks, and total corrective costs. You can view trends and statistics at a glance."
            } else if (userMessage.toLowerCase().includes("filter") || userMessage.toLowerCase().includes("search")) {
                botResponse =
                    "You can filter reports by typing in the search box. It searches across incident IDs, employee matricules, types, and classifications."
            } else {
                botResponse +=
                    "\n• Creating incident reports\n• Understanding the dashboard\n• Filtering and searching reports\n• Incident classifications and risk levels"
            }

            setMessages((prev) => [...prev, { role: "bot", content: botResponse }])
        }, 500)
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
                    "overflow-hidden rounded-lg",
                    isOpen ? "scale-100 opacity-100" : "scale-0 opacity-0",
                )}
            >
                {/* Header sans aucun espace en haut */}
                <CardHeader className="p-0">
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
                    </div>

                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSend()}
                            placeholder="Type your message..."
                            className="flex-1"
                        />
                        <Button onClick={handleSend} size="icon">
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </>
    )
}
