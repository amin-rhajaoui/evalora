import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import {
  Trophy,
  Target,
  TrendingUp,
  Lightbulb,
  Clock,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Star,
  Heart,
  Sparkles,
  ThumbsUp,
  Award,
  MessageCircle,
  User,
  Bot,
} from "lucide-react"

export default function Results() {
  const navigate = useNavigate()
  const { feedback, selectedAvatar, resetExam, conversationTranscript } = useExam()

  const handleRestart = () => {
    resetExam()
    navigate("/")
  }

  const displayFeedback = feedback || {
    total_score: 0,
    max_score: 20,
    grade_letter: "E",
    passed: false,
    monologue_score: 0,
    monologue_max: 8.5,
    debat_score: 0,
    debat_max: 4.5,
    general_score: 0,
    general_max: 7,
    summary: "Evaluation en cours...",
    strengths: [],
    improvements: [],
    advice: [],
    monologue_duration: "--:--",
    debat_duration: "--:--",
    total_duration: "--:--",
  }

  const scorePercent = (displayFeedback.total_score / displayFeedback.max_score) * 100

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-amber-400 to-orange-500 rounded-3xl mb-4 shadow-lg">
            <Trophy className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Vos résultats</h1>
          {selectedAvatar && (
            <p className="text-slate-600 mt-1">
              Examinateur: <span className="font-semibold text-slate-800">{selectedAvatar.name}</span>
            </p>
          )}
          <Card className="mt-4 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 max-w-xl mx-auto">
            <div className="p-4 text-center">
              <p className="text-sm text-slate-700">
                <Heart className="w-4 h-4 inline mr-1 text-pink-400" />
                <strong className="text-green-700">Bravo pour votre participation !</strong>
                <span className="block mt-1 text-xs text-slate-600">Chaque entraînement est une étape vers le progrès</span>
              </p>
            </div>
          </Card>
        </div>

        {/* Score Card */}
        <Card className="overflow-hidden border-2 border-slate-200 shadow-lg">
          <div className={cn(
            "p-10 text-center text-white relative overflow-hidden",
            displayFeedback.passed
              ? "bg-gradient-to-br from-green-500 via-emerald-500 to-teal-500"
              : "bg-gradient-to-br from-amber-400 via-orange-400 to-yellow-400"
          )}>
            {/* Éléments décoratifs */}
            <div className="absolute top-4 right-4 opacity-20">
              <Sparkles className="w-16 h-16" />
            </div>
            <div className="absolute bottom-4 left-4 opacity-20">
              <Award className="w-12 h-12" />
            </div>
            
            <div className="relative z-10">
              <div className="flex items-center justify-center gap-3 mb-5">
                {displayFeedback.passed ? (
                  <>
                    <CheckCircle2 className="w-10 h-10" />
                    <Badge variant="secondary" className="text-xl px-5 py-2 bg-white/20 backdrop-blur-sm border-white/30">
                      {displayFeedback.grade_letter}
                    </Badge>
                  </>
                ) : (
                  <>
                    <ThumbsUp className="w-10 h-10" />
                    <Badge variant="secondary" className="text-xl px-5 py-2 bg-white/20 backdrop-blur-sm border-white/30">
                      {displayFeedback.grade_letter}
                    </Badge>
                  </>
                )}
              </div>

              <div className="text-7xl font-bold mb-3 drop-shadow-lg">
                {displayFeedback.total_score.toFixed(1)}
                <span className="text-3xl opacity-90">/{displayFeedback.max_score}</span>
              </div>

              <p className="text-xl font-semibold opacity-95 mb-2">
                {displayFeedback.passed 
                  ? "🎉 Félicitations, vous avez réussi !" 
                  : "💪 Continuez vos efforts, vous progressez !"}
              </p>
              <p className="text-base opacity-90">
                {displayFeedback.passed 
                  ? "Votre travail porte ses fruits !" 
                  : "Chaque tentative vous rapproche de votre objectif"}
              </p>
            </div>
          </div>

          <CardContent className="p-6">
            {/* Score Breakdown */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <ScoreBlock
                label="Monologue"
                score={displayFeedback.monologue_score}
                max={displayFeedback.monologue_max}
                icon={<Target className="w-4 h-4" />}
              />
              <ScoreBlock
                label="Debat"
                score={displayFeedback.debat_score}
                max={displayFeedback.debat_max}
                icon={<TrendingUp className="w-4 h-4" />}
              />
              <ScoreBlock
                label="General"
                score={displayFeedback.general_score}
                max={displayFeedback.general_max}
                icon={<Star className="w-4 h-4" />}
              />
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Score global</span>
                <span className="font-medium">{scorePercent.toFixed(0)}%</span>
              </div>
              <Progress value={scorePercent} className="h-3" />
            </div>
          </CardContent>
        </Card>

        {/* Summary */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-amber-50 to-orange-50 border-b-2 border-slate-200">
            <CardTitle className="flex items-center gap-2 text-slate-800">
              <Trophy className="w-5 h-5 text-amber-500" />
              Résumé de votre performance
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="bg-white/60 rounded-lg p-4 border border-slate-200">
              <p className="text-foreground leading-relaxed text-base">
                {displayFeedback.summary}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Strengths */}
        {displayFeedback.strengths.length > 0 && (
          <Card className="border-2 border-green-200 shadow-sm bg-gradient-to-br from-green-50 to-emerald-50">
            <CardHeader className="border-b-2 border-green-200">
              <CardTitle className="flex items-center gap-2 text-green-700">
                <CheckCircle2 className="w-5 h-5" />
                Vos points forts ✨
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <ul className="space-y-3">
                {displayFeedback.strengths.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-green-200 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                      <CheckCircle2 className="w-4 h-4 text-green-700" />
                    </div>
                    <span className="text-slate-700 leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Improvements */}
        {displayFeedback.improvements.length > 0 && (
          <Card className="border-2 border-amber-200 shadow-sm bg-gradient-to-br from-amber-50 to-orange-50">
            <CardHeader className="border-b-2 border-amber-200">
              <CardTitle className="flex items-center gap-2 text-amber-700">
                <TrendingUp className="w-5 h-5" />
                Axes d'amélioration pour progresser 📈
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-600 mb-4 italic">
                💡 Ces suggestions vous aideront à continuer à progresser. Chaque point est une opportunité d'apprendre !
              </p>
              <ul className="space-y-3">
                {displayFeedback.improvements.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-amber-200 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                      <TrendingUp className="w-4 h-4 text-amber-700" />
                    </div>
                    <span className="text-slate-700 leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Advice */}
        {displayFeedback.advice.length > 0 && (
          <Card className="border-2 border-blue-200 shadow-sm bg-gradient-to-br from-blue-50 to-sky-50">
            <CardHeader className="border-b-2 border-blue-200">
              <CardTitle className="flex items-center gap-2 text-blue-700">
                <Lightbulb className="w-5 h-5" />
                Conseils pour continuer à progresser 💡
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <ul className="space-y-3">
                {displayFeedback.advice.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-blue-200 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                      <Lightbulb className="w-4 h-4 text-blue-700" />
                    </div>
                    <span className="text-slate-700 leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Durations */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50/30 border-b-2 border-slate-200">
            <CardTitle className="flex items-center gap-2 text-slate-800">
              <Clock className="w-5 h-5 text-slate-600" />
              Durées de votre session
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-5 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border-2 border-green-200">
                <p className="text-3xl font-bold text-slate-800 mb-1">
                  {displayFeedback.monologue_duration}
                </p>
                <p className="text-sm text-slate-600 font-medium">Monologue</p>
              </div>
              <div className="text-center p-5 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border-2 border-purple-200">
                <p className="text-3xl font-bold text-slate-800 mb-1">
                  {displayFeedback.debat_duration}
                </p>
                <p className="text-sm text-slate-600 font-medium">Débat</p>
              </div>
              <div className="text-center p-5 bg-gradient-to-br from-blue-50 to-sky-50 rounded-xl border-2 border-blue-200">
                <p className="text-3xl font-bold text-slate-800 mb-1">
                  {displayFeedback.total_duration}
                </p>
                <p className="text-sm text-slate-600 font-medium">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Conversation Transcript */}
        {conversationTranscript && conversationTranscript.length > 0 && (
          <Card className="border-2 border-indigo-200 shadow-sm bg-gradient-to-br from-indigo-50 to-violet-50">
            <CardHeader className="border-b-2 border-indigo-200">
              <CardTitle className="flex items-center gap-2 text-indigo-700">
                <MessageCircle className="w-5 h-5" />
                Transcription de la conversation vocale
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                {conversationTranscript.map((entry, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex gap-3",
                      entry.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {entry.role === "assistant" && (
                      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                        <Bot className="w-4 h-4 text-indigo-600" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
                        entry.role === "user"
                          ? "bg-gradient-to-br from-sky-500 to-blue-500 text-white rounded-br-md shadow-sm"
                          : "bg-white border-2 border-indigo-200 rounded-bl-md text-slate-700"
                      )}
                    >
                      {entry.text}
                      {entry.timestamp && (
                        <span className={cn(
                          "block text-xs mt-1 opacity-70",
                          entry.role === "user" ? "text-white/70" : "text-slate-500"
                        )}>
                          {entry.timestamp}
                        </span>
                      )}
                    </div>
                    {entry.role === "user" && (
                      <div className="w-8 h-8 rounded-full bg-sky-500 flex items-center justify-center shrink-0">
                        <User className="w-4 h-4 text-white" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Restart Button */}
        <div className="flex flex-col items-center gap-4 pt-6">
          <Button 
            size="lg" 
            onClick={handleRestart} 
            className="gap-2 bg-gradient-to-r from-sky-500 to-blue-500 hover:from-sky-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl text-base px-8 py-6 rounded-xl"
          >
            <RotateCcw className="w-5 h-5" />
            Recommencer un entraînement
          </Button>
          <Card className="bg-gradient-to-r from-sky-50 to-blue-50 border-2 border-sky-200 max-w-md">
            <div className="p-4 text-center">
              <p className="text-sm text-slate-700">
                <Sparkles className="w-4 h-4 inline mr-1 text-sky-600" />
                Chaque entraînement vous rapproche de votre objectif. Continuez ainsi !
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function ScoreBlock({
  label,
  score,
  max,
  icon,
}: {
  label: string
  score: number
  max: number
  icon: React.ReactNode
}) {
  const percent = (score / max) * 100

  return (
    <div className="text-center p-5 bg-white rounded-xl border-2 border-slate-200 shadow-sm">
      <div className="flex items-center justify-center gap-2 text-slate-600 mb-3">
        {icon}
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="text-3xl font-bold text-slate-800 mb-2">
        {score.toFixed(1)}
        <span className="text-base text-slate-500 font-normal">/{max}</span>
      </p>
      <Progress value={percent} className="h-2 mt-2 bg-slate-100" />
      <p className="text-xs text-slate-500 mt-2">{percent.toFixed(0)}%</p>
    </div>
  )
}
