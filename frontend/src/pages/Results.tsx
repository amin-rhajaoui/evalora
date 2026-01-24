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
} from "lucide-react"

export default function Results() {
  const navigate = useNavigate()
  const { feedback, selectedAvatar, resetExam } = useExam()

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
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900">Resultats</h1>
          {selectedAvatar && (
            <p className="text-muted-foreground mt-1">
              Examinateur: {selectedAvatar.name}
            </p>
          )}
        </div>

        {/* Score Card */}
        <Card className="overflow-hidden">
          <div className={cn(
            "p-8 text-center text-white",
            displayFeedback.passed
              ? "bg-gradient-to-br from-green-500 to-emerald-600"
              : "bg-gradient-to-br from-amber-500 to-orange-600"
          )}>
            <div className="flex items-center justify-center gap-2 mb-4">
              {displayFeedback.passed ? (
                <CheckCircle2 className="w-8 h-8" />
              ) : (
                <AlertCircle className="w-8 h-8" />
              )}
              <Badge variant="secondary" className="text-lg px-4 py-1">
                {displayFeedback.grade_letter}
              </Badge>
            </div>

            <div className="text-6xl font-bold mb-2">
              {displayFeedback.total_score.toFixed(1)}
              <span className="text-2xl opacity-80">/{displayFeedback.max_score}</span>
            </div>

            <p className="text-lg opacity-90">
              {displayFeedback.passed ? "Felicitations, vous avez reussi !" : "Continuez vos efforts !"}
            </p>
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
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-500" />
              Resume
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-foreground leading-relaxed">
              {displayFeedback.summary}
            </p>
          </CardContent>
        </Card>

        {/* Strengths */}
        {displayFeedback.strengths.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-600">
                <CheckCircle2 className="w-5 h-5" />
                Points forts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {displayFeedback.strengths.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center shrink-0 mt-0.5">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    </div>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Improvements */}
        {displayFeedback.improvements.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-amber-600">
                <TrendingUp className="w-5 h-5" />
                Axes d'amelioration
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {displayFeedback.improvements.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center shrink-0 mt-0.5">
                      <TrendingUp className="w-4 h-4 text-amber-600" />
                    </div>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Advice */}
        {displayFeedback.advice.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-blue-600">
                <Lightbulb className="w-5 h-5" />
                Conseils pour progresser
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {displayFeedback.advice.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-0.5">
                      <Lightbulb className="w-4 h-4 text-blue-600" />
                    </div>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Durations */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-muted-foreground" />
              Durees
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-foreground">
                  {displayFeedback.monologue_duration}
                </p>
                <p className="text-sm text-muted-foreground">Monologue</p>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-foreground">
                  {displayFeedback.debat_duration}
                </p>
                <p className="text-sm text-muted-foreground">Debat</p>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-foreground">
                  {displayFeedback.total_duration}
                </p>
                <p className="text-sm text-muted-foreground">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Restart Button */}
        <div className="flex justify-center pt-4">
          <Button size="lg" onClick={handleRestart} className="gap-2">
            <RotateCcw className="w-5 h-5" />
            Recommencer une simulation
          </Button>
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
    <div className="text-center p-4 bg-slate-50 rounded-xl">
      <div className="flex items-center justify-center gap-1 text-muted-foreground mb-2">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className="text-2xl font-bold text-foreground">
        {score.toFixed(1)}
        <span className="text-sm text-muted-foreground font-normal">/{max}</span>
      </p>
      <Progress value={percent} className="h-1.5 mt-2" />
    </div>
  )
}
