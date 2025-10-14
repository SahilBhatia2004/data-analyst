import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode, useRef } from 'react';
import { supabase } from '../services/supabase';
import { User as SupabaseUser, Session } from '@supabase/supabase-js';
import { useNavigate } from 'react-router-dom';

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
}

interface AuthResponse {
  user: User | null;
  error: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<AuthResponse>;
  signUp: (email: string, password: string, firstName?: string, lastName?: string) => Promise<AuthResponse>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error: string | null }>;
  signInWithGoogle: () => Promise<AuthResponse>;
  signInWithGithub: () => Promise<AuthResponse>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

const mapUser = (user: SupabaseUser | null): User | null => {
  if (!user) return null;
  
  return {
    id: user.id,
    email: user.email || '',
    first_name: user.user_metadata?.first_name || user.user_metadata?.full_name?.split(' ')[0],
    last_name: user.user_metadata?.last_name || user.user_metadata?.full_name?.split(' ').slice(1).join(' '),
    avatar_url: user.user_metadata?.avatar_url,
  };
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigateRef = useRef<ReturnType<typeof useNavigate> | null>(null);

  // Function to handle auth state changes
  const handleAuthChange = useCallback(async (event: string, session: Session | null) => {
    try {
      const currentUser = session?.user ? mapUser(session.user) : null;
      setUser(currentUser);
      
      // Update loading state
      setLoading(false);
      
      // Get the latest navigation function
      const navigate = navigateRef.current;
      if (!navigate) return;
      
      // Handle different auth events
      switch (event) {
        case 'SIGNED_IN':
          navigate('/app/dashboard');
          break;
        case 'SIGNED_OUT':
          localStorage.removeItem('supabase.auth.token');
          navigate('/login');
          break;
        case 'TOKEN_REFRESHED':
          console.log('Token refreshed');
          break;
        case 'USER_UPDATED':
          console.log('User updated');
          break;
      }
    } catch (error) {
      console.error('Error in auth state change:', error);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Check active session and set the user
    const getInitialSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          await handleAuthChange('SIGNED_IN', session);
        }
      } catch (error) {
        console.error('Error getting session:', error);
      } finally {
        setLoading(false);
      }
    };

    getInitialSession();

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(handleAuthChange);

    return () => {
      subscription?.unsubscribe();
    };
  }, [handleAuthChange]);

  const signIn = async (email: string, password: string) => {
    try {
      setLoading(true);
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password: password.trim(),
      });

      if (error) {
        console.error('Sign in error:', error);
        throw new Error(error.message || 'Failed to sign in');
      }
      
      if (!data.session) {
        throw new Error('No session returned after sign in');
      }
      
      // The auth state change handler will update the user state
      return { user: mapUser(data.user), error: null };
    } catch (error: any) {
      console.error('Sign in error:', error);
      return { 
        user: null, 
        error: error.message || 'An error occurred during sign in. Please try again.' 
      };
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string, firstName?: string, lastName?: string) => {
    try {
      setLoading(true);
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
        password: password.trim(),
        options: {
          data: {
            first_name: firstName?.trim(),
            last_name: lastName?.trim(),
          },
          emailRedirectTo: `${window.location.origin}/app/dashboard`,
        },
      });

      if (error) {
        console.error('Sign up error:', error);
        throw new Error(error.message || 'Failed to sign up');
      }
      
      // Check if email confirmation is required
      if (data.user?.identities?.length === 0) {
        throw new Error('This email is already registered. Please sign in instead.');
      }
      
      return { 
        user: mapUser(data.user), 
        error: null,
        requiresConfirmation: !data.session // If no session, email confirmation is required
      };
    } catch (error: any) {
      console.error('Sign up error:', error);
      return { 
        user: null, 
        error: error.message || 'An error occurred during sign up. Please try again.' 
      };
    } finally {
      setLoading(false);
    }
  };

  const signInWithGoogle = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/app/dashboard`,
          queryParams: {
            access_type: 'offline',
            prompt: 'consent',
          },
        },
      });

      if (error) {
        console.error('Google sign in error:', error);
        throw new Error(error.message || 'Failed to sign in with Google');
      }
      
      // The auth state change handler will handle the redirect
      return { user: null, error: null };
    } catch (error: any) {
      console.error('Google sign in error:', error);
      return { 
        user: null, 
        error: error.message || 'An error occurred during Google sign in. Please try again.' 
      };
    } finally {
      setLoading(false);
    }
  };

  const signInWithGithub = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'github',
        options: {
          redirectTo: `${window.location.origin}/app/dashboard`,
        },
      });

      if (error) {
        console.error('GitHub sign in error:', error);
        throw new Error(error.message || 'Failed to sign in with GitHub');
      }
      
      // The auth state change handler will handle the redirect
      return { user: null, error: null };
    } catch (error: any) {
      console.error('GitHub sign in error:', error);
      return { 
        user: null, 
        error: error.message || 'An error occurred during GitHub sign in. Please try again.' 
      };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signOut();
      
      if (error) {
        console.error('Sign out error:', error);
        throw error;
      }
      
      // Clear any stored data
      localStorage.removeItem('supabase.auth.token');
      setUser(null);
      
      // Redirect to login page using the ref
      if (navigateRef.current) {
        navigateRef.current('/login');
      }
    } catch (error) {
      console.error('Error signing out:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (email: string) => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: `${window.location.origin}/reset-password`,
      });

      if (error) {
        console.error('Password reset error:', error);
        throw new Error(error.message || 'Failed to send password reset email');
      }
      
      return { error: null };
    } catch (error: any) {
      return { error: error.message };
    } finally {
      setLoading(false);
    }
  };

  const value = {
    user,
    loading,
    signIn,
    signUp,
    signOut,
    resetPassword,
    signInWithGoogle,
    signInWithGithub,
  };

  // Navigation component that will be rendered inside Router
  const NavigationHandler = () => {
    const navigate = useNavigate();
    
    useEffect(() => {
      navigateRef.current = navigate;
      return () => {
        navigateRef.current = null;
      };
    }, [navigate]);
    
    return null;
  };

  return (
    <AuthContext.Provider value={value}>
      <NavigationHandler />
      {!loading && children}
    </AuthContext.Provider>
  );
};
