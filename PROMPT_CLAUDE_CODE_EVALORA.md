# Prompt d'implémentation Evalora — À coller dans Claude Code

---

## Contexte du projet

Tu travailles sur **Evalora**, un simulateur d'examen de production orale pour le DU FLE (Diplôme Universitaire de Français Langue Étrangère) de la Sorbonne Abu Dhabi. Le projet est en production avec de vrais étudiants. Il s'agit d'une application full-stack avec un agent vocal IA multi-phases.

**Stack :** FastAPI + Python (backend) · React + TypeScript (frontend) · LiveKit Agents Python (agent vocal) · Neon PostgreSQL · ElevenLabs TTS · OpenAI GPT-4o · Tavus CVI (intégration en cours)

---

## Instructions obligatoires AVANT de coder

**Avant chaque tâche, lis impérativement le(s) skill(s) correspondant(s) :**

```
CLAUDE.md                                        ← Point d'entrée, lis TOUJOURS en premier
.claude/skills/00-project/SKILL.md               ← Architecture, stack, règles absolues
.claude/skills/01-security/SKILL.md              ← Sécurité, .env, credentials
.claude/skills/02-tavus-integration/SKILL.md     ← Tavus CVI, avatar vidéo
.claude/skills/03-agent-livekit/SKILL.md         ← Agent vocal, phases d'examen
.claude/skills/04-evaluation/SKILL.md            ← Évaluation LLM, grille DU FLE
.claude/skills/05-frontend-exam/SKILL.md         ← React, LiveKit UI, Exam.tsx
```

**Règle :** Si tu touches à un fichier sans avoir lu le skill associé, tu risques de casser une contrainte critique (silence monologue, comptage questions, sécurité...).

---

## Tâches à implémenter — Dans cet ordre exact

### 🔴 SPRINT 1 — Sécurité (lis `.claude/skills/01-security/SKILL.md`)

**Tâche 1.1 — Sécuriser les credentials**
- Ouvrir `backend/app/config.py`
- Supprimer `JWT_SECRET_KEY` de la valeur par défaut — la variable doit être sans défaut, lue depuis `.env` uniquement
- Supprimer `DATABASE_URL` de la valeur par défaut — même traitement
- Créer `backend/.env.example` avec le template documenté dans le skill 01
- Vérifier que `.env` est dans `.gitignore`
- Valider : `grep -r "secret-key-change\|npg_" backend/app/` doit retourner vide

**Tâche 1.2 — Passer GPT-4o-mini → GPT-4o**
- `agent/agent.py` : remplacer `model="gpt-4o-mini"` par `model="gpt-4o"` dans `AgentSession`
- `backend/app/services/evaluation_service.py` : remplacer `"model": "gpt-4o-mini"` par `"model": "gpt-4o"`
- Augmenter le timeout de l'appel évaluation de 30s à 90s

---

### 🟠 SPRINT 2 — Intégration Tavus (lis `.claude/skills/02-tavus-integration/SKILL.md`)

**Tâche 2.1 — Migration base de données**
- Créer `backend/app/alembic/versions/006_add_tavus_conversation_id.py`
- Ajouter la colonne `tavus_conversation_id: String(128), nullable=True` à la table `exam_sessions`
- Ajouter la colonne dans le modèle SQLAlchemy `backend/app/db/models.py` → classe `ExamSession`
- Appliquer : `alembic upgrade head`

**Tâche 2.2 — Router backend Tavus**
- Créer `backend/app/routers/tavus.py` avec les endpoints :
  - `POST /api/tavus/{session_id}/start` → crée une conversation Tavus, sauvegarde `conversation_id` en BDD, retourne `conversation_url`
  - `DELETE /api/tavus/{session_id}/end` → termine la conversation Tavus
- Le router doit mapper `avatar_id` → `persona_id` Tavus via `TAVUS_PERSONAS = {"clea": "p0bd677850df", ...}`
- Enregistrer le router dans `backend/app/main.py`
- Ajouter `TAVUS_API_KEY` dans `backend/app/config.py` (lu depuis `.env`)

**Tâche 2.3 — Service API Tavus côté frontend**
- Dans `frontend/src/services/api.ts`, ajouter :
  - `startTavusConversation(sessionId: string): Promise<TavusSession>`
  - `endTavusConversation(sessionId: string): Promise<void>`
- Dans `frontend/src/types/index.ts`, ajouter l'interface `TavusSession`

**Tâche 2.4 — Composant TavusPlayer**
- Créer `frontend/src/components/TavusPlayer.tsx`
- Le composant reçoit `conversationUrl: string | null` et `isVisible: boolean`
- Si `conversationUrl` est null → afficher un placeholder sombre avec "Connexion avatar..."
- Si disponible → afficher un `<iframe>` avec les permissions `camera; microphone; autoplay; display-capture`
- Style : `w-full aspect-video rounded-xl overflow-hidden`

**Tâche 2.5 — Intégration dans Exam.tsx**
- Ajouter `const [tavusUrl, setTavusUrl] = useState<string | null>(null)`
- Au moment où LiveKit est connecté (`livekitConnected === true`), appeler `startTavusConversation(session.id)` et stocker l'URL
- Dans `handleEndConversation`, appeler `endTavusConversation(session.id)` avant `navigate("/results")`
- Remplacer le placeholder avatar actuel par `<TavusPlayer conversationUrl={tavusUrl} isVisible={livekitConnected} />`

---

### 🟡 SPRINT 3 — Qualité évaluation (lis `.claude/skills/04-evaluation/SKILL.md`)

**Tâche 3.1 — Améliorer le prompt d'évaluation**
- Dans `backend/app/services/evaluation_service.py`, remplacer `EVALUATION_PROMPT` par la version améliorée du skill 04 qui inclut :
  - Les dimensions IC manquantes dans le critère `interaction` (gestion tours de parole, demandes de clarification, rebonds)
  - Le disclaimer obligatoire sur la prononciation : `"⚠️ Score indicatif — à confirmer avec un professeur."`
  - La note de calibration contre la surévaluation des niveaux A2+/B1
- Ajouter `"response_format": {"type": "json_object"}` à l'appel OpenAI pour forcer le JSON

**Tâche 3.2 — Adapter le ton du feedback par avatar**
- Dans `evaluation_service.py`, créer la méthode `adapt_feedback_tone(evaluation, avatar_config)` selon le skill 04
- L'appeler dans `auto_evaluate` avant de persister en BDD
- Les 4 avatars ont des tons distincts : Cléa (empathique), Alex (décontracté), Karim (neutre analytique), Claire (exigeant)

**Tâche 3.3 — Corriger le placement du critère `comprehension`**
- Dans `backend/app/config.py`, déplacer `comprehension` (max 1.0) depuis la section `general` vers la section `debat`
- Mettre à jour les totaux : `debat` passe de 4.5 à 5.5 pts, `general` passe de 7.0 à 6.0 pts
- Mettre à jour le prompt d'évaluation en conséquence

---

## Règles absolues — Ne jamais violer

Ces contraintes sont issues du cahier des charges officiel. Toute modification qui les brise est un bug critique.

1. **`MonologueAgent.llm_node()` doit retourner `[]`** — c'est la seule garantie du silence pendant le monologue. Ne jamais appeler `super().llm_node()` dans cet agent.

2. **Exactement 5 questions en débat** — le compteur est dans `on_conversation_item`. Ne pas modifier la logique de comptage sans lire le skill 03 en entier.

3. **JWT_SECRET_KEY et DATABASE_URL jamais dans le code** — uniquement dans `.env`. Un commit avec ces valeurs est une faille de sécurité immédiate.

4. **GPT-4o obligatoire** pour le débat et l'évaluation — jamais `gpt-4o-mini` ni autre modèle moins capable.

5. **DataChannel topic `"exam"`** pour tous les events LiveKit — ne pas changer ce topic sans modifier simultanément l'agent et le frontend.

6. **Toujours async/await** — jamais de code synchrone bloquant dans le backend ou l'agent.

7. **La note n'est jamais révélée avant la phase `feedback`** — ni dans le LLM du débat, ni dans les events DataChannel.

---

## Validation après chaque sprint

### Après Sprint 1
```bash
# Aucun credential dans le code
grep -r "secret-key-change\|npg_\|sk-proj" backend/app/ agent/
# → Doit retourner vide

# Backend démarre
uvicorn app.main:app --port 8000
curl http://localhost:8000/health
# → {"status": "healthy"}
```

### Après Sprint 2
```bash
# Migration appliquée
alembic current
# → 006_tavus (head)

# Endpoint Tavus répond
curl -X POST http://localhost:8000/api/tavus/TEST_SESSION/start \
  -H "Authorization: Bearer TOKEN"
# → {"conversation_id": "...", "conversation_url": "...", "status": "active"}
  
# TavusPlayer s'affiche dans Exam.tsx sans erreur TypeScript
cd frontend && npm run build
# → Build réussi sans erreurs
```

### Après Sprint 3
```bash
# Évaluation retourne du JSON valide
curl -X POST http://localhost:8000/api/evaluation/auto-evaluate?session_id=TEST
# → {"total_score": X, "grade_letter": "...", "passed": true/false}

# Le feedback prononciation contient le disclaimer
curl http://localhost:8000/api/evaluation/TEST | jq '.detailed_scores.general[] | select(.criterion == "prononciation") | .comment'
# → "⚠️ Score indicatif — à confirmer avec un professeur. ..."
```

---

## En cas de doute

- **Tu ne sais pas comment une partie fonctionne** → Lis d'abord le skill correspondant, puis explore le fichier concerné dans le repo
- **Tu veux modifier l'architecture multi-agents** → Lis `.claude/skills/03-agent-livekit/SKILL.md` en entier avant toute modification
- **Tu touches à l'évaluation** → Les scores doivent toujours sommer à 20.0 pts maximum
- **Tu crées un nouveau fichier Python** → Il doit être async, utiliser `httpx` (pas `requests`), et ses exceptions doivent être catchées pour ne pas faire crasher l'agent
- **Tu crées un nouveau composant React** → Il doit utiliser `useExam()` pour lire l'état global, pas des props chaînées

---

*Evalora — Sorbonne Abu Dhabi — PRD v2.0 — Février 2026*
