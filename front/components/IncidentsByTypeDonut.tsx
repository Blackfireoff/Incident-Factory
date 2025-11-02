"use client"

import { TypeEvent } from "@/lib/data/incidents-data"
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts"

const COLORS: Record<TypeEvent, string> = {
  EHS: "#a84b00",
  DAMAGE: "#9f0712",
  ENVIRONMENT: "#016630",
}

export interface DonutDatum {
  name: TypeEvent
  value: number
}

export default function IncidentsByTypeDonut({ data }: { data: DonutDatum[] }) {
  // data doit contenir exactement 3 items: EHS, DAMAGE, ENVIRONNEMENTAL
  const chartData = data.map(d => ({ ...d, color: COLORS[d.name] }))

  return (
    <div className="h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            innerRadius="60%"
            outerRadius="85%"
            strokeWidth={2}
            paddingAngle={2}
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
          <Legend verticalAlign="bottom" align="center" iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
