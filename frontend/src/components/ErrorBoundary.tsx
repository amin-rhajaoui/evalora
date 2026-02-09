import { Component, ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { AlertTriangle, RotateCcw } from "lucide-react"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  handleGoHome = () => {
    window.location.href = "/"
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 flex items-center justify-center px-4">
          <Card className="max-w-md w-full border-2 border-red-200 shadow-lg">
            <CardContent className="p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">
                Une erreur est survenue
              </h2>
              <p className="text-sm text-slate-600 mb-6">
                L'application a rencontre un probleme inattendu. Veuillez reessayer.
              </p>
              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={this.handleReset}>
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reessayer
                </Button>
                <Button onClick={this.handleGoHome} className="bg-sky-500 hover:bg-sky-600 text-white">
                  Retour a l'accueil
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
