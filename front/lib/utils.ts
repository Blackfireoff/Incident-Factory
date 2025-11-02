import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { ClassificationEvent, TypeEvent } from './data/incidents-data'

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

export function getTypeString(type: TypeEvent | null) {
  if (!type) return ""
  switch (type) {
    case TypeEvent.EHS:
        return "EHS"
    case TypeEvent.DAMAGE:
        return "Damage"
    case TypeEvent.ENVIRONMENT:
        return "Environment"
    default:
        return "Default"
  }
}

export function getClassificationString(classification: ClassificationEvent | null) {
  if (!classification) return ""
  switch (classification) {
    case ClassificationEvent.INJURY:
        return "Injury"
    case ClassificationEvent.CHEMICAL_SPILL:
        return "Chemical spill"
    case ClassificationEvent.ENVIRONMENTAL_INCIDENT:
        return "Environmental incident"
    case ClassificationEvent.FIRE:
        return "Fire"
    case ClassificationEvent.EQUIPMENT_FAILURE:
        return "Equipment failure"
    case ClassificationEvent.FIRE_ALARM:
        return "Fire alarm"
    case ClassificationEvent.FIRST_AID:
        return "First aid"
    case ClassificationEvent.LOST_TIME:
        return "Lost time"
    case ClassificationEvent.NEAR_MISS:
        return "Near miss"
    case ClassificationEvent.PREVENTIVE_DECLARATION:
      return "Preventive declaration"
      case ClassificationEvent.PROPERTY_DAMAGE:
        return "Property damage"
    default:
        return "Default"
  }
}

