#!/usr/bin/env python3
"""
Test script for the updated voice service with simplified voice management
"""

import asyncio
import os
from services.voice_service import VoiceService
from services.database_service import DatabaseService

async def test_voice_service():
    """Test the voice service functionality"""
    print("🎤 Testing Voice Service with Simplified Voice Management")
    print("=" * 60)
    
    # Initialize services
    voice_service = VoiceService()
    db_service = DatabaseService()
    
    try:
        # Test 1: Get available voices
        print("\n1. Testing available voices...")
        voices = await voice_service.get_available_voices()
        print(f"   Found {len(voices)} available voices")
        
        if voices:
            for voice in voices[:3]:  # Show first 3 voices
                print(f"   - {voice['name']} ({voice['voice_id']}) - {voice['category']}")
        
        # Test 2: Get voices by category
        print("\n2. Testing voices by category...")
        male_voices = await voice_service.get_voices_by_category('male')
        female_voices = await voice_service.get_voices_by_category('female')
        print(f"   Male voices: {len(male_voices)}")
        print(f"   Female voices: {len(female_voices)}")
        
        # Test 3: Get default voice
        print("\n3. Testing default voice...")
        default_voice = await voice_service.get_default_voice()
        if default_voice:
            print(f"   Default voice: {default_voice['name']} ({default_voice['voice_id']})")
        else:
            print("   No default voice found")
        
        # Test 4: Get specific voice
        if voices:
            voice_id = voices[0]['voice_id']
            print(f"\n4. Testing specific voice lookup...")
            voice = await voice_service.get_voice_by_id(voice_id)
            if voice:
                print(f"   Found voice: {voice['name']} - {voice['description']}")
            else:
                print("   Voice not found")
        
        # Test 5: Test voice selection for message
        print(f"\n5. Testing voice selection...")
        selected_voice_id = await voice_service.select_voice_for_message("test-message-id")
        print(f"   Selected voice ID: {selected_voice_id}")
        
        print("\n✅ All voice service tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error testing voice service: {e}")
        import traceback
        traceback.print_exc()

async def test_database_voice_operations():
    """Test database voice operations"""
    print("\n🗄️ Testing Database Voice Operations")
    print("=" * 60)
    
    db_service = DatabaseService()
    
    try:
        # Test available voices
        print("\n1. Testing get_available_voices...")
        voices = await db_service.get_available_voices()
        print(f"   Found {len(voices)} voices in database")
        
        # Test voice by category
        print("\n2. Testing get_voices_by_category...")
        male_voices = await db_service.get_voices_by_category('male')
        print(f"   Male voices: {len(male_voices)}")
        
        # Test specific voice
        if voices:
            voice_id = voices[0]['voice_id']
            print(f"\n3. Testing get_voice_by_id...")
            voice = await db_service.get_voice_by_id(voice_id)
            if voice:
                print(f"   Found voice: {voice['name']}")
            else:
                print("   Voice not found")
        
        print("\n✅ All database voice tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error testing database operations: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests"""
    print("🚀 VoiceFlow AI - Backend Service Tests")
    print("=" * 60)
    
    # Check environment variables
    required_env_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set up your .env file with Supabase credentials")
        return
    
    # Run tests
    await test_database_voice_operations()
    await test_voice_service()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
