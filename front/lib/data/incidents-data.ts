export interface Incident {
    id: number
    type: TypeEvent | null
    classification: ClassificationEvent | null
    start_datetime: Date | null
    end_datetime: Date | null
    description: string | null
    person : Person | null
    employees: LinkedEmployee[] | null
    corrective_measures: CorrectiveMeasure[] | null
    organizational_unit: OrganizationalUnit | null
    risks: Risk[] | null
}

export enum TypeEvent {
    EHS = "EHS",
    ENVIRONMENT = "ENVIRONMENT",
    DAMAGE = "DAMAGE"
}

export enum ClassificationEvent {
    INJURY = "INJURY",
    FIRST_AID = "FIRST_AID",
    NEAR_MISS = "NEAR_MISS",
    LOST_TIME = "LOST_TIME",
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE",
    PREVENTIVE_DECLARATION = "PREVENTIVE_DECLARATION",
    PROPERTY_DAMAGE = "PROPERTY_DAMAGE",
    CHEMICAL_SPILL = "CHEMICAL_SPILL",
    ENVIRONMENTAL_INCIDENT = "ENVIRONMENTAL_INCIDENT",
    FIRE_ALARM = "FIRE_ALARM",
    FIRE = "FIRE",
    GRAVITY_OR_FALL = "GRAVITY_OR_FALL",
    DEATH = "DEATH"
}


export interface OrganizationalUnit {
    id:number
    identifier:string
    name:string
    location:string

}

export interface Risk {
    id: number
    name: string
    gravity: string
    probability: string|null
}

export interface Person{
    id: number
    matricule: string
    name:string
    family_name:string
    role:string | null

}

export interface LinkedEmployee {
  linked_person: Person
  involvement_type: string
}

export interface CorrectiveMeasure {
    id: number
    name: string
    description: string
    implementation: Date
    owner: Person
    organization_unit: OrganizationalUnit
    cost: number

}

