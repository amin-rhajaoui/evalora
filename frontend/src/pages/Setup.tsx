import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { getAvatars } from "@/services/api"
import { Avatar as AvatarType } from "@/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"
import { ArrowRight, Shuffle, UserX, Check, Loader2 } from "lucide-react"

const AVATAR_EMOJIS: Record<string, string> = {
  clea: "👩‍🏫",
  alex: "🧑‍🎓",
  karim: "👨‍💼",
  claire: "👩‍💼",
}

export default function Setup() {
  const navigate = useNavigate()
  const {
    studentName,
    setStudentName,
    studentLevel,
    setStudentLevel,
    selectedAvatar,
    setSelectedAvatar,
  } = useExam()

  const [avatars, setAvatars] = useState<AvatarType[]>([])
  const [loading, setLoading] = useState(true)
  const [noAvatar, setNoAvatar] = useState(false)

  useEffect(() => {
    async function loadAvatars() {
      try {
        const data = await getAvatars()
        setAvatars(data.avatars)
      } catch {
        // Error loading avatars - continue with empty list
      } finally {
        setLoading(false)
      }
    }
    loadAvatars()
  }, [])

  const handleAvatarSelect = (avatar: AvatarType) => {
    setSelectedAvatar(avatar)
    setNoAvatar(false)
  }

  const handleNoAvatar = () => {
    setSelectedAvatar(null)
    setNoAvatar(true)
  }

  const handleRandomAvatar = () => {
    const randomIndex = Math.floor(Math.random() * avatars.length)
    setSelectedAvatar(avatars[randomIndex])
    setNoAvatar(false)
  }

  const handleContinue = () => {
    if (studentName.trim()) {
      navigate("/documents")
    }
  }

  const canContinue = studentName.trim() && (selectedAvatar || noAvatar)

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Configuration</h1>
          <p className="text-muted-foreground mt-2">
            Configurez votre session d'examen
          </p>
        </div>

        {/* Student Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>Informations</CardTitle>
            <CardDescription>
              Entrez votre prenom et selectionnez votre niveau
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Name Input */}
            <div className="space-y-2">
              <Label htmlFor="name">Prenom *</Label>
              <Input
                id="name"
                placeholder="Entrez votre prenom"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                maxLength={50}
                className="max-w-sm"
              />
            </div>

            {/* Level Selection */}
            <div className="space-y-3">
              <Label>Niveau estime</Label>
              <RadioGroup
                value={studentLevel}
                onValueChange={(v) => setStudentLevel(v as "A2+" | "B1")}
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="A2+" id="a2" />
                  <Label htmlFor="a2" className="font-normal cursor-pointer">
                    A2+
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="B1" id="b1" />
                  <Label htmlFor="b1" className="font-normal cursor-pointer">
                    B1
                  </Label>
                </div>
              </RadioGroup>
            </div>
          </CardContent>
        </Card>

        {/* Avatar Selection Card */}
        <Card>
          <CardHeader>
            <CardTitle>Examinateur</CardTitle>
            <CardDescription>
              Choisissez votre examinateur virtuel ou laissez le hasard decider
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {/* Avatar Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {avatars.map((avatar) => (
                    <AvatarCard
                      key={avatar.id}
                      avatar={avatar}
                      emoji={AVATAR_EMOJIS[avatar.id] || "👤"}
                      isSelected={selectedAvatar?.id === avatar.id}
                      onClick={() => handleAvatarSelect(avatar)}
                    />
                  ))}
                </div>

                {/* Options */}
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    variant={noAvatar ? "default" : "outline"}
                    onClick={handleNoAvatar}
                    className="flex-1"
                  >
                    <UserX className="w-4 h-4 mr-2" />
                    Sans avatar
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleRandomAvatar}
                    className="flex-1"
                  >
                    <Shuffle className="w-4 h-4 mr-2" />
                    Aleatoire
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Continue Button */}
        <div className="flex justify-end pt-4">
          <Button
            size="lg"
            onClick={handleContinue}
            disabled={!canContinue}
            className="min-w-[200px]"
          >
            Continuer
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function AvatarCard({
  avatar,
  emoji,
  isSelected,
  onClick,
}: {
  avatar: AvatarType
  emoji: string
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative p-4 rounded-xl border-2 transition-all text-left",
        "hover:border-primary/50 hover:bg-slate-50",
        isSelected
          ? "border-primary bg-primary/5 ring-2 ring-primary/20"
          : "border-slate-200 bg-white"
      )}
    >
      {isSelected && (
        <div className="absolute top-2 right-2 w-5 h-5 bg-primary rounded-full flex items-center justify-center">
          <Check className="w-3 h-3 text-white" />
        </div>
      )}

      <Avatar className="w-16 h-16 mx-auto mb-3">
        <AvatarFallback className="text-3xl bg-slate-100">
          {emoji}
        </AvatarFallback>
      </Avatar>

      <div className="text-center">
        <p className="font-semibold text-sm">{avatar.name}</p>
        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
          {avatar.personality.split(".")[0]}
        </p>
        <Badge
          variant={avatar.register === "tutoiement" ? "info" : "secondary"}
          className="mt-2"
        >
          {avatar.register === "tutoiement" ? "Tu" : "Vous"}
        </Badge>
      </div>
    </button>
  )
}
