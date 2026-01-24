import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { Button } from "@/components/ui/button"
import { GraduationCap, Mic, Clock, MessageSquare } from "lucide-react"

export default function Welcome() {
  const navigate = useNavigate()
  const { resetExam } = useExam()

  const handleStart = () => {
    resetExam()
    navigate("/setup")
  }

  return (
    <div className="min-h-screen gradient-hero flex flex-col">
      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12 text-white">
        <div className="w-20 h-20 bg-white/10 backdrop-blur rounded-2xl flex items-center justify-center mb-8">
          <GraduationCap className="w-10 h-10" />
        </div>

        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
          EVALORA
        </h1>

        <p className="text-lg md:text-xl text-blue-100 text-center max-w-xl mb-12">
          Simulateur d'examen de production orale
          <br />
          <span className="text-blue-200">Diplome Universitaire FLE - Sorbonne Abu Dhabi</span>
        </p>

        <Button
          size="xl"
          onClick={handleStart}
          className="bg-white text-slate-900 hover:bg-blue-50 shadow-lg hover:shadow-xl transition-all"
        >
          Commencer la simulation
        </Button>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-3xl w-full">
          <FeatureCard
            icon={<Mic className="w-5 h-5" />}
            title="Avatars IA"
            description="4 examinateurs virtuels avec personnalites distinctes"
          />
          <FeatureCard
            icon={<Clock className="w-5 h-5" />}
            title="Timer intelligent"
            description="Gestion du temps avec alertes visuelles"
          />
          <FeatureCard
            icon={<MessageSquare className="w-5 h-5" />}
            title="Feedback detaille"
            description="Evaluation complete avec conseils personnalises"
          />
        </div>
      </div>

      {/* Footer */}
      <footer className="py-6 text-center text-blue-200/60 text-sm">
        <p>Sorbonne Universite Abu Dhabi</p>
        <p>Niveau A2+ / B1</p>
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="bg-white/5 backdrop-blur-sm rounded-xl p-5 border border-white/10">
      <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center mb-3">
        {icon}
      </div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-blue-200/80">{description}</p>
    </div>
  )
}
