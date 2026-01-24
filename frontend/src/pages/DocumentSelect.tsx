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
  Users
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
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">
            Choisissez votre document
          </h1>
          <p className="text-muted-foreground mt-2">
            Ce document servira de support pour votre monologue et le debat
          </p>
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
              <Card className="mb-8">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <Badge variant="outline" className="mb-2">
                        {selectedDocument.theme}
                      </Badge>
                      <CardTitle>{selectedDocument.title}</CardTitle>
                      <CardDescription className="mt-1">
                        {selectedDocument.source} | {selectedDocument.author} | {selectedDocument.date}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-foreground leading-relaxed mb-4">
                    {selectedDocument.text}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedDocument.keywords.map((kw, i) => (
                      <Badge key={i} variant="secondary">
                        {kw}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Start Button */}
            <div className="flex justify-center">
              <Button
                size="xl"
                onClick={handleStartExam}
                disabled={!selectedDocument || starting}
                className="min-w-[250px]"
              >
                {starting ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    {selectedAvatar
                      ? "Preparation de l'avatar (1–2 min)..."
                      : "Demarrage..."}
                  </>
                ) : (
                  <>
                    Commencer l'examen
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </Button>
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
        "relative p-4 rounded-xl border-2 transition-all text-left w-full",
        "hover:border-primary/50 hover:shadow-md",
        isSelected
          ? "border-primary bg-white ring-2 ring-primary/20 shadow-md"
          : "border-slate-200 bg-white"
      )}
    >
      {isSelected && (
        <div className="absolute top-3 right-3 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={cn("w-12 h-12 rounded-lg flex items-center justify-center text-white mb-3", bgColor)}>
        {icon}
      </div>

      <Badge variant="outline" className="mb-2 text-xs">
        {document.theme}
      </Badge>

      <h3 className="font-semibold text-sm line-clamp-2 mb-1">
        {document.title}
      </h3>

      <p className="text-xs text-muted-foreground">
        {document.source}
      </p>
    </button>
  )
}
