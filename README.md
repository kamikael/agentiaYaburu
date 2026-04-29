# 🤖 Yaburu ChatBot IA - Assistant Conversationnel WhatsApp

> Assistant IA intelligent pour vendeurs africains sur la plateforme Yaburu

## 📋 Aperçu

Yaburu ChatBot est un assistant conversationnel intelligent qui aide les vendeurs e-commerce à gérer leur boutique directement via WhatsApp, utilisant l'IA (Gemini 2.0 Flash) et l'orchestration d'agents avec LangGraph.

### ✨ Fonctionnalités Principales

```
✓ Assistance 24/7 via WhatsApp
✓ Gestion produits/stocks/ventes en langage naturel
✓ Support FAQ avec RAG (Retrieval-Augmented Generation)
✓ Mémoire conversationnelle persistante
✓ Actions sécurisées via API Yaburu
✓ Scalabilité multi-utilisateurs
✓ Monitoring & analytics
```

### 📊 Stack Technique

```
Backend:        FastAPI + Uvicorn + Async
Agent IA:       LangChain + LangGraph + Gemini 2.0 Flash
Database:       Supabase (PostgreSQL + pgvector)
Intégrations:   WhatsApp Business API (Meta)
Deployment:     Docker + GitHub Actions + Render/Railway
```

---

## 🚀 Démarrage Rapide

### Prérequis

```bash
Python 3.11+
Docker & Docker Compose
Git
Compte Meta Developer (WhatsApp API)
Clé API Google Gemini
Projet Supabase
```

### 1️⃣ Setup Local (2 min)

```bash
# Clone repo
git clone <repo_url>
cd yaburu-chatbot

# Créer virtualenv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Copier .env
cp .env.example .env
# ⚠️ Remplir les valeurs dans .env
```

### 2️⃣ Docker Compose (Dev Environment)

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier logs
docker-compose logs -f app

# Accéder à l'app
http://localhost:8000/health
http://localhost:8080/  # Adminer (DB management)
```

### 3️⃣ Tester Webhook WhatsApp

```bash
# Test local webhook verify
curl -X GET "http://localhost:8000/api/webhook?token=your_verify_token&challenge=test_challenge"

# Simuler un message
curl -X POST "http://localhost:8000/api/webhook" \
  -H "X-Hub-Signature-256: sha256=..." \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "1234567890",
            "id": "msg_123",
            "timestamp": "1234567890",
            "text": {"body": "Combien en stock?"},
            "type": "text"
          }]
        }
      }]
    }]
  }'
```

### 4️⃣ Exécuter Tests

```bash
# Tests unitaires
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=app --cov-report=html

# Ouvrir report
open htmlcov/index.html
```

---

## 📁 Structure du Projet

```
yaburu-chatbot/
├── app/
│   ├── api/                 # Routes FastAPI
│   │   ├── routes.py       # Endpoints
│   │   └── middleware.py   # Auth, CORS, rate limiting
│   ├── agent/              # Logique IA
│   │   ├── graph.py        # LangGraph workflow
│   │   ├── tools.py        # LangChain tools
│   │   ├── prompts.py      # System prompts
│   │   └── rag.py          # RAG + vector search
│   ├── services/           # Business logic
│   │   ├── whatsapp_service.py
│   │   ├── yaburu_service.py
│   │   ├── memory_service.py
│   │   └── logging_service.py
│   ├── models/             # Schemas Pydantic
│   ├── utils/              # Helpers
│   └── handlers/           # Webhook handler
├── tests/                  # Test suite
├── docker/                 # Docker files
├── scripts/                # Migration, setup
├── main.py                 # App entry point
├── config.py               # Settings
├── requirements.txt        # Dependencies
├── docker-compose.yml      # Local dev environment
├── Dockerfile              # Production image
└── .github/workflows/      # CI/CD pipelines
```

---

## ⚙️ Configuration

### Variables d'Environnement (.env)

```bash
# App
DEBUG=False
ENVIRONMENT=development

# WhatsApp / Meta
WHATSAPP_API_TOKEN=...
WHATSAPP_SECRET=...
WEBHOOK_VERIFY_TOKEN=...

# Yaburu API
YABURU_API_URL=https://api.yaburu.com/v1
YABURU_API_KEY=...

# Google Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash

# Supabase
SUPABASE_URL=...
SUPABASE_KEY=...

# Monitoring
SENTRY_DSN=...
LOG_LEVEL=INFO
```

### Initialiser Base de Données

```bash
# Créer tables
python scripts/migrate.py upgrade

# Charger documentation dans RAG
python scripts/seed_rag.py
```

---

## 🧠 Architecture Agent IA

### Flux Principal

```
Message WhatsApp
    ↓
[Webhook FastAPI] ← Validation signature Meta
    ↓
[LangGraph Agent]
├─ receive_message    → Parse input
├─ classify_intent    → Détect intent (FAQ, check_stock, etc.)
├─ retrieve_docs      → RAG search (optional)
├─ route_to_tool      → Sélect tool
├─ execute_tools      → Appel API Yaburu
└─ generate_response  → LLM génère réponse
    ↓
[Memory Persistence] → Supabase
    ↓
[Response WhatsApp]  → Meta API → Utilisateur
```

### Intents Supportés

```
✓ faq_help          → Questions fréquentes
✓ check_stock       → Vérifier stock produit
✓ get_sales         → Consulter ventes
✓ create_product    → Créer produit (multi-turn)
✓ get_stats         → Statistiques boutique
```

### Tools Disponibles

```python
# Disponible dans agent/tools.py
@tool
async def check_stock(shop_id, product_id) -> str
@tool
async def get_sales(shop_id, period="day") -> str
@tool
async def create_product(shop_id, product_data) -> str
@tool
async def get_stats(shop_id) -> str
```

---

## 🔒 Sécurité

### Authentication WhatsApp

```python
# Validation signature Meta (obligatoire)
from app.api.middleware import validate_meta_signature

# Tous les webhooks sont vérifiés avant traitement
```

### Rate Limiting

```python
# Limité à 100 requêtes/minute par IP
@limiter.limit("100/minute")
async def webhook(request: Request):
    pass
```

### Secrets Management

```bash
# Ne JAMAIS commit .env
echo ".env" >> .gitignore

# Utiliser GitHub Secrets pour CI/CD
# Settings → Secrets → Actions
GEMINI_API_KEY=...
SUPABASE_KEY=...
```

---

## 📊 Monitoring & Logging

### Logs Structurés

```python
import structlog

logger = structlog.get_logger()
logger.info("message", user_id="123", intent="check_stock")
# Sortie JSON pour agrégation facile
```

### Sentry (Error Tracking)

```python
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(settings.SENTRY_DSN)
    # Erreurs tracées automatiquement
```

### Métriques Prometheus

```python
from prometheus_client import Counter, Histogram

webhook_requests = Counter('webhook_requests_total', 'Total webhook requests')
response_time = Histogram('response_time_seconds', 'Response time')
```

---

## 🚀 Déploiement

### Déploiement sur Render.com

```bash
# 1. Créer web service sur Render
#    - Connecter repo GitHub
#    - Branche: main
#    - Build command: pip install -r requirements.txt
#    - Start command: uvicorn main:app --host 0.0.0.0

# 2. Ajouter variables d'environnement
#    Settings → Environment

# 3. Deploy
#    Push to main → GitHub Actions → Auto deploy

# Vérifier déploiement
curl https://your-render-app.onrender.com/health
```

### Déploiement sur Railway

```bash
# 1. Installer Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Deploy
railway up

# 4. Config env
railway open → Project Settings
```

### CI/CD GitHub Actions

```bash
# Pipeline automatique sur:
# - PR → Tests
# - Push develop → Deploy staging
# - Push main → Deploy production

# Voir: .github/workflows/deploy.yml
```

---

## 🧪 Tests

### Test Structure

```
tests/
├── test_api.py           # API routes
├── test_agent.py         # Agent logic
├── test_tools.py         # Tool execution
├── test_integration.py   # E2E tests
└── mocks/
    ├── meta_webhook.py   # Mock Meta
    └── yaburu_api.py     # Mock Yaburu
```

### Exécuter Tests

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_agent.py::test_classify_intent -v

# Mode watch
pytest-watch tests/
```

### Exemple Test

```python
@pytest.mark.asyncio
async def test_agent_check_stock():
    agent = create_agent_graph()
    
    state = {
        "user_id": "test_123",
        "messages": [],
        "current_input": "Combien en stock?",
        "intent": "",
        "response": ""
    }
    
    result = agent.invoke(state)
    
    assert "stock" in result["response"].lower()
```

---

## 📈 Performance & Optimisation

### Tokens Gemini (Coûts)

```
Consommation estimée: 67,500 tokens/jour/utilisateur
Coûts mensuels (Gemini 2.0 Flash):
- 100 users   → ~42k FCFA
- 300 users   → ~169k FCFA
- 1000 users  → ~605k FCFA
```

### Optimisation Possible

```python
# 1. Cache responses (Redis)
# 2. Batch API calls
# 3. Limit RAG context
# 4. Use faster embeddings
# 5. Async all I/O operations
```

---

## 🐛 Troubleshooting

### Webhook ne reçoit pas de messages

```bash
# 1. Vérifier token
# Verify token doit match WEBHOOK_VERIFY_TOKEN

# 2. Checker signature validation
# Voir logs pour "Signature validation failed"

# 3. URL publique?
# Webhook doit être accessible publiquement
# ngrok pour test local: ngrok http 8000
```

### LLM Timeout

```python
# Augmenter timeout Gemini
GEMINI_TIMEOUT=60  # 60 secondes

# Ou réduire max_tokens
GEMINI_MAX_TOKENS=512
```

### Erreur Supabase

```bash
# Tester connexion
psql postgresql://user:pwd@host/db

# Vérifier JWT secret
SELECT * FROM supabase.users;

# Réinitialiser credentials si leak
```

---

## 📚 Documentation Additionnelle

- [Architecture Détaillée](./ARCHITECTURE.md)
- [API Reference](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Contributing](./CONTRIBUTING.md)
- [LangChain Docs](https://python.langchain.com/)
- [Meta WhatsApp API](https://developers.facebook.com/docs/whatsapp)

---

## 💬 Support

### Issues & Bugs

```bash
# Créer issue GitHub
# Inclure: logs, steps to reproduce, environment
```

### Slack Channel

```
#yaburu-chatbot-support
```

### Email

```
dev@yaburu.com
```

---

## 📄 Licence

```
MIT License - See LICENSE.txt
```

---

## 🙏 Contribuer

Voir [CONTRIBUTING.md](./CONTRIBUTING.md) pour guidelines.

```bash
# Workflow:
1. Fork repo
2. Create feature branch (git checkout -b feature/xyz)
3. Commit changes (git commit -m 'Add xyz')
4. Push to branch (git push origin feature/xyz)
5. Open Pull Request
```

---

## 🎯 Roadmap

### Q1 2025

- [x] MVP foundation
- [ ] Multi-language support
- [ ] Advanced analytics
- [ ] Custom training data

### Q2 2025

- [ ] Mobile app
- [ ] More integrations
- [ ] Advanced RAG
- [ ] Marketing automations

---

**Status:** 🟢 Production Ready  
**Last Updated:** 2025-01-01  
**Maintained By:** Dev Team Yaburu