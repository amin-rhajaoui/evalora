// Types pour Evalora

export type ExamPhase = 'consignes' | 'monologue' | 'debat' | 'feedback' | 'results';

export type StudentLevel = 'A2+' | 'B1';

export interface Avatar {
  id: string;
  name: string;
  gender: 'homme' | 'femme';
  age: number;
  register: 'tutoiement' | 'vouvoiement';
  personality: string;
  role?: string;
  behavior?: string;
  feedback_tone: string;
  placeholder_image: string;
}

export interface Document {
  id: string;
  title: string;
  theme: string;
  author?: string;
  source?: string;
  date?: string;
  text: string;
  image_url: string;
  keywords: string[];
  debate_questions?: string[];
}

export interface Session {
  id: string;
  student_name: string;
  level: StudentLevel;
  avatar_id?: string;
  avatar_info?: Avatar;
  document_id?: string;
  current_phase: ExamPhase;
  livekit_token?: string;
  livekit_url?: string;
  created_at: string;
}

export interface CriterionScore {
  criterion: string;
  score: number;
  max_score: number;
  comment?: string;
}

export interface Feedback {
  session_id: string;
  student_name: string;
  avatar_name?: string;
  total_score: number;
  max_score: number;
  grade_letter: string;
  passed: boolean;
  monologue_score: number;
  monologue_max: number;
  debat_score: number;
  debat_max: number;
  general_score: number;
  general_max: number;
  summary: string;
  strengths: string[];
  improvements: string[];
  advice: string[];
  detailed_scores: {
    monologue: CriterionScore[];
    debat: CriterionScore[];
    general: CriterionScore[];
  };
  monologue_duration: string;
  debat_duration: string;
  total_duration: string;
}

export interface TavusSession {
  conversation_id: string;
  conversation_url: string;
  status: string;
}

// Types pour la transcription de conversation vocale
export interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
  timestamp?: string;
  phase?: string; // consignes | monologue | debat
}

export interface Transcription {
  session_id: string;
  transcript: TranscriptEntry[];
  created_at: string;
}

