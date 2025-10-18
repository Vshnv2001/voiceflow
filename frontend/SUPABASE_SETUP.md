# Supabase Authentication Setup

This guide will help you set up Supabase authentication for your VoiceFlow AI application.

## Prerequisites

1. A Supabase account (sign up at [supabase.com](https://supabase.com))
2. A new Supabase project created

## Setup Steps

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Choose your organization
4. Enter project details:
   - Name: `voiceflow-ai` (or your preferred name)
   - Database Password: Generate a strong password
   - Region: Choose the closest to your users
5. Click "Create new project"

### 2. Get Your Project Credentials

1. In your Supabase dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (starts with `https://`)
   - **Project API Key** (anon/public key)

### 3. Configure Environment Variables

1. Open `.env.local` in your project root
2. Replace the placeholder values with your actual Supabase credentials:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. Configure Authentication Providers (Optional)

#### Google OAuth Setup

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Enable **Google** provider
3. You'll need to:
   - Create a Google Cloud Console project
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add your domain to authorized origins
   - Copy Client ID and Client Secret to Supabase

#### GitHub OAuth Setup

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Enable **GitHub** provider
3. You'll need to:
   - Create a GitHub OAuth App
   - Set Authorization callback URL to: `https://your-project-id.supabase.co/auth/v1/callback`
   - Copy Client ID and Client Secret to Supabase

### 5. Configure Email Templates (Optional)

1. Go to **Authentication** → **Email Templates**
2. Customize the email templates for:
   - Confirm signup
   - Reset password
   - Magic link
   - Change email address

### 6. Set Up Email Settings

1. Go to **Authentication** → **Settings**
2. Configure your site URL (e.g., `http://localhost:3000` for development)
3. Add redirect URLs for OAuth providers:
   - `http://localhost:3000/dashboard` (development)
   - `https://yourdomain.com/dashboard` (production)

### 7. Test the Integration

1. Start your development server:
   ```bash
   npm run dev
   ```

2. Navigate to `http://localhost:3000/login`

3. Test the following:
   - Email/password sign up
   - Email/password sign in
   - OAuth sign in (if configured)
   - Sign out functionality

## Features Included

✅ **Email/Password Authentication**
- User registration
- User login
- Password validation
- Error handling

✅ **OAuth Integration**
- Google OAuth
- GitHub OAuth
- Automatic redirect after authentication

✅ **User State Management**
- React Context for global auth state
- Automatic session persistence
- Loading states

✅ **Protected Routes**
- Dashboard requires authentication
- Automatic redirect to login if not authenticated
- User information display

✅ **UI/UX Features**
- Loading states during authentication
- Error messages for failed attempts
- Remember me functionality
- Responsive design

## File Structure

```
src/
├── contexts/
│   └── AuthContext.tsx          # Authentication context and hooks
├── lib/
│   └── supabase.ts             # Supabase client configuration
├── app/
│   ├── layout.tsx              # Root layout with AuthProvider
│   ├── login/
│   │   └── page.tsx            # Login page with Supabase integration
│   └── dashboard/
│       └── page.tsx            # Protected dashboard page
└── .env.local                  # Environment variables
```

## Usage Examples

### Using Authentication in Components

```tsx
import { useAuth } from '@/contexts/AuthContext'

function MyComponent() {
  const { user, signOut, loading } = useAuth()
  
  if (loading) return <div>Loading...</div>
  if (!user) return <div>Please log in</div>
  
  return (
    <div>
      <p>Welcome, {user.email}!</p>
      <button onClick={signOut}>Sign Out</button>
    </div>
  )
}
```

### Checking Authentication Status

```tsx
const { user, loading } = useAuth()

useEffect(() => {
  if (!loading && !user) {
    router.push('/login')
  }
}, [user, loading, router])
```

## Troubleshooting

### Common Issues

1. **"Invalid API key" error**
   - Check that your environment variables are correctly set
   - Ensure you're using the anon/public key, not the service role key

2. **OAuth redirect issues**
   - Verify your redirect URLs are correctly configured in Supabase
   - Check that your site URL matches your development/production URL

3. **Email not sending**
   - Check your email settings in Supabase
   - Verify your site URL is configured correctly
   - For development, emails might go to spam

4. **CORS errors**
   - Ensure your domain is added to the allowed origins in Supabase
   - Check that you're using the correct project URL

### Getting Help

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Discord Community](https://discord.supabase.com)
- [Next.js Documentation](https://nextjs.org/docs)

## Security Notes

- Never commit your `.env.local` file to version control
- Use environment variables for all sensitive configuration
- Regularly rotate your API keys
- Enable Row Level Security (RLS) for your database tables
- Use HTTPS in production
