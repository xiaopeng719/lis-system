import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '../services/api';

interface User {
  id: number;
  username: string;
  real_name: string;
  role: string;
  department: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  permissions: string[];
  roleLabel: string;
  hasPermission: (perm: string) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const roleLabels: Record<string, string> = {
  ADMIN: '管理员',
  DIRECTOR: '科室主任',
  REVIEWER: '审核员',
  TECHNICIAN: '检验师',
};

const AuthContext = createContext<AuthContextType>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('lis_token'));
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPermissions = async () => {
    try {
      const res = await authApi.permissions();
      setPermissions(res.data.permissions || []);
    } catch {
      setPermissions([]);
    }
  };

  useEffect(() => {
    if (token) {
      authApi.me()
        .then((res) => {
          setUser(res.data);
          fetchPermissions();
        })
        .catch(() => {
          localStorage.removeItem('lis_token');
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await authApi.login({ username, password });
    const newToken = res.data.access_token;
    localStorage.setItem('lis_token', newToken);
    setToken(newToken);
    const userRes = await authApi.me();
    setUser(userRes.data);
    await fetchPermissions();
  };

  const logout = () => {
    localStorage.removeItem('lis_token');
    setToken(null);
    setUser(null);
    setPermissions([]);
  };

  const hasPermission = (perm: string) => permissions.includes(perm);
  const roleLabel = roleLabels[user?.role || ''] || user?.role || '';

  return (
    <AuthContext.Provider value={{
      user, token, permissions, roleLabel, hasPermission, login, logout, loading
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
