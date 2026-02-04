import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AuthProvider } from "@/contexts/AuthContext"
import { ExamProvider } from "@/contexts/ExamContext"
import { TooltipProvider } from "@/components/ui/tooltip"
import ProtectedRoute from "@/components/ProtectedRoute"
import Welcome from "@/pages/Welcome"
import Setup from "@/pages/Setup"
import DocumentSelect from "@/pages/DocumentSelect"
import Exam from "@/pages/Exam"
import Results from "@/pages/Results"
import Login from "@/pages/Login"
import Register from "@/pages/Register"

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <TooltipProvider>
          <ExamProvider>
            <div className="min-h-screen bg-background font-sans antialiased">
              <Routes>
                {/* Routes publiques */}
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Routes protegees */}
                <Route path="/" element={
                  <ProtectedRoute><Welcome /></ProtectedRoute>
                } />
                <Route path="/setup" element={
                  <ProtectedRoute><Setup /></ProtectedRoute>
                } />
                <Route path="/documents" element={
                  <ProtectedRoute><DocumentSelect /></ProtectedRoute>
                } />
                <Route path="/exam" element={
                  <ProtectedRoute><Exam /></ProtectedRoute>
                } />
                <Route path="/results" element={
                  <ProtectedRoute><Results /></ProtectedRoute>
                } />
              </Routes>
            </div>
          </ExamProvider>
        </TooltipProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
