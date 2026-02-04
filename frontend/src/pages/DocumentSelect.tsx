import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { getDocuments, createSession, createLivekitRoom, getLivekitToken } from "@/services/api"
import { Document } from "@/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
  ArrowRight,
  Check,
  Loader2,
  FileText,
  Building2,
  Palette,
  Leaf,
  Laptop,
  Briefcase,
  BookOpen,
  Globe,
  Users,
  Info,
  BookMarked
} from "lucide-react"

const THEME_ICONS: Record<string, React.ReactNode> = {
  societe: <Building2 className="w-6 h-6" />,
  culture: <Palette className="w-6 h-6" />,
  environnement: <Leaf className="w-6 h-6" />,
  numerique: <Laptop className="w-6 h-6" />,
  travail: <Briefcase className="w-6 h-6" />,
  education: <BookOpen className="w-6 h-6" />,
  diversite: <Globe className="w-6 h-6" />,
  "relations humaines": <Users className="w-6 h-6" />,
}

const THEME_COLORS: Record<string, string> = {
  societe: "bg-blue-500",
  culture: "bg-purple-500",
  environnement: "bg-green-500",
  numerique: "bg-cyan-500",
  travail: "bg-orange-500",
  education: "bg-indigo-500",
  diversite: "bg-pink-500",
  "relations humaines": "bg-rose-500",
}

export default function DocumentSelect() {
  const navigate = useNavigate()
  const {
    studentName,
    studentLevel,
    selectedAvatar,
    selectedDocument,
    setSelectedDocument,
    setSession,
    setLivekitToken,
    setLivekitRoomName,
    setLivekitWsUrl,
    setTavusConversationUrl,
  } = useExam()

  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    if (!studentName) {
      navigate("/setup")
      return
    }

    async function loadDocuments() {
      try {
        const data = await getDocuments()
        setDocuments(data.documents)
      } catch {
        // Error loading documents - silently handled
      } finally {
        setLoading(false)
      }
    }
    loadDocuments()
  }, [studentName, navigate])

  const handleStartExam = async () => {
    if (!selectedDocument) return

    setStarting(true)
    try {
      const session = await createSession({
        student_name: studentName,
        level: studentLevel,
        avatar_id: selectedAvatar?.id,
        document_id: selectedDocument.id,
      })
      setSession(session)

      // Récupérer l'URL de conversation Tavus si disponible
      if (session.tavus_conversation_url) {
        setTavusConversationUrl(session.tavus_conversation_url)
      }

      try {
        const roomRes = await createLivekitRoom(session.id)
        const tokenRes = await getLivekitToken(roomRes.room_name, `student-${session.id}`)
        if (tokenRes.token) {
          setLivekitToken(tokenRes.token)
          setLivekitRoomName(roomRes.room_name)
          if (tokenRes.ws_url) setLivekitWsUrl(tokenRes.ws_url)
        }
      } catch {
        // LiveKit non configuré ou erreur - mode simulation, on continue
      }

      navigate("/exam")
    } catch {
      // Error creating session
      setStarting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-400 to-pink-500 rounded-2xl mb-4 shadow-md">
            <BookMarked className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            Choisissez votre document
          </h1>
          <p className="text-slate-600 mt-2 text-lg">
            Sélectionnez un document qui vous intéresse
          </p>
          
          {/* Message d'aide */}
          <Card className="mt-4 bg-blue-50/80 border-2 border-blue-200 max-w-2xl mx-auto">
            <div className="p-4 flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
              <div className="text-left">
                <p className="text-sm text-slate-700 font-medium mb-1">
                  Comment ça fonctionne ?
                </p>
                <p className="text-xs text-slate-600">
                  Vous allez présenter ce document pendant votre monologue, puis en discuter avec l'examinateur. 
                  <strong className="text-slate-800"> Choisissez celui qui vous inspire le plus !</strong> Il n'y a pas de mauvais choix.
                </p>
              </div>
            </div>
          </Card>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Documents Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  isSelected={selectedDocument?.id === doc.id}
                  onClick={() => setSelectedDocument(doc)}
                />
              ))}
            </div>

            {/* Selected Document Preview */}
            {selectedDocument && (
              <Card className="mb-8 border-2 border-sky-300 bg-gradient-to-br from-white to-sky-50/30 shadow-lg">
                <CardHeader className="bg-gradient-to-r from-sky-50 to-blue-50 border-b border-sky-200">
                  <div className="flex items-start justify-between">
                    <div>
                      <Badge variant="outline" className="mb-3 bg-sky-100 text-sky-700 border-sky-300">
                        {selectedDocument.theme}
                      </Badge>
                      <CardTitle className="text-slate-800 text-xl mb-2">{selectedDocument.title}</CardTitle>
                      <CardDescription className="mt-1 text-slate-600">
                        {selectedDocument.source} | {selectedDocument.author} | {selectedDocument.date}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="bg-white/60 rounded-lg p-4 mb-4 border border-slate-200">
                    <p className="text-foreground leading-relaxed text-base">
                      {selectedDocument.text}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-slate-600 font-medium mr-2">Mots-clés :</span>
                    {selectedDocument.keywords.map((kw, i) => (
                      <Badge key={i} variant="secondary" className="bg-sky-100 text-sky-700 border-sky-200">
                        {kw}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Start Button */}
            <div className="flex flex-col items-center gap-4">
              <Button
                size="xl"
                onClick={handleStartExam}
                disabled={!selectedDocument || starting}
                className="min-w-[280px] bg-gradient-to-r from-sky-500 to-blue-500 hover:from-sky-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl transition-all text-base px-8 py-6 rounded-xl"
              >
                {starting ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    {selectedAvatar
                      ? "Préparation de l'avatar (1–2 min)..."
                      : "Démarrage..."}
                  </>
                ) : (
                  <>
                    Commencer l'entraînement
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </Button>
              
              {selectedDocument && !starting && (
                <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 max-w-md">
                  <div className="p-3 text-center">
                    <p className="text-sm text-slate-700">
                      <strong className="text-green-700">Excellent choix !</strong> 
                      <span className="block mt-1 text-xs text-slate-600">Vous êtes prêt(e) à commencer. Respirez profondément, vous allez bien vous débrouiller ! 😊</span>
                    </p>
                  </div>
                </Card>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function DocumentCard({
  document,
  isSelected,
  onClick,
}: {
  document: Document
  isSelected: boolean
  onClick: () => void
}) {
  const themeKey = document.theme.toLowerCase()
  const icon = THEME_ICONS[themeKey] || <FileText className="w-6 h-6" />
  const bgColor = THEME_COLORS[themeKey] || "bg-slate-500"

  return (
    <button
      onClick={onClick}
      className={cn(
        "relative p-5 rounded-2xl border-2 transition-all text-left w-full",
        "hover:border-sky-400 hover:shadow-lg hover:scale-[1.02]",
        isSelected
          ? "border-sky-500 bg-gradient-to-br from-sky-50 to-blue-50 ring-2 ring-sky-200 shadow-lg"
          : "border-slate-200 bg-white"
      )}
    >
      {isSelected && (
        <div className="absolute top-3 right-3 w-7 h-7 bg-gradient-to-br from-sky-500 to-blue-500 rounded-full flex items-center justify-center shadow-sm">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={cn("w-14 h-14 rounded-xl flex items-center justify-center text-white mb-4 shadow-sm", bgColor)}>
        {icon}
      </div>

      <Badge variant="outline" className="mb-3 text-xs bg-slate-100 text-slate-700 border-slate-300">
        {document.theme}
      </Badge>

      <h3 className="font-semibold text-base text-slate-800 line-clamp-2 mb-2 leading-snug">
        {document.title}
      </h3>

      <p className="text-xs text-slate-500">
        {document.source}
      </p>
    </button>
  )
}
