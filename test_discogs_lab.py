#!/usr/bin/env python3
"""
Test script for the Discogs Collection Lab integration
"""

from enhanced_snowflake_agent import EnhancedSnowflakeAgent, LabConfig, LabType

def test_discogs_lab():
    """Test the Discogs lab generation."""
    agent = EnhancedSnowflakeAgent()
    
    # Test configuration
    config = LabConfig(
        company_name="Universal Music Group",
        lab_types=[LabType.DISCOGS_COLLECTION],
        industry="entertainment",
        use_case="Music Collection Analytics",
        data_domain="music"
    )
    
    print("🎵 Testing Discogs Collection Lab Generation")
    print("=" * 50)
    
    try:
        agent.generate_labs(config)
        print("\n✅ Discogs lab generation test completed successfully!")
        print("Check the generated_labs directory for the output.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    test_discogs_lab()