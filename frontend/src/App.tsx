import { BrowserRouter, Routes, Route } from "react-router-dom"
import { ExamProvider } from "@/contexts/ExamContext"
import { TooltipProvider } from "@/components/ui/tooltip"
import Welcome from "@/pages/Welcome"
import Setup from "@/pages/Setup"
import DocumentSelect from "@/pages/DocumentSelect"
import Exam from "@/pages/Exam"
import Results from "@/pages/Results"

export default function App() {
  return (
    <BrowserRouter>
      <TooltipProvider>
        <ExamProvider>
          <div className="min-h-screen bg-background font-sans antialiased">
            <Routes>
              <Route path="/" element={<Welcome />} />
              <Route path="/setup" element={<Setup />} />
              <Route path="/documents" element={<DocumentSelect />} />
              <Route path="/exam" element={<Exam />} />
              <Route path="/results" element={<Results />} />
            </Routes>
          </div>
        </ExamProvider>
      </TooltipProvider>
    </BrowserRouter>
  )
}
