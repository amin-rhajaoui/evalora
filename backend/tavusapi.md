Voici un fichier Markdown optimisé pour donner du contexte à **Cursor** (ou tout autre assistant de code IA).

Tu peux enregistrer ce contenu dans un fichier nommé `.cursor/rules/tavus.md` ou simplement `tavus_api.md` à la racine de ton projet, puis le référencer dans le chat de Cursor avec `@tavus_api.md`.

```markdown
# Documentation API Tavus (v2) pour Cursor

## Contexte Global
Tavus est une plateforme de génération vidéo par IA et d'interfaces vidéo conversationnelles (CVI - Conversational Video Interface). Cette documentation couvre l'API v2, qui permet de gérer des répliques (Digital Twins), de générer des vidéos asynchrones et de créer des sessions de conversation vidéo en temps réel.

---

## 1. Configuration & Authentification

- **Base URL** : `https://tavusapi.com/v2`
- **Authentification** : Via Header HTTP `x-api-key`.
- **Clés API** : À générer dans le portail développeur Tavus (Settings -> API Keys).

### Header Standard
```json
{
  "Content-Type": "application/json",
  "x-api-key": "VOTRE_CLE_API"
}

```

---

## 2. Interface Vidéo Conversationnelle (CVI / Phoenix)

Ce module permet de créer des sessions où un utilisateur parle en temps réel avec une réplique IA.

### 2.1 Créer une Conversation

Initialise une session de chat vidéo.

* **Endpoint** : `POST /v2/conversations`
* **Body** :
* `replica_id` (string, requis) : ID de la réplique visuelle.
* `persona_id` (string, requis) : ID du persona (comportement/cerveau).
* `conversation_name` (string, optionnel) : Nom de la session.
* `callback_url` (string, optionnel) : URL pour les webhooks.



**Exemple de requête :**

```bash
curl --request POST \
  --url [https://tavusapi.com/v2/conversations](https://tavusapi.com/v2/conversations) \
  --header 'x-api-key: <api_key>' \
  --header 'Content-Type: application/json' \
  --data '{
    "replica_id": "r9d30b0e55ac",
    "persona_id": "pe13ed370726",
    "conversation_name": "Entretien Utilisateur"
  }'

```

**Réponse (Succès) :**

```json
{
  "conversation_id": "cv_12345",
  "conversation_url": "[https://tavus.video/conversation/cv_12345](https://tavus.video/conversation/cv_12345)",
  "status": "active"
}

```

### 2.2 Personas (Le "Cerveau")

Définit la personnalité, le ton et le contexte de l'IA.

* **Créer un Persona** : `POST /v2/personas`
* **Body** :
* `system_prompt` (string) : Instructions principales (ex: "Tu es un expert en vente...").
* `context` (string) : Contexte additionnel.



---

## 3. Répliques (Digital Twins)

Les répliques sont les clones visuels et vocaux.

### 3.1 Lister les Répliques

Récupère la liste des répliques disponibles pour le compte.

* **Endpoint** : `GET /v2/replicas`

### 3.2 Créer une Réplique

Nécessite généralement l'upload d'une vidéo d'entraînement.

* **Endpoint** : `POST /v2/replicas`

---

## 4. Génération de Vidéo (Asynchrone)

Génération de vidéos scriptées (Text-to-Video ou Audio-to-Video).

### 4.1 Générer une vidéo

* **Endpoint** : `POST /v2/videos`
* **Body** :
* `replica_id` (string) : La réplique à animer.
* `script` (string) : Le texte à dire (si TTS).
* `audio_url` (string, optionnel) : URL d'un fichier audio (si Lipsync uniquement).
* `background_url` (string, optionnel) : URL pour l'arrière-plan.



**Note** : Cette opération est asynchrone. L'API retourne un `video_id` qu'il faut utiliser pour poller le statut ou attendre un webhook.

### 4.2 Récupérer une vidéo

* **Endpoint** : `GET /v2/videos/{video_id}`
* **Statuts possibles** : `queued`, `processing`, `ready`, `failed`.

---

## 5. Knowledge Base (RAG)

Permet d'uploader des documents pour que le Persona puisse s'y référer durant une conversation.

* **Endpoint Upload** : `POST /v2/documents`
* **Types supportés** : PDF, TXT, DOCX, CSV.
* **Utilisation** : Les `document_id` retournés doivent être associés au Persona ou à la Conversation.

---

## 6. Webhooks

Tavus envoie des événements POST à la `callback_url` définie.

### Événements Clés

* `system.replica_joined` : La réplique est entrée dans la room.
* `application.transcription_ready` : La transcription est prête après la conversation.
* `video.ready` : Une vidéo générée est prête au téléchargement.

**Structure Payload Webhook :**

```json
{
  "event_type": "application.transcription_ready",
  "conversation_id": "cv_...",
  "properties": {
    "transcript": [ ... ]
  }
}

```

## Bonnes Pratiques pour le Code (Cursor Rules)

1. **Gestion d'erreurs** : Toujours vérifier les codes 401 (Auth invalide) et 4xx (Mauvais paramètres).
2. **Async** : Les conversations et générations vidéo prennent du temps. Utiliser des mécanismes de polling ou des webhooks, ne pas bloquer le thread principal.
3. **Types** : Utiliser des interfaces TypeScript strictes pour les payloads `persona_id` et `replica_id` pour éviter les erreurs de typage.

```

### Comment l'utiliser avec Cursor ?

1.  **Copie** le code ci-dessus.
2.  **Crée** un fichier nommé `tavus_api.md` dans ton projet.
3.  Dans le chat de Cursor (Cmd+L), tape :
    > "En utilisant @tavus_api.md, écris-moi un script Node.js qui crée une nouvelle conversation vidéo."

```