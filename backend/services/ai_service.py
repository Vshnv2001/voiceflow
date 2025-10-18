"""
AI service for generating responses using Groq/LLM providers
"""

import asyncio
import aiohttp
import os
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime

class AIService:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_base_url = "https://api.groq.com/openai/v1"
        self.default_model = "llama-3.1-70b-versatile"
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
        """Generate AI response using Groq API"""
        try:
            model = model or self.default_model
            temperature = temperature or self.temperature
            max_tokens = max_tokens or self.max_tokens
            
            # Get conversation context
            context = await self._get_conversation_context(session_id)
            
            # Build the prompt
            prompt = self._build_prompt(user_message, context)
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.groq_base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        raise Exception(f"Groq API error: {error_text}")
                        
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
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.groq_base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stream": True
                }
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                line_str = line.decode('utf-8').strip()
                                if line_str.startswith('data: '):
                                    data_str = line_str[6:]
                                    if data_str == '[DONE]':
                                        break
                                    try:
                                        data = json.loads(data_str)
                                        if 'choices' in data and len(data['choices']) > 0:
                                            delta = data['choices'][0].get('delta', {})
                                            if 'content' in delta:
                                                yield delta['content']
                                    except json.JSONDecodeError:
                                        continue
                    else:
                        error_text = await response.text()
                        yield f"Error: {error_text}"
                        
        except Exception as e:
            yield f"Error generating response: {str(e)}"
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of customer message"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.groq_base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.default_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Analyze the sentiment of the following customer message. Respond with a JSON object containing: sentiment (positive/negative/neutral), confidence (0-1), and urgency (low/medium/high)."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 100
                }
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result["choices"][0]["message"]["content"]
                        try:
                            return json.loads(response_text)
                        except json.JSONDecodeError:
                            return {"sentiment": "neutral", "confidence": 0.5, "urgency": "medium"}
                    else:
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
            async with aiohttp.ClientSession() as session:
                url = f"{self.groq_base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.default_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Extract the main keywords from the following customer message. Return them as a comma-separated list."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 50
                }
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        keywords_text = result["choices"][0]["message"]["content"]
                        return [kw.strip() for kw in keywords_text.split(",")]
                    else:
                        return []
                        
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
