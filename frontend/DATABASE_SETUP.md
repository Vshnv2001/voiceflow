# Database Setup for VoiceFlow AI

This guide will help you set up the `reps` table in your Supabase database to store customer service representative information.

## Prerequisites

1. A Supabase project with authentication already set up
2. Access to your Supabase dashboard

## Setup Steps

### 1. Create the Reps Table

1. Go to your Supabase dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the contents of `supabase-schema.sql` into the SQL editor
4. Click **Run** to execute the SQL

This will create:
- The `reps` table with all necessary columns
- Row Level Security (RLS) policies
- Indexes for better performance
- Triggers for automatic timestamp updates

### 2. Verify the Setup

After running the SQL, you should see:
- A new `reps` table in your **Table Editor**
- The table should have the following columns:
  - `id` (UUID, Primary Key)
  - `user_id` (UUID, Foreign Key to auth.users)
  - `display_name` (Text)
  - `organization` (Text)
  - `email` (Text)
  - `phone` (Text, Optional)
  - `avatar_url` (Text, Optional)
  - `status` (Text, Default: 'active')
  - `calls_handled` (Integer, Default: 0)
  - `avg_response_time` (Text, Default: '0s')
  - `satisfaction` (Integer, Default: 0)
  - `current_calls` (Integer, Default: 0)
  - `created_at` (Timestamp)
  - `updated_at` (Timestamp)

### 3. Test the Integration

1. Start your development server: `npm run dev`
2. Navigate to the signup page and create a new account
3. Check the `reps` table in Supabase to verify the data was inserted
4. Navigate to the reps page to see the new representative listed

## Security Features

The setup includes:
- **Row Level Security (RLS)**: Ensures users can only access appropriate data
- **Policies**: 
  - Users can read all reps (for the reps page)
  - Users can only insert/update their own rep record
- **Foreign Key Constraints**: Links reps to auth.users with cascade delete

## Troubleshooting

### Common Issues

1. **Permission Denied**: Make sure RLS policies are correctly set up
2. **Foreign Key Violation**: Ensure the user exists in auth.users before inserting into reps
3. **Missing Columns**: Verify all columns were created correctly

### Getting Help

- Check the Supabase documentation for RLS and policies
- Verify your environment variables are correctly set
- Check the browser console for any JavaScript errors
