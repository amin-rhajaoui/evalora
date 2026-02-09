import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Toaster } from "sonner"
import { AuthProvider } from "@/contexts/AuthContext"
import { ExamProvider } from "@/contexts/ExamContext"
import { TooltipProvider } from "@/components/ui/tooltip"
import ErrorBoundary from "@/components/ErrorBoundary"
import ProtectedRoute from "@/components/ProtectedRoute"
import Welcome from "@/pages/Welcome"
import Setup from "@/pages/Setup"
import DocumentSelect from "@/pages/DocumentSelect"
import SystemCheck from "@/pages/SystemCheck"
import MicTest from "@/pages/MicTest"
import Exam from "@/pages/Exam"
import Results from "@/pages/Results"
import Login from "@/pages/Login"
import Register from "@/pages/Register"

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <TooltipProvider>
            <ExamProvider>
              <div className="min-h-screen bg-background font-sans antialiased">
                <Toaster position="top-right" richColors closeButton />
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
                  <Route path="/system-check" element={
                    <ProtectedRoute><SystemCheck /></ProtectedRoute>
                  } />
                  <Route path="/mic-test" element={
                    <ProtectedRoute><MicTest /></ProtectedRoute>
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
    </ErrorBoundary>
  )
}
