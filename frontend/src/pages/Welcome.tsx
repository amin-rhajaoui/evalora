import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { GraduationCap, Mic, Clock, MessageSquare, Heart, Shield, Sparkles, LogOut, User } from "lucide-react"

export default function Welcome() {
  const navigate = useNavigate()
  const { resetExam } = useExam()
  const { user, logout } = useAuth()

  const handleStart = () => {
    resetExam()
    navigate("/setup")
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen gradient-hero flex flex-col">
      {/* Header avec info utilisateur */}
      <header className="absolute top-0 right-0 p-4 flex items-center gap-3">
        {user && (
          <>
            <div className="flex items-center gap-2 text-sm text-slate-600 bg-white/80 px-3 py-2 rounded-lg">
              <User className="w-4 h-4" />
              <span>{user.full_name}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="bg-white/80 hover:bg-white"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Deconnexion
            </Button>
          </>
        )}
      </header>

      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        {/* Logo avec animation douce */}
        <div className="w-24 h-24 bg-gradient-to-br from-sky-400 to-blue-500 rounded-3xl flex items-center justify-center mb-6 shadow-lg animate-float">
          <GraduationCap className="w-12 h-12 text-white" />
        </div>

        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-3 text-slate-800">
          EVALORA
        </h1>

        <p className="text-xl md:text-2xl text-slate-700 text-center max-w-2xl mb-4 font-medium">
          Bienvenue dans votre espace d'entraînement
        </p>
        
        <p className="text-base md:text-lg text-slate-600 text-center max-w-xl mb-8">
          Simulateur d'examen de production orale
          <br />
          <span className="text-slate-500 text-sm">Diplôme Universitaire FLE - Sorbonne Abu Dhabi</span>
        </p>

        {/* Message rassurant */}
        <Card className="max-w-xl w-full mb-8 bg-white/80 backdrop-blur-sm border-2 border-sky-200 shadow-md">
          <div className="p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-3">
              <Heart className="w-5 h-5 text-pink-400" />
              <p className="text-lg font-semibold text-slate-800">
                Un environnement bienveillant pour progresser
              </p>
            </div>
            <p className="text-sm text-slate-600">
              Prenez votre temps, respirez, et faites de votre mieux. 
              C'est un espace d'apprentissage, pas un test stressant.
            </p>
          </div>
        </Card>

        <Button
          size="xl"
          onClick={handleStart}
          className="bg-gradient-to-r from-sky-500 to-blue-500 text-white hover:from-sky-600 hover:to-blue-600 shadow-lg hover:shadow-xl transition-all text-lg px-8 py-6 rounded-xl"
        >
          <Sparkles className="w-5 h-5 mr-2" />
          Commencer l'entraînement
        </Button>

        {/* Features avec design plus doux */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12 max-w-4xl w-full">
          <FeatureCard
            icon={<Mic className="w-6 h-6" />}
            title="Examinateurs bienveillants"
            description="4 examinateurs virtuels compréhensifs qui vous guident avec bienveillance"
            color="from-blue-400 to-cyan-400"
          />
          <FeatureCard
            icon={<Clock className="w-6 h-6" />}
            title="Gestion du temps"
            description="Un timer visuel pour vous aider à gérer votre temps sereinement"
            color="from-green-400 to-emerald-400"
          />
          <FeatureCard
            icon={<MessageSquare className="w-6 h-6" />}
            title="Feedback constructif"
            description="Des conseils personnalisés pour progresser à votre rythme"
            color="from-purple-400 to-pink-400"
          />
        </div>

        {/* Encadré rassurant */}
        <Card className="max-w-2xl w-full mt-8 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200">
          <div className="p-6">
            <div className="flex items-start gap-3">
              <Shield className="w-6 h-6 text-green-600 mt-1 shrink-0" />
              <div>
                <h3 className="font-semibold text-slate-800 mb-2">Rappelez-vous</h3>
                <ul className="text-sm text-slate-700 space-y-1">
                  <li>• C'est un entraînement, pas un examen officiel</li>
                  <li>• Vous pouvez recommencer autant de fois que nécessaire</li>
                  <li>• Chaque erreur est une opportunité d'apprendre</li>
                  <li>• Nous sommes là pour vous accompagner dans votre progression</li>
                </ul>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Footer */}
      <footer className="py-6 text-center text-slate-500 text-sm bg-white/50">
        <p className="font-medium">Sorbonne Université Abu Dhabi</p>
        <p className="text-xs mt-1">Niveau A2+ / B1 - Espace d'entraînement</p>
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
  color = "from-sky-400 to-blue-400",
}: {
  icon: React.ReactNode
  title: string
  description: string
  color?: string
}) {
  return (
    <Card className="bg-white/90 backdrop-blur-sm border-2 border-slate-200 hover:border-sky-300 transition-all shadow-sm hover:shadow-md">
      <div className="p-5">
        <div className={`w-12 h-12 bg-gradient-to-br ${color} rounded-xl flex items-center justify-center mb-4 text-white shadow-sm`}>
          {icon}
        </div>
        <h3 className="font-semibold mb-2 text-slate-800">{title}</h3>
        <p className="text-sm text-slate-600 leading-relaxed">{description}</p>
      </div>
    </Card>
  )
}
