# 🚀 Configuration du projet FireTeams

## 📋 Prérequis
- Docker et Docker Compose installés
- Credentials AWS (Access Key, Secret Key, Session Token)

## ⚙️ Configuration

### 1. Copier le fichier d'environnement
```bash
cp .env.example .env
```

### 2. Éditer le fichier `.env`
Ouvrez le fichier `.env` et remplissez vos credentials AWS :

```bash
# AWS Configuration - À REMPLIR AVEC VOS VRAIES VALEURS
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=VOTRE_ACCESS_KEY_ICI
AWS_SECRET_ACCESS_KEY=VOTRE_SECRET_KEY_ICI
AWS_SESSION_TOKEN=VOTRE_SESSION_TOKEN_ICI
```

**Note:** Les autres variables (PostgreSQL, OpenSearch) sont déjà configurées avec des valeurs par défaut.

### 3. Lancer le projet
```bash
# Build et démarrage des conteneurs
docker compose up -d

# Vérifier les logs
docker compose logs -f

# Arrêter les conteneurs
docker compose down
```

## 🌐 Accès aux services

Une fois les conteneurs démarrés, vous pouvez accéder à :

- **Frontend (Next.js):** http://localhost:3000
- **Backend API (FastAPI):** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **OpenSearch Dashboards:** http://localhost:5601
- **PostgreSQL:** localhost:5432

## 🔐 Sécurité

⚠️ **IMPORTANT:** 
- Ne commitez JAMAIS le fichier `.env` (il est déjà dans `.gitignore`)
- Ne partagez JAMAIS vos credentials AWS
- Utilisez `.env.example` pour documenter les variables nécessaires

## 🛠️ Commandes utiles

```bash
# Rebuild un service spécifique
docker compose build backend
docker compose build web

# Voir les logs d'un service
docker compose logs -f backend
docker compose logs -f web

# Redémarrer un service
docker compose restart backend

# Supprimer tout et recommencer
docker compose down -v
docker compose up -d --build
```

## 📦 Structure des variables d'environnement

### PostgreSQL
- `POSTGRES_USER`: Utilisateur de la base de données
- `POSTGRES_PASSWORD`: Mot de passe de la base de données
- `POSTGRES_DB`: Nom de la base de données

### OpenSearch
- `OPENSEARCH_INITIAL_ADMIN_PASSWORD`: Mot de passe admin OpenSearch
- `OPENSEARCH_USERNAME`: Nom d'utilisateur OpenSearch
- `OPENSEARCH_PASSWORD`: Mot de passe OpenSearch

### Backend
- `OS_HOST`: Hôte OpenSearch
- `OS_PORT`: Port OpenSearch
- `DB_HOST`: Hôte PostgreSQL
- `DB_PORT`: Port PostgreSQL

### AWS
- `AWS_DEFAULT_REGION`: Région AWS
- `AWS_ACCESS_KEY_ID`: Votre Access Key AWS
- `AWS_SECRET_ACCESS_KEY`: Votre Secret Key AWS
- `AWS_SESSION_TOKEN`: Votre Session Token AWS

### Frontend
- `NEXT_PUBLIC_API_URL`: URL de l'API pour le client (navigateur)
- `API_BASE_URL`: URL de l'API pour le serveur Next.js
