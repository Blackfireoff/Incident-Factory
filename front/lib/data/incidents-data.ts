export interface Incident {
    id: number
    type: TypeEvent | null
    classification: ClassificationEvent | null
    start_datetime: Date | null
    end_date: Date | null
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
    FIRE = "FIRE"
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

// --- 2. DONNÉES DE SUPPORT (POUR FACILITER LE MOCK) ---

// Unités organisationnelles de base
const unitProd: OrganizationalUnit = { id: 1, identifier: "PROD", name: "Production", location: "Bâtiment A" };
const unitSafety: OrganizationalUnit = { id: 2, identifier: "EHS", name: "Safety", location: "Bâtiment B" };
const unitQuality: OrganizationalUnit = { id: 3, identifier: "QA", name: "Quality Assurance", location: "Laboratoire" };
const unitLogistics: OrganizationalUnit = { id: 4, identifier: "LOG", name: "Logistics", location: "Entrepôt C" };
const unitMaint: OrganizationalUnit = { id: 5, identifier: "MAINT", name: "Maintenance", location: "Atelier Central" };

// Personnes récurrentes (Reporters, Employés liés, Propriétaires de mesures)
const personJohnSmith: Person = { id: 101, matricule: "EMP001", name: "John", family_name: "Smith", role: "Opérateur" };
const personSarahJohnson: Person = { id: 102, matricule: "EMP002", name: "Sarah", family_name: "Johnson", role: "Responsable EHS" };
const personMichaelChen: Person = { id: 103, matricule: "EMP003", name: "Michael", family_name: "Chen", role: "Inspecteur Qualité" };
const personEmilyRodriguez: Person = { id: 104, matricule: "EMP004", name: "Emily", family_name: "Rodriguez", role: "Superviseur Logistique" };

const personMikeJohnson: Person = { id: 105, matricule: "EMP101", name: "Mike", family_name: "Johnson", role: "Technicien Maintenance" };
const personLisaBrown: Person = { id: 106, matricule: "EMP102", name: "Lisa", family_name: "Brown", role: "Opérateur" };
const personTomWilson: Person = { id: 107, matricule: "EMP201", name: "Tom", family_name: "Wilson", role: "Chimiste" };
const personAnnaDavis: Person = { id: 108, matricule: "EMP202", name: "Anna", family_name: "Davis", role: "Coordonatrice EHS" };
const personJamesMiller: Person = { id: 109, matricule: "EMP301", name: "James", family_name: "Miller", role: "Technicien QA" };
const personMariaGarcia: Person = { id: 110, matricule: "EMP401", name: "Maria", family_name: "Garcia", role: "Coordonatrice Environnement" };
const personTomAnderson: Person = { id: 111, matricule: "MGR-MAINT", name: "Tom", family_name: "Anderson", role: "Maintenance Manager" };
const personDavidWilson: Person = { id: 112, matricule: "MGR-FAC", name: "David", family_name: "Wilson", role: "Facilities Manager" };


// --- 3. VOS DONNÉES MOCK CORRIGÉES ---

export const incidents: Incident[] = [
    // Ancien ID: a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
    {
        id: 1,
        type: TypeEvent.DAMAGE, // "Equipment Failure"
        classification: ClassificationEvent.INJURY,
        start_datetime: new Date("2024-01-15T08:30:00Z"),
        end_date: new Date("2024-01-15T12:00:00Z"),
        description: "Injection molding machine malfunction causing production halt",
        person: personJohnSmith,
        organizational_unit: { ...unitProd, location: "Production Line A - Station 3" },

        employees: [
            {
                linked_person: personMikeJohnson,
                involvement_type: "responder" // ancien "role"
            },
            {
                linked_person: personLisaBrown,
                involvement_type: "witness"
            }
        ],

        risks: [
            {
                id: 1,
                name: "Production delays affecting customer orders", // ancienne 'description'
                gravity: "high", // ancien 'level'
                probability: "Élevée"
            },
            {
                id: 2,
                name: "Potential damage to other equipment if not addressed",
                gravity: "medium",
                probability: "Moyenne"
            }
        ],

        corrective_measures: [
            {
                id: 1,
                name: "Machine Repair",
                description: "Replace faulty hydraulic pump and test all systems",
                implementation: new Date("2024-01-16T09:00:00Z"),
                owner: personMikeJohnson, // ancienne string "Mike Johnson (Maintenance)"
                organization_unit: unitMaint,
                cost: 3500.0
            },
            {
                id: 2,
                name: "Preventive Maintenance Schedule",
                description: "Implement weekly inspection protocol for all injection molding machines",
                implementation: new Date("2024-01-22T09:00:00Z"),
                owner: personTomAnderson, // ancienne string "Tom Anderson (Maintenance Manager)"
                organization_unit: unitMaint,
                cost: 1200.0
            }
        ]
    },

    // Ancien ID: b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e
    {
        id: 2,
        type: TypeEvent.EHS, // "Safety Incident"
        classification: ClassificationEvent.FIRST_AID,
        start_datetime: new Date("2024-01-20T14:15:00Z"),
        end_date: new Date("2024-01-20T14:45:00Z"),
        description: "Worker exposed to chemical fumes due to ventilation system failure",
        person: personSarahJohnson,
        organizational_unit: { ...unitSafety, location: "Chemical Storage Area B" },

        employees: [
            {
                linked_person: personTomWilson,
                involvement_type: "victim"
            },
            {
                linked_person: personAnnaDavis,
                involvement_type: "responder"
            }
        ],

        risks: [
            {
                id: 3,
                name: "Worker health and safety - respiratory exposure",
                gravity: ClassificationEvent.FIRST_AID,
                probability: "Faible"
            },
            {
                id: 4,
                name: "Regulatory compliance violation",
                gravity: "high",
                probability: "Faible"
            },
            {
                id: 5,
                name: "Potential for similar incidents in other areas",
                gravity: "medium",
                probability: "Moyenne"
            }
        ],

        corrective_measures: [
            {
                id: 3,
                name: "Ventilation System Upgrade",
                description: "Install backup ventilation system and improve air monitoring",
                implementation: new Date("2024-01-28T09:00:00Z"),
                owner: personAnnaDavis,
                organization_unit: unitMaint,
                cost: 15000.0
            },
            {
                id: 4,
                name: "Safety Training",
                description: "Conduct emergency response training for all chemical area workers",
                implementation: new Date("2024-02-01T10:00:00Z"),
                owner: personSarahJohnson, // La reporter est aussi propriétaire de la mesure
                organization_unit: unitSafety,
                cost: 2500.0
            },
            {
                id: 5,
                name: "PPE Enhancement",
                description: "Provide upgraded respiratory protection equipment",
                implementation: new Date("2024-01-25T09:00:00Z"),
                owner: personAnnaDavis,
                organization_unit: unitSafety,
                cost: 4200.0
            }
        ]
    },

    // Ancien ID: c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f
    {
        id: 3,
        type: TypeEvent.DAMAGE, // "Quality Issue"
        classification: ClassificationEvent.NEAR_MISS,
        start_datetime: new Date("2024-01-25T10:00:00Z"),
        end_date: new Date("2024-01-25T11:30:00Z"),
        description: "Batch of plastic containers failed quality inspection due to improper cooling",
        person: personMichaelChen,
        organizational_unit: { ...unitQuality, location: "Quality Control Lab" },

        employees: [
            {
                linked_person: personJamesMiller,
                involvement_type: "responder"
            }
        ],

        risks: [
            {
                id: 6,
                name: "Customer satisfaction impact from defective products",
                gravity: "medium",
                probability: "Moyenne"
            },
            {
                id: 7,
                name: "Material waste from rejected batch",
                gravity: "low",
                probability: "Élevée"
            }
        ],

        corrective_measures: [
            {
                id: 6,
                name: "Cooling System Calibration",
                description: "Recalibrate cooling parameters and add monitoring sensors",
                implementation: new Date("2024-01-26T14:00:00Z"),
                owner: personJamesMiller, // Le 'responder' est aussi 'owner'
                organization_unit: unitMaint,
                cost: 1800.0
            },
            {
                id: 7,
                name: "Process Documentation Update",
                description: "Revise cooling procedures and operator guidelines",
                implementation: new Date("2024-01-27T09:00:00Z"),
                owner: personMichaelChen, // Le 'reporter' est aussi 'owner'
                organization_unit: unitQuality,
                cost: 500.0
            }
        ]
    },

    // Ancien ID: d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a
    {
        id: 4,
        type: TypeEvent.ENVIRONMENT, // "Environmental"
        classification: ClassificationEvent.INJURY,
        start_datetime: new Date("2024-02-01T16:00:00Z"),
        end_date: new Date("2024-02-01T18:30:00Z"),
        description: "Plastic pellet spill in loading dock area",
        person: personEmilyRodriguez,
        organizational_unit: { ...unitLogistics, location: "Loading Dock 2" },

        employees: [
            {
                linked_person: personMariaGarcia,
                involvement_type: "responder"
            }
        ],

        risks: [
            {
                id: 8,
                name: "Environmental contamination",
                gravity: "high",
                probability: "Moyenne"
            },
            {
                id: 9,
                name: "Cleanup costs and disposal requirements",
                gravity: "medium",
                probability: "Élevée"
            }
        ],

        corrective_measures: [
            {
                id: 8,
                name: "Spill Cleanup",
                description: "Professional cleanup and disposal of spilled materials",
                implementation: new Date("2024-02-02T08:00:00Z"),
                owner: personMariaGarcia,
                organization_unit: unitSafety,
                cost: 8500.0
            },
            {
                id: 9,
                name: "Containment System Installation",
                description: "Install spill containment barriers in loading dock area",
                implementation: new Date("2024-02-10T09:00:00Z"),
                owner: personDavidWilson,
                organization_unit: unitMaint,
                cost: 6200.0
            },
            {
                id: 10,
                name: "Loading Procedures Review",
                description: "Update material handling procedures and train staff",
                implementation: new Date("2024-02-05T09:00:00Z"),
                owner: personEmilyRodriguez,
                organization_unit: unitLogistics,
                cost: 1500.0
            }
        ]
    },

    // J'ai arrêté ici car les incidents suivants n'avaient pas de
    // 'linkedEmployees', 'risks', ou 'correctiveMeasures' associés dans vos données.
    // Vous pouvez continuer ce modèle pour les autres.
];