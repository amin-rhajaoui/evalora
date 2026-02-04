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
import { ArrowRight, Shuffle, UserX, Check, Loader2, Info, Smile, HelpCircle } from "lucide-react"

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
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header avec message rassurant */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-sky-400 to-blue-500 rounded-2xl mb-4 shadow-md">
            <Smile className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Préparation de votre session</h1>
          <p className="text-slate-600 mt-2 text-lg">
            Remplissons ensemble ces quelques informations
          </p>
          <Card className="mt-4 bg-blue-50/80 border-2 border-blue-200 max-w-xl mx-auto">
            <div className="p-4 flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
              <p className="text-sm text-slate-700 text-left">
                <strong className="text-slate-800">Pas de stress !</strong> Ces informations nous aident simplement à personnaliser votre expérience d'entraînement.
              </p>
            </div>
          </Card>
        </div>

        {/* Student Info Card */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-sky-50 to-blue-50 border-b border-slate-200">
            <CardTitle className="text-slate-800 flex items-center gap-2">
              <Smile className="w-5 h-5 text-sky-600" />
              Vos informations
            </CardTitle>
            <CardDescription className="text-slate-600">
              Quelques détails pour personnaliser votre expérience
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            {/* Name Input */}
            <div className="space-y-2">
              <Label htmlFor="name" className="text-slate-700 font-medium">
                Votre prénom <span className="text-sky-500">*</span>
              </Label>
              <Input
                id="name"
                placeholder="Ex: Marie, Ahmed, Sophie..."
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                maxLength={50}
                className="max-w-sm border-2 border-slate-200 focus:border-sky-400 focus:ring-sky-400"
              />
              <p className="text-xs text-slate-500 flex items-center gap-1">
                <HelpCircle className="w-3 h-3" />
                C'est juste pour que l'examinateur puisse vous appeler par votre prénom
              </p>
            </div>

            {/* Level Selection */}
            <div className="space-y-3">
              <Label className="text-slate-700 font-medium">Votre niveau estimé</Label>
              <Card className="bg-slate-50/50 border border-slate-200 p-4">
                <RadioGroup
                  value={studentLevel}
                  onValueChange={(v) => setStudentLevel(v as "A2+" | "B1")}
                  className="flex gap-6"
                >
                  <div className="flex items-center space-x-3">
                    <RadioGroupItem value="A2+" id="a2" className="border-2 border-slate-300" />
                    <Label htmlFor="a2" className="font-normal cursor-pointer text-slate-700">
                      A2+
                    </Label>
                  </div>
                  <div className="flex items-center space-x-3">
                    <RadioGroupItem value="B1" id="b1" className="border-2 border-slate-300" />
                    <Label htmlFor="b1" className="font-normal cursor-pointer text-slate-700">
                      B1
                    </Label>
                  </div>
                </RadioGroup>
              </Card>
              <p className="text-xs text-slate-500 flex items-center gap-1">
                <HelpCircle className="w-3 h-3" />
                Choisissez le niveau qui correspond le mieux à votre niveau actuel
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Avatar Selection Card */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b border-slate-200">
            <CardTitle className="text-slate-800 flex items-center gap-2">
              <Smile className="w-5 h-5 text-purple-600" />
              Votre examinateur
            </CardTitle>
            <CardDescription className="text-slate-600">
              Choisissez un examinateur avec qui vous vous sentez à l'aise, ou laissez-nous choisir pour vous
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
        <div className="flex justify-center pt-6">
          <Button
            size="lg"
            onClick={handleContinue}
            disabled={!canContinue}
            className="min-w-[250px] bg-gradient-to-r from-sky-500 to-blue-500 hover:from-sky-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl transition-all text-base px-8 py-6 rounded-xl"
          >
            Continuer
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </div>
        
        {/* Message d'encouragement */}
        {canContinue && (
          <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200">
            <div className="p-4 text-center">
              <p className="text-sm text-slate-700">
                <strong className="text-green-700">Parfait !</strong> Vous êtes prêt(e) à continuer. 
                <span className="block mt-1 text-xs text-slate-600">Prenez une grande respiration, tout va bien se passer ! 😊</span>
              </p>
            </div>
          </Card>
        )}
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
        "relative p-5 rounded-2xl border-2 transition-all text-left",
        "hover:border-sky-400 hover:bg-sky-50 hover:shadow-md",
        isSelected
          ? "border-sky-500 bg-gradient-to-br from-sky-50 to-blue-50 ring-2 ring-sky-200 shadow-md"
          : "border-slate-200 bg-white"
      )}
    >
      {isSelected && (
        <div className="absolute top-3 right-3 w-6 h-6 bg-gradient-to-br from-sky-500 to-blue-500 rounded-full flex items-center justify-center shadow-sm">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}

      <Avatar className="w-20 h-20 mx-auto mb-4 shadow-sm">
        <AvatarFallback className="text-4xl bg-gradient-to-br from-sky-100 to-blue-100 border-2 border-sky-200">
          {emoji}
        </AvatarFallback>
      </Avatar>

      <div className="text-center">
        <p className="font-semibold text-base text-slate-800 mb-1">{avatar.name}</p>
        <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
          {avatar.personality.split(".")[0]}
        </p>
        <Badge
          variant={avatar.register === "tutoiement" ? "default" : "secondary"}
          className="mt-3 bg-sky-100 text-sky-700 border-sky-200"
        >
          {avatar.register === "tutoiement" ? "Tu" : "Vous"}
        </Badge>
      </div>
    </button>
  )
}
