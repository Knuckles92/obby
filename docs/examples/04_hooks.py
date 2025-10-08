"""
Example 4: Using Hooks

Hooks allow you to intercept and modify interactions with Claude.
They're useful for:
- Preprocessing user input
- Logging conversations
- Adding safety filters
- Modifying responses
- Implementing custom logic before/after queries

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable
- Install dependencies: pip install -r requirements.txt

Usage:
    python examples/04_hooks.py
"""

import anyio
from claude_agent_sdk import ClaudeSDKClient
from typing import Any
import datetime


class ConversationLogger:
    """
    A hook that logs all conversations to a file or console.
    """

    def __init__(self, log_to_file: bool = False):
        self.log_to_file = log_to_file
        self.conversations = []

    def pre_query_hook(self, prompt: str) -> str:
        """
        Called before sending a query to Claude.

        Args:
            prompt: The original prompt

        Returns:
            Modified prompt (or original if no changes needed)
        """
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] USER: {prompt}"

        print(f"\n{'='*50}")
        print(f"HOOK: Pre-query hook triggered")
        print(f"HOOK: Logging user input...")
        print(f"{'='*50}\n")

        self.conversations.append(log_entry)

        if self.log_to_file:
            with open("conversation_log.txt", "a") as f:
                f.write(log_entry + "\n")

        return prompt  # Return unmodified prompt

    def post_response_hook(self, response: str) -> str:
        """
        Called after receiving a response from Claude.

        Args:
            response: Claude's response

        Returns:
            Modified response (or original if no changes needed)
        """
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] CLAUDE: {response}"

        print(f"\n{'='*50}")
        print(f"HOOK: Post-response hook triggered")
        print(f"HOOK: Logging Claude's response...")
        print(f"{'='*50}\n")

        self.conversations.append(log_entry)

        if self.log_to_file:
            with open("conversation_log.txt", "a") as f:
                f.write(log_entry + "\n\n")

        return response  # Return unmodified response


class SafetyFilter:
    """
    A hook that filters sensitive information from prompts.
    """

    def __init__(self):
        # Patterns to filter (simplified for demo)
        self.sensitive_patterns = [
            "password",
            "credit card",
            "ssn",
            "secret"
        ]

    def pre_query_hook(self, prompt: str) -> str:
        """
        Filter sensitive information from prompts.
        """
        original_prompt = prompt
        prompt_lower = prompt.lower()

        # Check for sensitive patterns
        for pattern in self.sensitive_patterns:
            if pattern in prompt_lower:
                print(f"\n⚠️  WARNING: Detected potential sensitive data: '{pattern}'")
                print(f"⚠️  Consider removing sensitive information before sending.\n")

        return prompt


class PromptEnhancer:
    """
    A hook that automatically enhances prompts with additional context.
    """

    def __init__(self, context: str = ""):
        self.context = context

    def pre_query_hook(self, prompt: str) -> str:
        """
        Add context to prompts automatically.
        """
        if self.context:
            enhanced = f"{self.context}\n\nUser Question: {prompt}"
            print(f"\n📝 HOOK: Enhanced prompt with context")
            print(f"📝 Original: {prompt}")
            print(f"📝 Enhanced length: {len(enhanced)} chars\n")
            return enhanced

        return prompt


async def demo_logging_hook():
    """
    Demonstrate conversation logging with hooks.
    """
    print("=" * 60)
    print("📝 DEMO 1: CONVERSATION LOGGING HOOK")
    print("=" * 60)
    print()

    logger = ConversationLogger(log_to_file=False)

    # In actual implementation, hooks would be registered with the client
    # This is a conceptual demonstration

    print("🔄 Simulating query with logging hooks...")
    print("-" * 60)

    # Simulate pre-query hook
    prompt = "What is Python?"
    prompt = logger.pre_query_hook(prompt)

    # Simulate Claude's response
    response = "Python is a high-level programming language..."
    response = logger.post_response_hook(response)

    print(f"\n📊 Conversation history: {len(logger.conversations)} entries")
    print("=" * 60)


async def demo_safety_hook():
    """
    Demonstrate safety filtering with hooks.
    """
    print("\n\n" + "=" * 60)
    print("🛡️  DEMO 2: SAFETY FILTER HOOK")
    print("=" * 60)
    print()

    safety = SafetyFilter()

    test_prompts = [
        "What is the weather today?",
        "How do I reset my password?",
        "Tell me about credit card processing",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"📝 TESTING PROMPT {i}: {prompt}")
        print("-" * 60)
        filtered = safety.pre_query_hook(prompt)
        print()


async def demo_enhancer_hook():
    """
    Demonstrate prompt enhancement with hooks.
    """
    print("\n\n" + "=" * 60)
    print("✨ DEMO 3: PROMPT ENHANCEMENT HOOK")
    print("=" * 60)
    print()

    context = "You are a helpful Python programming tutor. Provide clear, beginner-friendly explanations."
    enhancer = PromptEnhancer(context=context)

    prompt = "What are decorators?"
    print(f"📝 ORIGINAL PROMPT: {prompt}")
    print("-" * 60)
    
    enhanced = enhancer.pre_query_hook(prompt)

    print(f"\n🚀 ENHANCED PROMPT READY FOR CLAUDE:")
    print("-" * 60)
    print(f"   {enhanced[:100]}...")
    print("=" * 60)


async def main():
    """
    Run all hook demonstrations.
    """
    print("=" * 60)
    print("🪝 HOOKS DEMONSTRATION")
    print("=" * 60)
    print("Hooks allow you to intercept and modify Claude interactions")
    print("=" * 60)
    print()

    await demo_logging_hook()
    await demo_safety_hook()
    await demo_enhancer_hook()

    print("\n" + "=" * 60)
    print("✨ HOOKS DEMONSTRATION COMPLETED!")
    print("=" * 60)
    print("\nℹ️  NOTE: Full hook integration requires proper SDK setup.")
    print("ℹ️  Refer to claude-agent-sdk documentation for hook registration.")
    print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
