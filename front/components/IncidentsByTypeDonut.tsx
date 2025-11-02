"use client"

import { TypeEvent } from "@/lib/data/incidents-data"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts"

const COLORS: Record<TypeEvent, string> = {
    EHS: "#a84b00",
    DAMAGE: "#9f0712",
    ENVIRONMENT: "#016630",
}

export interface DonutDatum {
    name: TypeEvent
    value: number
}

const RADIAN = Math.PI / 180
const renderCustomizedLabel = ({
                                   cx,
                                   cy,
                                   midAngle,
                                   outerRadius,
                                   percent,
                                   name,
                               }: {
    cx: number;
    cy: number;
    midAngle: number;
    outerRadius: number;
    percent: number;
    name: TypeEvent;
}) => {
    // Le rayon de décalage est maintenu à 30px pour que les étiquettes aient de l'air
    const radius = outerRadius + 30
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)
    const textAnchor = x > cx ? "start" : "end"

    return (
        <text
            x={x}
            y={y}
            fill="currentColor"
            textAnchor={textAnchor}
            dominantBaseline="central"
            className="text-sm font-medium"
        >
            {`${name} (${(percent * 100).toFixed(0)}%)`}
        </text>
    )
}

export default function IncidentsByTypeDonut({ data }: { data: DonutDatum[] }) {
    const chartData = data.map(d => ({ ...d, color: COLORS[d.name] }))

    return (
        <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={chartData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius="50%"
                        // --- MODIFICATION ICI : Réduire le rayon extérieur à 75% ---
                        outerRadius="60%"
                        // --- FIN DE LA MODIFICATION ---
                        strokeWidth={2}
                        paddingAngle={2}
                        labelLine={true}
                        label={renderCustomizedLabel}
                    >
                        {chartData.map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value: number, _name, { payload }: any) => [
                            `${value} incident${value > 1 ? "s" : ""}`,
                            payload.name,
                        ]}
                    />
                </PieChart>
            </ResponsiveContainer>
        </div>
    )
}