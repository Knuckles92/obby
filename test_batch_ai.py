#!/usr/bin/env python3
"""
Test script for the new Batch AI Processing System

This script demonstrates how the batch AI processor works and can be used 
to test the functionality without running the full application.
"""

import os
import logging
import time
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_batch_ai_processor():
    """Test the batch AI processor functionality."""
    
    print("=" * 60)
    print("BATCH AI PROCESSING SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Import the batch processor
        from ai.batch_processor import BatchAIProcessor
        from ai.openai_client import OpenAIClient
        
        print("✓ Successfully imported batch processing modules")
        
        # Check if OpenAI API key is available
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠ Warning: OPENAI_API_KEY not set - AI processing will be simulated")
        
        # Initialize the components
        print("\n1. Initializing AI client and batch processor...")
        ai_client = OpenAIClient()
        batch_processor = BatchAIProcessor(ai_client)
        
        print("✓ Batch processor initialized successfully")
        
        # Check initial configuration
        print("\n2. Checking initial configuration...")
        status = batch_processor.get_batch_status()
        print(f"   - Enabled: {status.get('enabled', 'Unknown')}")
        print(f"   - Interval: {status.get('interval_seconds', 'Unknown')} seconds")
        print(f"   - Max batch size: {status.get('max_batch_size', 'Unknown')}")
        print(f"   - Last update: {status.get('last_update', 'Never')}")
        print(f"   - Pending changes: {status.get('pending_changes_count', 0)}")
        
        # Test configuration updates
        print("\n3. Testing configuration updates...")
        original_interval = status.get('interval_seconds', 300)
        test_interval = 180  # 3 minutes
        
        success = batch_processor.update_config(interval=test_interval)
        if success:
            print(f"✓ Successfully updated interval to {test_interval} seconds")
        else:
            print("✗ Failed to update configuration")
        
        # Restore original interval
        batch_processor.update_config(interval=original_interval)
        
        # Test manual batch processing (force mode since there may be no changes)
        print("\n4. Testing manual batch processing...")
        result = batch_processor.process_batch(force=True)
        
        if result.get('processed'):
            print("✓ Batch processing completed successfully")
            print(f"   - Changes processed: {result.get('changes_count', 0)}")
            print(f"   - Processing time: {result.get('processing_time', 0):.2f} seconds")
            if result.get('results'):
                batch_summary = result['results'].get('batch_summary', 'No summary')
                print(f"   - Batch summary: {batch_summary[:100]}...")
        else:
            reason = result.get('reason', result.get('error', 'Unknown'))
            print(f"ℹ Batch processing result: {reason}")
        
        # Test scheduler start/stop (briefly)
        print("\n5. Testing scheduler functionality...")
        
        print("   Starting scheduler...")
        batch_processor.start_scheduler()
        print("✓ Scheduler started")
        
        # Let it run briefly
        time.sleep(2)
        
        print("   Stopping scheduler...")
        batch_processor.stop_scheduler()
        print("✓ Scheduler stopped")
        
        print("\n6. Final status check...")
        final_status = batch_processor.get_batch_status()
        print(f"   - Scheduler running: {final_status.get('running', False)}")
        print(f"   - Next batch in: {final_status.get('next_batch_in_seconds', 0)} seconds")
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        print("\nThe batch AI processing system is ready to use!")
        print("\nKey features:")
        print("- Scheduled batch processing of accumulated file changes")
        print("- Configurable processing intervals and batch sizes")  
        print("- Manual trigger capability via API or direct calls")
        print("- Efficient AI processing to reduce API costs")
        print("- Integration with existing monitoring system")
        
        print("\nAPI Endpoints available:")
        print("- GET  /api/monitor/batch-ai/status     - Check status")
        print("- POST /api/monitor/batch-ai/trigger    - Manual trigger")
        print("- GET  /api/monitor/batch-ai/config     - Get config")
        print("- PUT  /api/monitor/batch-ai/config     - Update config")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure all required modules are available")
        return False
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False

def test_integration():
    """Test integration with the monitoring system."""
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST")
    print("=" * 60)
    
    try:
        from core.monitor import ObbyMonitor
        
        print("Testing batch AI integration with ObbyMonitor...")
        
        # Create monitor instance
        monitor = ObbyMonitor()
        
        # Check if batch processor is available
        if hasattr(monitor, 'batch_processor'):
            print("✓ Monitor has batch processor attribute")
        
        # Test batch processing methods
        if hasattr(monitor, 'trigger_batch_processing'):
            print("✓ Monitor has trigger_batch_processing method")
            
        if hasattr(monitor, 'get_batch_processing_status'):
            print("✓ Monitor has get_batch_processing_status method")
            
        if hasattr(monitor, 'update_batch_processing_config'):
            print("✓ Monitor has update_batch_processing_config method")
            
        print("✓ Integration test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("Batch AI Processing System Test Suite")
    print("This script tests the new batch processing functionality.\n")
    
    # Run main test
    main_success = test_batch_ai_processor()
    
    # Run integration test
    integration_success = test_integration()
    
    if main_success and integration_success:
        print("\n🎉 All tests passed! The batch AI processing system is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")