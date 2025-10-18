"""
Authentication service for Supabase Auth integration
"""

import jwt
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client

class AuthService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.jwt_secret = os.getenv("JWT_SECRET", "your-jwt-secret")
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        try:
            # For Supabase, you can verify the token using their method
            # or decode it manually if needed
            response = self.supabase.auth.get_user(token)
            
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "role": response.user.user_metadata.get("role", "user"),
                    "metadata": response.user.user_metadata
                }
            else:
                raise Exception("Invalid token")
                
        except Exception as e:
            print(f"Error verifying token: {e}")
            raise Exception("Invalid authentication credentials")
    
    async def is_agent(self, user_id: str) -> bool:
        """Check if user has agent role"""
        try:
            response = self.supabase.auth.admin.get_user_by_id(user_id)
            if response.user:
                role = response.user.user_metadata.get("role", "user")
                return role in ["agent", "admin"]
            return False
            
        except Exception as e:
            print(f"Error checking agent role: {e}")
            return False
    
    async def is_admin(self, user_id: str) -> bool:
        """Check if user has admin role"""
        try:
            response = self.supabase.auth.admin.get_user_by_id(user_id)
            if response.user:
                role = response.user.user_metadata.get("role", "user")
                return role == "admin"
            return False
            
        except Exception as e:
            print(f"Error checking admin role: {e}")
            return False
    
    async def create_user(
        self, 
        email: str, 
        password: str, 
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new user"""
        try:
            response = self.supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "user_metadata": {
                    "role": role,
                    **(metadata or {})
                }
            })
            
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "role": role,
                    "created_at": response.user.created_at
                }
            else:
                raise Exception("Failed to create user")
                
        except Exception as e:
            print(f"Error creating user: {e}")
            raise Exception(f"Failed to create user: {str(e)}")
    
    async def update_user_role(self, user_id: str, role: str) -> bool:
        """Update user role"""
        try:
            response = self.supabase.auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": {"role": role}}
            )
            
            return response.user is not None
            
        except Exception as e:
            print(f"Error updating user role: {e}")
            return False
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            response = self.supabase.auth.admin.get_user_by_id(user_id)
            
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "role": response.user.user_metadata.get("role", "user"),
                    "metadata": response.user.user_metadata,
                    "created_at": response.user.created_at,
                    "last_sign_in_at": response.user.last_sign_in_at
                }
            return None
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def list_users(
        self, 
        page: int = 1, 
        per_page: int = 50
    ) -> Dict[str, Any]:
        """List users with pagination"""
        try:
            # Note: This is a simplified implementation
            # In practice, you might need to implement custom pagination
            response = self.supabase.auth.admin.list_users()
            
            users = []
            for user in response.users:
                users.append({
                    "id": user.id,
                    "email": user.email,
                    "role": user.user_metadata.get("role", "user"),
                    "created_at": user.created_at,
                    "last_sign_in_at": user.last_sign_in_at
                })
            
            return {
                "users": users,
                "total": len(users),
                "page": page,
                "per_page": per_page
            }
            
        except Exception as e:
            print(f"Error listing users: {e}")
            return {"users": [], "total": 0, "page": page, "per_page": per_page}
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            response = self.supabase.auth.admin.delete_user(user_id)
            return True
            
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    async def reset_password(self, email: str) -> bool:
        """Send password reset email"""
        try:
            response = self.supabase.auth.reset_password_email(email)
            return True
            
        except Exception as e:
            print(f"Error sending password reset: {e}")
            return False
    
    async def verify_email(self, token: str) -> bool:
        """Verify email with token"""
        try:
            response = self.supabase.auth.verify_otp({
                "token": token,
                "type": "email"
            })
            return response.user is not None
            
        except Exception as e:
            print(f"Error verifying email: {e}")
            return False
    
    def generate_api_key(self, user_id: str, expires_in_days: int = 30) -> str:
        """Generate API key for user"""
        try:
            payload = {
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(days=expires_in_days),
                "type": "api_key"
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            return token
            
        except Exception as e:
            print(f"Error generating API key: {e}")
            raise Exception("Failed to generate API key")
    
    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key"""
        try:
            payload = jwt.decode(api_key, self.jwt_secret, algorithms=["HS256"])
            
            if payload.get("type") == "api_key":
                user_id = payload.get("user_id")
                if user_id:
                    user = await self.get_user_by_id(user_id)
                    return user
            
            return None
            
        except jwt.ExpiredSignatureError:
            return None
        except Exception as e:
            print(f"Error verifying API key: {e}")
            return None
