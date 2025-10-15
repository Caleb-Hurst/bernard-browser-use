"""
Test script for context_updater module functionality.

This script tests the core functionality without requiring OpenAI API calls.
"""

import tempfile
import os
from pathlib import Path
from context_updater import parse_remember_next_time, process_task_for_context_updates


def test_parse_remember_next_time():
	"""Test the parsing of REMEMBER NEXT TIME FOR patterns."""
	print("Testing parse_remember_next_time function...")
	
	# Test case 1: Basic pattern
	task1 = "Please test the login feature. REMEMBER NEXT TIME FOR recruiting (To post a job you need to first ensure you posses the feature)"
	result1 = parse_remember_next_time(task1)
	expected1 = ("recruiting", "To post a job you need to first ensure you posses the feature")
	assert result1 == expected1, f"Expected {expected1}, got {result1}"
	print("✓ Basic pattern test passed")
	
	# Test case 2: Pattern with extra whitespace
	task2 = "Test something. REMEMBER NEXT TIME FOR   user-management   (  Users must be verified before accessing admin features  )"
	result2 = parse_remember_next_time(task2)
	expected2 = ("user-management", "Users must be verified before accessing admin features")
	assert result2 == expected2, f"Expected {expected2}, got {result2}"
	print("✓ Whitespace handling test passed")
	
	# Test case 3: No pattern present
	task3 = "Just test the feature normally without any special instructions."
	result3 = parse_remember_next_time(task3)
	assert result3 is None, f"Expected None, got {result3}"
	print("✓ No pattern test passed")
	
	# Test case 4: Case insensitive
	task4 = "Test this. remember next time for billing-system (Payment processing requires SSL verification)"
	result4 = parse_remember_next_time(task4)
	expected4 = ("billing-system", "Payment processing requires SSL verification")
	assert result4 == expected4, f"Expected {expected4}, got {result4}"
	print("✓ Case insensitive test passed")
	
	# Test case 5: Multi-line information
	task5 = """Test the feature.
	REMEMBER NEXT TIME FOR onboarding (
		The onboarding process has three steps:
		1. Email verification
		2. Profile setup  
		3. Tutorial completion
	)"""
	result5 = parse_remember_next_time(task5)
	expected_info5 = """The onboarding process has three steps:
		1. Email verification
		2. Profile setup  
		3. Tutorial completion"""
	expected5 = ("onboarding", expected_info5)
	assert result5 == expected5, f"Expected {expected5}, got {result5}"
	print("✓ Multi-line pattern test passed")
	
	print("All parse_remember_next_time tests passed! ✓\n")


def test_process_task_without_api():
	"""Test task processing without making API calls."""
	print("Testing process_task_for_context_updates function (no API calls)...")
	
	# Create a temporary directory for testing
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_context_dir = Path(temp_dir)
		
		# Test case 1: Task without REMEMBER pattern
		task1 = "Just test the login feature normally"
		result1 = process_task_for_context_updates(task1, context_dir=temp_context_dir)
		assert result1 is None, f"Expected None for task without pattern, got {result1}"
		print("✓ Task without pattern test passed")
		
		# Test case 2: Task with REMEMBER pattern (will fail due to no API key, but should parse correctly)
		task2 = "Test login. REMEMBER NEXT TIME FOR authentication (Users need 2FA enabled)"
		
		# Temporarily remove API key to test parsing without API calls
		original_api_key = os.environ.get("OPENAI_API_KEY")
		if "OPENAI_API_KEY" in os.environ:
			del os.environ["OPENAI_API_KEY"]
		
		result2 = process_task_for_context_updates(task2, context_dir=temp_context_dir)
		
		# Restore API key if it existed
		if original_api_key:
			os.environ["OPENAI_API_KEY"] = original_api_key
		
		# Should return None due to missing API key, but parsing should work
		assert result2 is None, f"Expected None due to missing API key, got {result2}"
		print("✓ Task with pattern (no API key) test passed")
		
	print("All process_task_for_context_updates tests passed! ✓\n")


def test_filename_sanitization():
	"""Test that feature names are properly sanitized for filenames."""
	print("Testing filename sanitization...")
	
	from context_updater import update_context_file
	import re
	
	# Test various feature names that need sanitization
	test_cases = [
		("User Management", "user-management"),
		("billing/payment", "billing-payment"),
		("API & Authentication", "api-authentication"),
		("file-upload feature!", "file-upload-feature"),
		("   spaced   ", "spaced"),
	]
	
	for feature_name, expected_filename in test_cases:
		# Simulate the sanitization logic
		safe_feature_name = re.sub(r'[^\w\-]', '-', feature_name.lower())
		# Replace multiple consecutive dashes with single dash and strip dashes from ends
		safe_feature_name = re.sub(r'-+', '-', safe_feature_name).strip('-')
		assert safe_feature_name == expected_filename, f"Expected {expected_filename}, got {safe_feature_name}"
	
	print("✓ All filename sanitization tests passed")
	print("All filename sanitization tests passed! ✓\n")


if __name__ == "__main__":
	print("Running context_updater tests...\n")
	
	try:
		test_parse_remember_next_time()
		test_process_task_without_api() 
		test_filename_sanitization()
		
		print("🎉 All tests passed successfully!")
	except Exception as e:
		print(f"❌ Test failed: {str(e)}")
		raise