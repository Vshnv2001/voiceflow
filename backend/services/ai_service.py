"""
AI service for generating responses using OpenAI/LLM providers
"""

import asyncio
import os
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from openai import AsyncOpenAI

class AIService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.default_model = "gpt-4o-mini"  # More cost-effective than gpt-4
        self.max_tokens = 1000
        self.temperature = 0.7
        
    async def generate_response(
        self, 
        user_message: str, 
        session_id: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate AI response using OpenAI API"""
        try:
            model = model or self.default_model
            temperature = temperature or self.temperature
            max_tokens = max_tokens or self.max_tokens
            
            # Get conversation context
            context = await self._get_conversation_context(session_id)
            
            # Build the prompt
            prompt = self._build_prompt(user_message, context)
            
            # Use OpenAI client
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
                        
        except Exception as e:
            print(f"Error generating AI response: {e}")
            # Return a fallback response
            return "I apologize, but I'm having trouble processing your request right now. Please try again or contact support if the issue persists."
    
    async def _get_conversation_context(self, session_id: str) -> List[Dict[str, str]]:
        """Get recent conversation context for better responses"""
        # This would typically query your database for recent messages
        # For now, return empty context
        return []
    
    def _build_prompt(self, user_message: str, context: List[Dict[str, str]]) -> str:
        """Build the prompt for the AI model"""
        prompt = f"Customer message: {user_message}\n\n"
        
        if context:
            prompt += "Previous conversation context:\n"
            for msg in context[-5:]:  # Last 5 messages
                prompt += f"{msg['role']}: {msg['content']}\n"
        
        prompt += "\nPlease provide a helpful, professional response to the customer's message."
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI model"""
        return """You are a helpful customer service representative for VoiceFlow AI. 
        
Your role is to:
1. Provide helpful, accurate, and professional responses to customer inquiries
2. Be empathetic and understanding of customer concerns
3. Keep responses concise but informative
4. Ask clarifying questions when needed
5. Escalate complex issues to human agents when appropriate

Guidelines:
- Always be polite and professional
- Use clear, simple language
- Provide specific, actionable advice when possible
- If you don't know something, admit it and offer to find out
- Keep responses under 200 words unless the topic requires more detail
- End responses with a question to encourage further engagement when appropriate

Remember: You're representing a voice AI company, so be knowledgeable about AI, voice technology, and customer service best practices."""
    
    async def generate_response_with_streaming(
        self, 
        user_message: str, 
        session_id: str,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate AI response with streaming for real-time display"""
        try:
            model = model or self.default_model
            context = await self._get_conversation_context(session_id)
            prompt = self._build_prompt(user_message, context)
            
            # Use OpenAI streaming
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                        
        except Exception as e:
            yield f"Error generating response: {str(e)}"
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of customer message"""
        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of the following customer message. Respond with a JSON object containing: sentiment (positive/negative/neutral), confidence (0-1), and urgency (low/medium/high)."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            response_text = response.choices[0].message.content
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"sentiment": "neutral", "confidence": 0.5, "urgency": "medium"}
                        
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "urgency": "medium"}
    
    async def suggest_response_variations(self, user_message: str) -> List[str]:
        """Generate multiple response variations for agent review"""
        try:
            variations = []
            temperatures = [0.3, 0.7, 1.0]  # Different creativity levels
            
            for temp in temperatures:
                response = await self.generate_response(
                    user_message=user_message,
                    session_id="",  # No context needed for variations
                    temperature=temp
                )
                variations.append(response)
            
            return variations
            
        except Exception as e:
            print(f"Error generating response variations: {e}")
            return []
    
    async def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from customer message for categorization"""
        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract the main keywords from the following customer message. Return them as a comma-separated list."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            keywords_text = response.choices[0].message.content
            return [kw.strip() for kw in keywords_text.split(",")]
                        
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
