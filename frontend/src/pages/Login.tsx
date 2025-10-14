import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import { FaEye, FaEyeSlash, FaGoogle, FaGithub } from 'react-icons/fa';

const Login: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [forgotPassword, setForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSent, setResetSent] = useState(false);

  const { 
    user,
    loading: authLoading, 
    signIn, 
    signUp, 
    signInWithGoogle, 
    signInWithGithub, 
    resetPassword 
  } = useAuth();
  
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || '/app/dashboard';

  // Redirect if user is already logged in
  useEffect(() => {
    if (user) {
      navigate(from, { replace: true });
    }
  }, [user, navigate, from]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (forgotPassword) {
      if (!resetEmail) {
        toast.error('Please enter your email address');
        return;
      }

      setLoading(true);
      try {
        const { error } = await resetPassword(resetEmail);
        if (error) {
          toast.error(error);
        } else {
          setResetSent(true);
          toast.success('Password reset email sent! Check your inbox.');
        }
      } catch (error) {
        toast.error('Failed to send password reset email');
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!email || !password) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (!isLogin && (!firstName || !lastName)) {
      toast.error('Please fill in your name');
      return;
    }

    setLoading(true);

    try {
      let result;

      if (isLogin) {
        result = await signIn(email, password);
      } else {
        // For signup, we'll use Supabase's signUp method
        const signUpResult = await signUp(email, password, firstName, lastName);
        
        if (signUpResult.error) {
          throw new Error(signUpResult.error);
        }
        
        toast.success('Account created successfully! Please check your email to verify your account.');
        return; // Don't proceed to login automatically
      }

      if (result?.error) {
        throw new Error(result.error);
      }
      
      toast.success(isLogin ? 'Welcome back!' : 'Account created successfully!');
      navigate(from, { replace: true });
    } catch (error: any) {
      console.error('Authentication error:', error);
      toast.error(error.message || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSocialLogin = async (provider: 'google' | 'github') => {
    try {
      setLoading(true);
      const result = provider === 'google' 
        ? await signInWithGoogle() 
        : await signInWithGithub();

      if (result.error) {
        throw new Error(result.error);
      }
      
      toast.success(`Signed in with ${provider.charAt(0).toUpperCase() + provider.slice(1)}!`);
      navigate(from, { replace: true });
    } catch (error: any) {
      console.error('Social login error:', error);
      toast.error(error.message || `Failed to sign in with ${provider}`);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">AI Data Analyst</span>
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </p>
        </div>

        <div className="panel p-8">
          {forgotPassword ? (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Reset Password</h3>
              {resetSent ? (
                <div className="text-center">
                  <p className="text-green-600 mb-4">Password reset email sent! Check your inbox.</p>
                  <button
                    type="button"
                    onClick={() => {
                      setForgotPassword(false);
                      setResetSent(false);
                    }}
                    className="btn-primary w-full"
                  >
                    Back to Login
                  </button>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-600 mb-4">
                    Enter your email address and we'll send you a link to reset your password.
                  </p>
                  <div>
                    <label htmlFor="reset-email" className="block text-sm font-medium text-gray-700">
                      Email Address
                    </label>
                    <input
                      id="reset-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      className="input-field mt-1"
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => setForgotPassword(false)}
                      className="text-sm text-blue-600 hover:text-blue-500"
                    >
                      Back to Login
                    </button>
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={loading || authLoading}
                      className="btn-primary"
                    >
                      {loading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <form className="space-y-6" onSubmit={handleSubmit}>
            {!isLogin && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
                    First Name
                  </label>
                  <input
                    id="firstName"
                    name="firstName"
                    type="text"
                    required={!isLogin}
                    className="input-field mt-1"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
                    Last Name
                  </label>
                  <input
                    id="lastName"
                    name="lastName"
                    type="text"
                    required={!isLogin}
                    className="input-field mt-1"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                  />
                </div>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="input-field"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <div>
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Password
                  </label>
                  <div className="text-sm">
                    <button
                      type="button"
                      onClick={() => setForgotPassword(true)}
                      className="font-medium text-blue-600 hover:text-blue-500"
                    >
                      Forgot password?
                    </button>
                  </div>
                </div>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete={isLogin ? 'current-password' : 'new-password'}
                    required
                    className="input-field pr-10"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <button
                      type="button"
                      className="text-gray-500 hover:text-gray-700"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <FaEyeSlash /> : <FaEye />}
                    </button>
                  </div>
                </div>
              </div>
              {!isLogin && (
                <p className="mt-1 text-sm text-gray-600">
                  Password must be at least 6 characters long
                </p>
              )}
            </div>

              <div className="space-y-4">
              <button
                type="submit"
                disabled={loading || authLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading || authLoading ? 'Processing...' : isLogin ? 'Sign in' : 'Create account'}
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-white text-gray-500">Or continue with</span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => handleSocialLogin('google')}
                  disabled={loading || authLoading}
                  className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  <FaGoogle className="h-5 w-5 text-red-500" />
                </button>
                <button
                  type="button"
                  onClick={() => handleSocialLogin('github')}
                  disabled={loading || authLoading}
                  className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  <FaGithub className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="text-sm text-center">
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setForgotPassword(false);
                }}
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
              </button>
            </div>
          </form>
          )}
        </div>

        <div className="text-center">
          <p className="text-sm text-gray-500">
            Powered by AI
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
