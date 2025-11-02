import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { TypeEvent } from './data/incidents-data'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getTypeColor(type: TypeEvent) {
  switch (type) {
    case TypeEvent.EHS:
        return "bg-yellow-100 text-yellow-800 border-yellow-300"
    case TypeEvent.DAMAGE:
        return "bg-red-100 text-red-800 border-red-300"
    case TypeEvent.ENVIRONMENT:
        return "bg-green-100 text-green-800 border-green-300"
    default:
        return "bg-gray-100 text-gray-800 border-gray-300"
}
}
