// Service d'authentification pour Evalora

import api from './api';
import { User, LoginCredentials, RegisterData, AuthTokens } from '@/types/auth';

const TOKEN_KEY = 'evalora_access_token';
const REFRESH_KEY = 'evalora_refresh_token';

// Gestion du stockage des tokens
export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setStoredTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearStoredTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// API calls
export async function login(credentials: LoginCredentials): Promise<AuthTokens> {
  const response = await api.post('/auth/login', credentials);
  const tokens = response.data;
  setStoredTokens(tokens);
  return tokens;
}

export async function register(data: RegisterData): Promise<User> {
  const response = await api.post('/auth/register', data);
  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get('/auth/me');
  return response.data;
}

export async function refreshTokens(): Promise<AuthTokens> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
  const tokens = response.data;
  setStoredTokens(tokens);
  return tokens;
}

export function logout(): void {
  clearStoredTokens();
}
