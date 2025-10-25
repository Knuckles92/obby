"""
OpenAI integration for AI-managed session summaries.
This module will handle communication with OpenAI API for summarizing diffs.
"""

import os
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI
from config import settings as cfg
from typing import Optional
import threading

class OpenAIClient:
    """Handles OpenAI API calls for diff summarization with singleton pattern."""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    _warmed_up = False

    # Latest OpenAI models as of July 2025
    MODELS = {        # Latest GPT-4 model with improved capabilities
        'gpt-5-mini': 'gpt-5-mini',         # GPT-5 mini model
        'gpt-5': 'gpt-5',         # GPT-5 model
        'gpt-4.1': 'gpt-4.1',         # GPT-4.1 model
        'gpt-4.1-mini': 'gpt-4.1-mini'  # GPT-4.1 mini model
    }
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to reuse client instances."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, api_key=None, model="gpt-5-mini"):
        """Initialize the OpenAI client with improved timeout and retry settings."""
        # Skip re-initialization if already done
        if OpenAIClient._initialized:
            return
            
        with self._lock:
            if OpenAIClient._initialized:
                return
                
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            # Allow override via env while keeping default arg behavior
            self.model = os.getenv("OBBY_OPENAI_MODEL", model)
            
            # Enhanced timeout settings for cold starts
            try:
                # Longer timeout for initial/cold start calls
                self._timeout = float(os.getenv("OBBY_OPENAI_TIMEOUT", "60"))
                self._warm_timeout = float(os.getenv("OBBY_OPENAI_WARM_TIMEOUT", "30"))
            except Exception:
                self._timeout = 60.0
                self._warm_timeout = 30.0
                
            try:
                # More retries for better resilience
                self._max_retries = int(os.getenv("OBBY_OPENAI_MAX_RETRIES", "3"))
            except Exception:
                self._max_retries = 3
                
            # Configure OpenAI SDK with explicit timeout/retry to avoid hangs
            try:
                self.client = OpenAI(
                    api_key=self.api_key, 
                    timeout=self._timeout, 
                    max_retries=self._max_retries
                )
                logging.info(f"OpenAI client initialized with timeout={self._timeout}s, max_retries={self._max_retries}")
            except TypeError:
                # Fallback for SDKs without these kwargs
                logging.warning("OpenAI client does not support timeout/max_retries at construction; using basic client")
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client with advanced options: {e}")
                try:
                    self.client = OpenAI(api_key=self.api_key)
                except Exception as e2:
                    # As a last resort, set to None; callers handle errors gracefully
                    logging.error(f"Failed to initialize basic OpenAI client: {e2}")
                    self.client = None

            # Validate model selection
            if self.model not in self.MODELS.values():
                logging.warning(f"Model '{self.model}' not in latest models list. Available models: {list(self.MODELS.keys())}")
            logging.info(f"OpenAI client configured: model={self.model}, timeout={self._timeout}s, max_retries={self._max_retries}")

            # Format configuration caching
            self._format_config = None
            self._format_config_mtime = None
            self._format_file_path = Path('config/format.md')
            # Last error storage for diagnostics
            self._last_error = None
            
            # Mark as initialized
            OpenAIClient._initialized = True

    @classmethod
    def get_instance(cls, api_key=None, model="gpt-5-mini") -> 'OpenAIClient':
        """Get or create the singleton instance."""
        if not cls._instance:
            cls._instance = cls(api_key, model)
        return cls._instance

    def _get_temperature(self, requested_temperature: float) -> float:
        """
        Get appropriate temperature for the current model.
        GPT-5 era models only support temperature=1.0, older models support custom temperatures.
        """
        # GPT-5 era models that require temperature=1.0
        gpt5_models = ['gpt-5', 'gpt-5-mini']
        
        if self.model in gpt5_models:
            if requested_temperature != 1.0:
                logging.debug(f"Using temperature=1.0 for {self.model} (requested {requested_temperature})")
            return 1.0
        else:
            return requested_temperature

    def warm_up(self) -> bool:
        """Perform complete warm-up including an actual API call to establish connection.
        
        This method now makes a minimal API call to warm up the connection,
        preventing cold start issues on the first real request.
        
        Returns True if warm-up completed successfully.
        """
        if OpenAIClient._warmed_up:
            logging.debug("OpenAI client already warmed up, skipping")
            return True
            
        try:
            start_time = time.time()
            logging.info("Starting OpenAI client warm-up...")
            
            # Step 1: Load local configurations
            _ = self._load_session_summary_settings()
            _ = self._load_format_config()
            
            # Step 2: Ensure client is initialized
            if self.client is None:
                try:
                    self.client = OpenAI(api_key=self.api_key, timeout=self._timeout, max_retries=self._max_retries)
                except Exception as e:
                    logging.error(f"Failed to initialize OpenAI client during warm-up: {e}")
                    return False
            
            # Step 3: Make a minimal API call to warm up the connection
            try:
                logging.info("Making warm-up API call to establish connection...")
                warm_up_response = self._invoke_model(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say 'ready' in one word."}
                    ],
                    max_completion_tokens=10,
                    temperature=1.0
                )
                
                warm_up_time = time.time() - start_time
                logging.info(f"OpenAI warm-up completed successfully in {warm_up_time:.2f}s")
                
                # Mark as warmed up
                OpenAIClient._warmed_up = True
                return True
                
            except Exception as api_error:
                logging.error(f"Warm-up API call failed: {api_error}")
                # Even if warm-up fails, we can still try actual requests
                return False
                
        except Exception as e:
            logging.error(f"OpenAI warm-up encountered an error: {e}")
            return False

    def _invoke_model(self, model=None, messages=None, max_completion_tokens=None, temperature=None):
        """Invoke model via Responses API with Chat Completions fallback.

        Returns an object with .choices[0].message.content for compatibility.
        """
        model = model or self.model
        try:
            resp = self.client.responses.create(
                model=model,
                input=messages or [],
                temperature=temperature if temperature is not None else 1.0,
                max_output_tokens=max_completion_tokens,
            )
            text = getattr(resp, 'output_text', None)
            if not text:
                try:
                    text = resp.output[0].content[0].text
                    if hasattr(text, 'value'):
                        text = text.value
                except Exception:
                    text = None
            if text is None:
                raise ValueError('No text in Responses output')

            class _ShimMsg:
                def __init__(self, content):
                    self.content = content
            class _ShimChoice:
                def __init__(self, content):
                    self.message = _ShimMsg(content)
                    self.finish_reason = getattr(resp, 'finish_reason', None)
            class _ShimResp:
                def __init__(self, content):
                    self.choices = [_ShimChoice(content)]

            return _ShimResp(str(text).strip())
        except Exception as e:
            logging.debug(f"Responses API failed, falling back to chat.completions: {e}")
            return self.client.chat.completions.create(
                model=model,
                messages=messages or [],
                max_completion_tokens=max_completion_tokens,
                temperature=temperature if temperature is not None else 1.0,
            )

    def _invoke_model_with_tools(self, model=None, messages=None, max_completion_tokens=None, temperature=None, tools=None, tool_choice=None):
        """Invoke model with tool calling capability using Chat Completions API.
        
        Args:
            model: Model to use
            messages: Conversation messages
            max_completion_tokens: Token limit
            temperature: Sampling temperature
            tools: List of tool definitions in OpenAI format
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            
        Returns:
            Chat completion response with potential tool calls
        """
        model = model or self.model
        
        # For tool calling, we must use the Chat Completions API
        kwargs = {
            "model": model,
            "messages": messages or [],
            "max_completion_tokens": max_completion_tokens,
            "temperature": temperature if temperature is not None else 1.0,
        }
        
        # Add tools if provided
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        
        return self.client.chat.completions.create(**kwargs)

    def _retry_with_backoff(self, func, *args, max_retries=3, initial_delay=1.0, **kwargs):
        """Execute a function with exponential backoff retry logic.
        
        Args:
            func: The function to execute
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds between retries
            
        Returns:
            The result of the function call
            
        Raises:
            The last exception if all retries fail
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Use warm timeout after first attempt
                if attempt > 0 and 'timeout' not in kwargs:
                    # Update timeout for warmed connection
                    if hasattr(self.client, '_client'):
                        self.client._client.timeout = self._warm_timeout
                        
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logging.error(f"All {max_retries} attempts failed. Last error: {e}")
                    
        raise last_exception

    def summarize_diff(self, diff_content, settings=None, recent_tree_changes=None):
        """
        Summarize a diff for the session summary with semantic indexing optimization.
        Now includes retry logic and warm-up check.

        Args:
            diff_content: The diff content to summarize
            settings: Optional session summary settings for customization
            recent_tree_changes: Optional list of recent tree changes to include as context

        Returns:
            str: AI-generated summary with semantic metadata
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            # Load settings if not provided
            if settings is None:
                settings = self._load_session_summary_settings()

            # Build customized system prompt based on settings
            system_prompt = self._build_system_prompt(settings, "diff")

            # Adjust max_completion_tokens based on summary length setting
            max_completion_tokens_map = {
                'brief': 300,
                'moderate': 600,
                'detailed': 1000
            }
            max_completion_tokens = max_completion_tokens_map.get(settings.get('summaryLength', 'moderate'), 600)

            # Build user content with diff and optional tree change context
            user_content = f"Please summarize the following diff:\n\n{diff_content}"

            # Add recent tree changes as context if provided
            if recent_tree_changes and len(recent_tree_changes) > 0:
                tree_changes_text = "\n\nRecent file tree changes (for context):\n"
                for change in recent_tree_changes:
                    path = change.get('path', 'unknown')
                    event_type = change.get('type', 'unknown')
                    timestamp = change.get('timestamp', 'unknown')
                    tree_changes_text += f"- {event_type.capitalize()} {path} (at {timestamp})\n"
                user_content += tree_changes_text

            # Add focus areas to the user prompt if specified
            if settings.get('focusAreas'):
                focus_areas_text = ", ".join(settings['focusAreas'])
                user_content += f"\n\nPay special attention to these focus areas: {focus_areas_text}"

            # Use retry logic for the API call
            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                max_completion_tokens=max_completion_tokens,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("diff_summary", 0.7))
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logging.error(f"Error in summarize_diff after retries: {e}")
            return f"Error generating AI summary: {str(e)}"

    def summarize_minimal(self, context_text: str, files_used: list[str] | None = None):
        """Concise session-summary summary with Sources section in one pass.
        - First: 1–3 ultra-concise bullets, each starting with '- '
        - Then: a '### Sources' section listing files used with one-sentence rationales
        - If context appears trivial/noisy, return exactly: '- no meaningful changes'
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            system_prompt = (
                "You are a precise changelog summarizer. "
                "Output two parts in markdown: (1) 1–3 concise bullets (each starts with '- ') summarizing outcomes; "
                "then (2) a '### Sources' section listing the files used with one-sentence rationales (one bullet per file). "
                "Bullet rules for part (1): 12–20 words, no fluff, focus on WHAT changed and WHY it matters. "
                "If nothing substantive, respond exactly: '- no meaningful changes'."
            )

            files_block = ""
            if files_used:
                try:
                    dedup = []
                    seen = set()
                    for p in files_used:
                        if p and p not in seen:
                            dedup.append(p)
                            seen.add(p)
                    if dedup:
                        files_block = "\n\nFiles considered:\n" + "\n".join([f"- {p}" for p in dedup])
                except Exception:
                    files_block = ""

            user_content = (
                "Summarize these recent changes briefly, then include a Sources section.\n\n"
                f"Changes:\n{context_text}{files_block}"
            )
            
            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_completion_tokens=1200,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("minimal_summary", 0.3)),
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"- no meaningful changes (error: {str(e)})"

    def get_completion(self, prompt: str, system_prompt: Optional[str] = None,
                       max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """Generic helper to get a completion for an arbitrary prompt.

        Args:
            prompt: The user prompt/content sent to the model (string-only convenience).
            system_prompt: Optional system instruction to steer the model.
            max_tokens: Optional completion tokens cap. Falls back to insights limits.
            temperature: Optional temperature override. Falls back to insights temp.

        Returns:
            str: The model's message content, or an error string on failure.
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()

            sys_content = system_prompt or (
                "You are a precise, reliable assistant for the Obby project. "
                "Always begin by searching the local notes before considering other data sources. "
                "Only query databases or external systems if the notes search cannot answer the question. "
                "Follow the user's instructions exactly and return only the requested output."
            )

            # Sensible defaults using existing centralized settings
            if max_tokens is None:
                max_tokens = cfg.OPENAI_TOKEN_LIMITS.get("insights", 30000)  # Increased from 800 to 2000 for detailed responses
            if temperature is None:
                temperature = self._get_temperature(cfg.OPENAI_TEMPERATURES.get("insights", 0.7))

            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_content},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=max_tokens,
                temperature=temperature,
            )
            self._last_error = None

            content = response.choices[0].message.content
            if content is None:
                logging.warning("OpenAI returned None content, returning empty string")
                return ""

            return content.strip()
        except Exception as e:
            logging.error(f"get_completion failed: {e}")
            self._last_error = f"Error generating completion: {str(e)}"
            return self._last_error

    def is_available(self) -> bool:
        """Return True if the client is configured and ready to use."""
        try:
            return bool(self.api_key) and self.client is not None
        except Exception:
            return False

    def generate_proposed_questions(self, context_text: str) -> str:
        """Generate 2-4 concise, actionable questions based on the change context.

        Output rules:
        - 2–4 bullets, each starting with '- '
        - Make questions specific and helpful for follow-up exploration
        - If context appears trivial/noisy, return empty string
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            system_prompt = (
                "You propose thoughtful follow-up questions to help a user reflect on changes. "
                "Write 2-4 concise questions, each starting with '- '. "
                "Be specific and actionable; avoid generic questions. "
                "If the content looks trivial/noise (e.g., formatting only), return nothing."
            )
            user_content = (
                "Given these changes, propose a few questions the user could ask their assistant to explore next.\n\n"
                f"Changes:\n{context_text}"
            )
            
            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_completion_tokens=10000,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("proposed_questions", 0.7)),
            )
            text = response.choices[0].message.content.strip()
            # Heuristic: if the model replied with something other than bullets, ignore
            if not any(line.strip().startswith('- ') for line in text.splitlines()):
                return ""
            return text
        except Exception:
            return ""

    def generate_session_title(self, context_text: str) -> str:
        """Generate a short, punchy header for the session from context.

        Rules:
        - 3–7 words, Title Case
        - Optional 1 relevant emoji prefix
        - No trailing punctuation
        - If trivial/noisy context, return 'Minor Updates'
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            system_prompt = (
                "You create concise, punchy titles for development session summaries. "
                "Return ONLY the title. 3–7 words, Title Case, no trailing punctuation. "
                "Optionally start with ONE relevant emoji if it clearly fits."
            )
            user_content = (
                "Create a concise title that captures the main theme of these changes.\n\n"
                f"Changes:\n{context_text}"
            )
            
            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_completion_tokens=20,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("session_title", 0.7)),
            )
            title = response.choices[0].message.content.strip()
            # Post-process: collapse lines, strip quotes/backticks, trim length
            title = title.replace('\n', ' ').strip().strip('"\'`')
            if not title:
                return "Minor Updates"
            # Keep it reasonably short
            if len(title) > 60:
                title = title[:60].rstrip()
            return title
        except Exception:
            return "Minor Updates"

    def generate_sources_section(self, files: list, context_snippet: str = "") -> str:
        """Generate a markdown Sources section listing files used with 1-line rationales.

        Args:
            files: List of file identifiers (usually string paths). May also accept dicts with 'path' or 'filePath'.
            context_snippet: Optional short text (e.g., combined diffs) to help the model craft rationales.

        Returns:
            Markdown string beginning with '### Sources' followed by bullet list of file paths and rationales.
        """
        try:
            if not OpenAIClient._warmed_up:
                self.warm_up()

            # Normalize files list to paths
            normalized = []
            for f in files or []:
                if isinstance(f, str):
                    normalized.append(f)
                elif isinstance(f, dict):
                    p = f.get('path') or f.get('filePath') or f.get('file_path')
                    if p:
                        normalized.append(p)
            normalized = list(dict.fromkeys(normalized))  # de-dup preserve order

            if not normalized:
                return ""

            system_prompt = (
                "You produce a concise markdown Sources section. "
                "For each file, output exactly one bullet: 'path — one sentence rationale'. "
                "No extra commentary."
            )
            # Limit context to avoid long prompts
            ctx = context_snippet[:2000] if isinstance(context_snippet, str) else ""
            files_block = "\n".join([f"- {p}" for p in normalized])
            user_content = (
                "Create a Sources section listing these files with one-sentence rationales.\n\n"
                f"Files:\n{files_block}\n\n"
                f"Context (optional):\n{ctx}\n\n"
                "Return markdown starting with '### Sources' followed by the bullets."
            )

            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_completion_tokens=400,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("sources_section", 0.2)),
            )
            text = response.choices[0].message.content.strip()
            return text
        except Exception as e:
            logging.warning(f"Sources section generation failed: {e}")
            return ""

    def _load_session_summary_settings(self):
        """Load session summary settings from config file."""
        import json

        settings_file = Path('config/session_summary_settings.json')
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load session summary settings: {e}")

        # Return default settings
        return {
            'updateFrequency': 'realtime',
            'summaryLength': 'moderate',
            'writingStyle': 'technical',
            'includeMetrics': True,
            'autoUpdate': True,
            'maxSections': 10,
            'focusAreas': []
        }

    def _load_format_config(self):
        """Load format configuration from format.md with caching."""
        try:
            if not self._format_file_path.exists():
                logging.warning("format.md not found, using fallback prompts")
                return self._get_fallback_format_config()

            # Check if we need to reload the config
            current_mtime = self._format_file_path.stat().st_mtime
            if (self._format_config is None or
                self._format_config_mtime != current_mtime):

                with open(self._format_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self._format_config = self._parse_format_config(content)
                self._format_config_mtime = current_mtime
                logging.info("Format configuration loaded from format.md")

            return self._format_config

        except Exception as e:
            logging.error(f"Failed to load format.md: {e}")
            return self._get_fallback_format_config()

    def _parse_format_config(self, content):
        """Parse format.md content into structured configuration.
        
        NOTE: The current config/format.md file doesn't contain the specific sections
        this parser looks for (e.g., "## Session Summary Session Template", style variations).
        As a result, it always falls back to hardcoded templates. The regex parsing here
        is legacy code that could be simplified in the future.
        """
        # Start with fallback config as base to ensure we always have working templates
        fallback = self._get_fallback_format_config()
        config = {
            'session_template': fallback['session_template'],
            'diff_prompt': fallback['diff_prompt'],
            'tree_prompt': fallback['tree_prompt'],
            'insights_prompt': fallback['insights_prompt'],
            'style_variations': fallback['style_variations'].copy(),
            'length_options': fallback['length_options'].copy(),
            'manual_prompts': fallback.get('manual_prompts', {}),
            'user_format_instructions': content  # Store the entire format.md as user instructions
        }

        # Extract session template
        template_match = re.search(
            r'## Session Summary Session Template\s*```markdown\s*(.+?)\s*```',
            content, re.DOTALL
        )
        if template_match:
            config['session_template'] = template_match.group(1).strip()

        # Extract diff summarization prompt
        diff_match = re.search(
            r'#### Base Prompt\s*(.+?)(?=####|\n## )',
            content, re.DOTALL
        )
        if diff_match:
            config['diff_prompt'] = diff_match.group(1).strip()

        # Extract style variations
        style_sections = [
            ('technical', r'##### Technical Style\s*(.+?)(?=####|#####|\n## )'),
            ('casual', r'##### Casual Style\s*(.+?)(?=####|#####|\n## )'),
            ('formal', r'##### Formal Style\s*(.+?)(?=####|#####|\n## )'),
            ('bullet-points', r'##### Bullet-Points Style\s*(.+?)(?=####|#####|\n## )')
        ]

        for style, pattern in style_sections:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                config['style_variations'][style] = match.group(1).strip()

        # Extract length options
        length_sections = [
            ('brief', r'##### Brief\s*(.+?)(?=####|#####|\n## )'),
            ('moderate', r'##### Moderate\s*(.+?)(?=####|#####|\n## )'),
            ('detailed', r'##### Detailed\s*(.+?)(?=####|#####|\n## )')
        ]

        for length, pattern in length_sections:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                config['length_options'][length] = match.group(1).strip()

        # Extract tree change prompt
        tree_match = re.search(
            r'### Tree Change Summarization Prompt\s*(.+?)(?=###|\n## )',
            content, re.DOTALL
        )
        if tree_match:
            config['tree_prompt'] = tree_match.group(1).strip()

        # Extract session insights prompt
        insights_match = re.search(
            r'### Session Insights Prompt\s*(.+?)(?=###|\n## )',
            content, re.DOTALL
        )
        if insights_match:
            config['insights_prompt'] = insights_match.group(1).strip()

        # Extract manual update prompts
        manual_sections = [
            ('quick', r'#### Quick Update Prompt\s*(.+?)(?=####|\n## )'),
            ('full', r'#### Full Regeneration Prompt\s*(.+?)(?=####|\n## )'),
            ('smart', r'#### Smart Refresh Prompt\s*(.+?)(?=####|\n## )')
        ]

        for update_type, pattern in manual_sections:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                config['manual_prompts'][update_type] = match.group(1).strip()

        return config

    def _get_fallback_format_config(self):
        """Return hardcoded fallback configuration when format.md is unavailable."""
        return {
            'session_template': '''## {ai_header}

> {timestamp} • {file_path}

{detailed_entries}
{ai_insights}

---

''',
            'diff_prompt': '''You are an AI assistant for Obby. Generate VERY concise, targeted updates. {style_instruction} {length_instruction}

IMPORTANT: Format your response as a single bullet point:
- [Brief summary of what changed between session summary updates - focus only on the key change, not details]

Be extremely concise. Focus on WHAT changed, not HOW. Maximum one sentence. Make it specific and searchable but very brief.''',
            'tree_prompt': '''You are an AI assistant for Obby, a comprehensive note monitoring system. When summarizing file tree changes, provide a structured summary optimized for search and discovery.

IMPORTANT: Format your response EXACTLY as follows:
**Summary**: [Concise human-readable summary of the file/directory change]
**Topics**: [2-3 relevant topic keywords like "organization", "structure", "cleanup"]
**Keywords**: [3-5 searchable keywords related to the file operation]
**Impact**: [brief/moderate/significant - assess organizational impact]

Focus on the organizational impact and what it means for project structure. Do not include additional text outside this format.''',
            'insights_prompt': '''You are an AI assistant that analyzes development sessions. Be VERY reserved - only provide insights when there are clear, actionable takeaways or significant patterns.

Analyze this development session with {total_changes} changes:

{changes_text}

IMPORTANT:
- Only generate insights if there's a clear takeaway, pattern, or action item
- If changes are routine/minor, respond with just "-" (no insights)
- Maximum 2 concise bullet points starting with '-'
- Focus on: significant patterns, important decisions, or clear next steps
- Be specific and actionable. Avoid generic observations.''',
            'style_variations': {
                'technical': 'Use precise technical language and include technical details.',
                'casual': 'Use conversational tone and explain concepts in accessible terms.',
                'formal': 'Use professional, formal language suitable for documentation.',
                'bullet-points': 'Structure your response using clear bullet points and concise statements.'
            },
            'length_options': {
                'brief': 'Keep summaries concise and focus on the most important changes only.',
                'moderate': 'Provide balanced summaries with good detail without being verbose.',
                'detailed': 'Include comprehensive details and provide thorough analysis of changes.'
            },
            'manual_prompts': {
                'quick': 'Focus on recent changes from the last 1-2 hours. Prioritize immediate context and current work session.',
                'full': 'Provide a comprehensive overview of today\'s entire development session. Analyze patterns across all changes.',
                'smart': 'Intelligently determine what aspects need updating based on content gaps and recent activity patterns.'
            }
        }

    def _build_system_prompt(self, settings, content_type="diff"):
        """Build a customized system prompt based on user settings and format configuration."""
        writing_style = settings.get('writingStyle', 'technical')
        summary_length = settings.get('summaryLength', 'moderate')
        include_metrics = settings.get('includeMetrics', True)

        # Load format configuration
        format_config = self._load_format_config()

        # Check if we have user format instructions from format.md - use them as PRIMARY instructions
        user_instructions = format_config.get('user_format_instructions', '')
        if user_instructions and user_instructions.strip():
            return f"""You are an AI assistant for Obby, a comprehensive note monitoring system. \n\nThe user has provided specific formatting preferences. Follow these instructions EXACTLY:\n\n{user_instructions.strip()}\n\nBased on these preferences, summarize the provided diff content."""

        # Fallback to legacy system if no format.md found
        # Get base prompt template
        if content_type == "diff":
            base_prompt = format_config.get('diff_prompt', '')
        elif content_type == "tree":
            return format_config.get('tree_prompt', '')
        elif content_type == "insights":
            return format_config.get('insights_prompt', '')
        else:
            base_prompt = format_config.get('diff_prompt', '')

        # Get style instruction
        style_instruction = format_config.get('style_variations', {}).get(
            writing_style,
            'Use precise technical language and include technical details.'
        )

        # Get length instruction
        length_instruction = format_config.get('length_options', {}).get(
            summary_length,
            'Provide balanced summaries with good detail without being verbose.'
        )

        # Get metrics instruction
        metrics_instruction = ''
        if include_metrics:
            metrics_instruction = 'Include relevant metrics and quantitative information where applicable.'

        # Substitute placeholders in the base prompt
        prompt = base_prompt.format(
            style_instruction=style_instruction,
            length_instruction=length_instruction,
            metrics_instruction=metrics_instruction
        )

        return prompt

    def summarize_tree_change(self, tree_change_description, settings=None):
        """
        Summarize a file tree change for the session summary with semantic metadata.

        Args:
            tree_change_description: Description of the tree change (creation, deletion, move)
            settings: Optional session summary settings for customization

        Returns:
            str: AI-generated summary with semantic metadata
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            # Load settings if not provided
            if settings is None:
                settings = self._load_session_summary_settings()

            # Build system prompt using format configuration
            system_prompt = self._build_system_prompt(settings, "tree")

            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following file tree change with semantic metadata:\n\n{tree_change_description}"
                    }
                ],
                max_completion_tokens=400,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("tree_summary", 0.3))
            )

            text = response.choices[0].message.content.strip()
            # Optional safety-net: if model omitted Sources, and we have file_summaries, append via helper
            try:
                from config import settings as cfg
                if cfg.AI_SOURCES_FALLBACK_ENABLED:
                    low = text.lower()
                    if '## sources' not in low and '### sources' not in low:
                        # Build file list from file_summaries
                        paths = []
                        for fs in (batch_data.get('file_summaries') or []):
                            p = fs.get('file_path') if isinstance(fs, dict) else None
                            if p:
                                paths.append(p)
                        # dedup
                        seen = set()
                        paths = [p for p in paths if not (p in seen or seen.add(p))]
                        if paths:
                            sources_md = self.generate_sources_section(paths, batch_data.get('combined_diff') or '')
                            if sources_md and sources_md.strip():
                                text = text.rstrip() + "\n\n" + sources_md.strip()
            except Exception:
                pass
            return text

        except Exception as e:
            return f"Error generating tree change summary: {str(e)}"

    def update_session_summary(self, session_summary_path, summary, change_type="content", settings=None):
        """
        Update the session summary with the AI summary using structured format.

        Args:
            session_summary_path: Path to the session summary file
            summary: AI-generated summary to add
            change_type: Type of change ("content" or "tree")
            settings: Optional session summary settings for customization
        """
        session_summary_path = Path(session_summary_path)

        # Load settings if not provided
        if settings is None:
            settings = self._load_session_summary_settings()

        # Create session summary if it doesn't exist
        if not session_summary_path.exists():
            session_summary_path.parent.mkdir(exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            initial_content = f"# Session Summary - {today}\n\nThis file contains AI-generated summaries of your development sessions.\n\n---\n\n"
            session_summary_path.write_text(initial_content, encoding='utf-8')

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%I:%M %p")

        # Read existing content
        existing_content = ""
        if session_summary_path.exists() and session_summary_path.stat().st_size > 0:
            existing_content = session_summary_path.read_text(encoding='utf-8')

        # Always create new entry with simple format (no session management needed)
        self._create_new_session(session_summary_path, summary, change_type, date_str, time_str, existing_content, settings)

        # Extract semantic metadata and create searchable index entry
        try:
            metadata = self.extract_semantic_metadata(summary)
            # Use the current file path if available, otherwise fall back to notes folder
            file_path_for_index = getattr(self, '_current_file_path', str(session_summary_path.parent))
            searchable_entry = self.create_searchable_entry(
                metadata,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_type,
                file_path=file_path_for_index
            )
            self.save_semantic_index(searchable_entry)
            # Clear the temporary file path
            if hasattr(self, '_current_file_path'):
                delattr(self, '_current_file_path')
        except Exception as e:
            logging.warning(f"Failed to create semantic index entry: {e}")

        # Git integration has been removed from Obby - session summaries are saved without auto-commit

        logging.info(f"Session summary updated with structured format and semantic indexing: {session_summary_path}")

        # Return success status
        return True

    def _create_new_session(self, session_summary_path, summary, change_type, date_str, time_str, existing_content, settings=None):
        """Create a new session entry in the structured format."""

        # Generate initial insights
        if settings is None:
            settings = self._load_session_summary_settings()
        insights = self._generate_session_insights([summary], [change_type], is_new_session=True, settings=settings)

        # Load format configuration for session template
        format_config = self._load_format_config()
        template = format_config.get('session_template', '')

        # Prepare template variables (nicer timestamp + AI header)
        now_dt = datetime.now()
        date_part = f"{now_dt.strftime('%A')}, {now_dt.strftime('%B')} {now_dt.day}, {now_dt.year}"
        time_part = now_dt.strftime('%I:%M %p').lstrip('0')
        timestamp = f"{date_part} at {time_part}"

        # Derive a friendly file_path label
        file_path = getattr(self, '_current_file_path', None)
        if not file_path or file_path == 'multiple files':
            # Try to infer from metrics in the summary
            try:
                m = re.search(r"Files affected:\s*(\d+)", summary)
                if m:
                    n = int(m.group(1))
                    file_path = f"{n} file{'s' if n != 1 else ''}"
                else:
                    file_path = 'multiple files'
            except Exception:
                file_path = 'multiple files'

        # AI-generated session header/title
        ai_header = self.generate_session_title(summary)

        detailed_entries = summary  # Summary is already clean bullet points from AI

        # Apply template with variable substitution (extra keys are safe if unused)
        session_header = template.format(
            timestamp=timestamp,
            file_path=file_path,
            detailed_entries=detailed_entries,
            ai_insights=insights,
            ai_header=ai_header,
        )

        # Prepend new session to existing content with proper spacing
        # Ensure proper separation between session content and existing content
        if existing_content and not existing_content.startswith('\n'):
            # Add extra newline if existing content doesn't start with one
            updated_content = session_header + '\n' + existing_content
        else:
            updated_content = session_header + existing_content

        with open(session_summary_path, "w", encoding='utf-8') as f:
            f.write(updated_content)
            f.flush()  # Ensure content is written to disk

        # Small delay to ensure file system events are triggered
        import time
        time.sleep(0.1)

    def _add_to_existing_session(self, session_summary_path, summary, change_type, lines, session_start_line, settings=None):
        """Add to an existing session in the structured format."""
        from datetime import datetime

        # Find the detailed changes section and collect existing summaries
        detailed_changes_line = -1
        insights_line = -1
        existing_summaries = []
        existing_change_types = []

        for i in range(session_start_line, len(lines)):
            if lines[i].strip() == "### Detailed Changes:":
                detailed_changes_line = i
            elif lines[i].strip() == "## Insights":
                insights_line = i
                break
            elif detailed_changes_line != -1 and lines[i].strip().startswith("- **"):
                # Extract existing summaries for insight generation
                parts = lines[i].split("**: ", 1)
                if len(parts) > 1:
                    existing_summaries.append(parts[1])
                    # Try to determine change type from summary content
                    existing_change_types.append("content")  # Default to content

        if detailed_changes_line != -1:
            # Add new change to detailed changes section
            new_change = f"- **{datetime.now().strftime('%H:%M:%S')}**: {summary}"
            lines.insert(detailed_changes_line + 1, new_change)

            # Update the changes count in session summary
            for i in range(session_start_line, detailed_changes_line + 1):
                if "**Changes**:" in lines[i]:
                    # Extract current count and increment
                    parts = lines[i].split("**Changes**: ")
                    if len(parts) > 1:
                        try:
                            current_count = int(parts[1].split()[0])
                            lines[i] = f"**Changes**: {current_count + 1} changes detected"
                        except (ValueError, IndexError):
                            lines[i] = "**Changes**: Multiple changes detected"
                    break

            # Update insights with all summaries including the new one
            all_summaries = existing_summaries + [summary]
            all_change_types = existing_change_types + [change_type]
            if settings is None:
                settings = self._load_session_summary_settings()
            new_insights = self._generate_session_insights(all_summaries, all_change_types, is_new_session=False, settings=settings)

            # Replace insights section
            if insights_line != -1:
                # Find the end of insights section (next ## or --- or end of file)
                insights_end = len(lines)
                for i in range(insights_line + 1, len(lines)):
                    if lines[i].strip().startswith("##") or lines[i].strip() == "---":
                        insights_end = i
                        break

                # Replace insights content
                lines[insights_line + 1:insights_end] = [new_insights, ""]

        # Write updated content back to file
        with open(session_summary_path, "w", encoding='utf-8') as f:
            f.write('\n'.join(lines))
            f.flush()  # Ensure content is written to disk

        # Small delay to ensure file system events are triggered
        import time
        time.sleep(0.1)

    def _generate_session_insights(self, summaries, change_types, is_new_session=True, settings=None):
        """Generate intelligent insights based on session patterns and changes."""
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            # Load settings if not provided
            if settings is None:
                settings = self._load_session_summary_settings()

            # Analyze patterns in the summaries
            content_changes = sum(1 for ct in change_types if ct == "content")
            tree_changes = sum(1 for ct in change_types if ct == "tree")
            total_changes = len(summaries)

            # Create context for AI insight generation
            changes_text = "\n".join([f"- {summary}" for summary in summaries])

            # Build system prompt using format configuration
            system_prompt = self._build_system_prompt(settings, "insights")

            # Apply variable substitution to the prompt
            user_prompt = system_prompt.format(
                total_changes=total_changes,
                content_changes=content_changes,
                tree_changes=tree_changes,
                changes_text=changes_text
            )

            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_completion_tokens=300,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("insights", 0.4))
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logging.debug(f"AI insight generation failed: {e}")
            # Fallback insights if AI generation fails
            if is_new_session:
                return "- Active development session in progress\n- Monitoring file changes and updates"
            else:
                return f"- Development session with {len(summaries)} changes\n- Mix of content and structural modifications\n- Iterative development pattern observed"

    def extract_semantic_metadata(self, summary_text):
        """
        Extract semantic metadata from AI-generated summaries for indexing.
        Handles both new bullet-point format and legacy structured format.

        Args:
            summary_text: The formatted AI summary with semantic metadata

        Returns:
            dict: Extracted metadata with topics, keywords, and impact level
        """
        metadata = {
            'summary': '',
            'topics': [],
            'keywords': [],
            'impact': 'brief'
        }

        try:
            lines = summary_text.splitlines()

            # Check for new bullet-point format
            bullet_summaries = []
            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    bullet_summaries.append(line[2:].strip())

            if bullet_summaries:
                # New format: combine bullet points into summary
                metadata['summary'] = '; '.join(bullet_summaries)
                # Set impact based on number of changes
                if len(bullet_summaries) > 3:
                    metadata['impact'] = 'significant'
                elif len(bullet_summaries) > 1:
                    metadata['impact'] = 'moderate'
                else:
                    metadata['impact'] = 'brief'
            else:
                # Legacy format parsing
                for line in lines:
                    line = line.strip()
                    if line.startswith('**Summary**:'):
                        metadata['summary'] = line.replace('**Summary**:', '').strip()
                    elif line.startswith('**Topics**:'):
                        topics_str = line.replace('**Topics**:', '').strip()
                        metadata['topics'] = [t.strip() for t in topics_str.split(',') if t.strip()]
                    elif line.startswith('**Keywords**:'):
                        keywords_str = line.replace('**Keywords**:', '').strip()
                        metadata['keywords'] = [k.strip() for k in keywords_str.split(',') if k.strip()]
                    elif line.startswith('**Impact**:'):
                        metadata['impact'] = line.replace('**Impact**:', '').strip().lower()

                # If no structured metadata found, treat entire text as summary
                if not metadata['summary'] and not metadata['topics']:
                    metadata['summary'] = summary_text

        except Exception as e:
            logging.warning(f"Error extracting semantic metadata: {e}")
            metadata['summary'] = summary_text

        return metadata

    def create_searchable_entry(self, metadata, timestamp, change_type, file_path=None):
        """
        Create a searchable entry combining metadata for future search indexing.

        Args:
            metadata: Extracted semantic metadata dictionary
            timestamp: When the change occurred
            change_type: Type of change (content/tree)
            file_path: Path of the changed file (optional)

        Returns:
            dict: Searchable entry structure
        """
        searchable_entry = {
            'id': f"{timestamp}_{change_type}",
            'timestamp': timestamp,
            'date': self._parse_timestamp_date(timestamp),
            'time': self._parse_timestamp_time(timestamp),
            'type': change_type,
            'summary': metadata.get('summary', ''),
            'topics': metadata.get('topics', []),
            'keywords': metadata.get('keywords', []),
            'impact': metadata.get('impact', 'brief'),
            'file_path': file_path,
            'searchable_text': self._create_searchable_text(metadata)
        }

        return searchable_entry

    def _parse_timestamp_date(self, timestamp):
        """Parse timestamp to extract date safely."""
        try:
            if isinstance(timestamp, str):
                # Handle different timestamp formats
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', ''))
                else:
                    dt = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                return dt.date().isoformat()
            return datetime.now().date().isoformat()
        except Exception:
            return datetime.now().date().isoformat()

    def _parse_timestamp_time(self, timestamp):
        """Parse timestamp to extract time safely."""
        try:
            if isinstance(timestamp, str):
                # Handle different timestamp formats
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', ''))
                else:
                    dt = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                return dt.time().isoformat()
            return datetime.now().time().isoformat()
        except Exception:
            return datetime.now().time().isoformat()

    def _create_searchable_text(self, metadata):
        """Create a comprehensive searchable text field combining all metadata."""
        components = [
            metadata.get('summary', ''),
            ' '.join(metadata.get('topics', [])),
            ' '.join(metadata.get('keywords', [])),
            metadata.get('impact', '')
        ]
        return ' '.join([comp for comp in components if comp]).lower()

    def save_semantic_index(self, searchable_entry, index_path="notes/semantic_index.json"):
        """
        Save semantic index entry to a JSON file for future search capabilities.

        Args:
            searchable_entry: The searchable entry dictionary
            index_path: Path to the semantic index file
        """
        import json
        from pathlib import Path

        index_file = Path(index_path)

        try:
            # Load existing index or create new one
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {'entries': [], 'metadata': {'created': searchable_entry['timestamp'], 'version': '1.0'}}
                # Ensure parent directory exists
                index_file.parent.mkdir(parents=True, exist_ok=True)

            # Add new entry
            index_data['entries'].append(searchable_entry)
            index_data['metadata']['last_updated'] = searchable_entry['timestamp']
            index_data['metadata']['total_entries'] = len(index_data['entries'])

            # Keep only last 1000 entries to prevent file from growing too large
            if len(index_data['entries']) > 1000:
                index_data['entries'] = index_data['entries'][-1000:]
                index_data['metadata']['total_entries'] = 1000

            # Save updated index
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)

            logging.debug(f"Semantic index updated: {index_path}")

        except Exception as e:
            logging.error(f"Error saving semantic index: {e}")

    def summarize_batch_changes(self, batch_data: dict, settings=None):
        """
        Summarize a batch of accumulated file changes for efficient processing.

        Args:
            batch_data: Dictionary containing accumulated changes information
            settings: Optional session summary settings for customization

        Returns:
            str: AI-generated batch summary with semantic metadata
        """
        try:
            # Ensure client is warmed up
            if not OpenAIClient._warmed_up:
                self.warm_up()
                
            # Load settings if not provided
            if settings is None:
                settings = self._load_session_summary_settings()

            # Build system prompt for batch processing
            system_prompt = self._build_batch_system_prompt(settings)

            # Prepare batch context
            files_changed = batch_data.get('files_count', 0)
            total_changes = batch_data.get('total_changes', 0)
            time_span = batch_data.get('time_span', 'unknown')

            # Build user content for batch processing
            user_content = f"""Please analyze this batch of accumulated file changes:

Batch Overview:
- Files affected: {files_changed}
- Total changes: {total_changes}
- Time span: {time_span}

"""

            # Add individual file summaries if available
            if batch_data.get('file_summaries'):
                user_content += "Individual File Changes:\n"
                for file_summary in batch_data['file_summaries']:
                    file_path = file_summary.get('file_path', 'unknown')
                    summary = file_summary.get('summary', 'No summary')
                    user_content += f"- {file_path}: {summary}\n"
                user_content += "\n"
                # Also include concise list of files considered for Sources generation
                try:
                    paths = [fs.get('file_path', 'unknown') for fs in batch_data['file_summaries'] if fs.get('file_path')]
                    paths = list(dict.fromkeys(paths))
                    if paths:
                        user_content += "Files considered in this analysis:\n" + "\n".join([f"- {p}" for p in paths]) + "\n\n"
                except Exception:
                    pass

            # Add combined diff content if available (truncated for API limits)
            if batch_data.get('combined_diff'):
                user_content += "Key Changes Overview:\n"
                combined_diff = batch_data['combined_diff']
                # Truncate if too long to avoid API limits
                if len(combined_diff) > 3000:
                    user_content += combined_diff[:3000] + "\n... (truncated for brevity)\n"
                else:
                    user_content += combined_diff + "\n"

            # Add focus areas if specified
            if settings.get('focusAreas'):
                focus_areas_text = ", ".join(settings['focusAreas'])
                user_content += f"\nPay special attention to these focus areas: {focus_areas_text}"

            # Adjust max tokens for batch processing
            max_completion_tokens_map = {
                'brief': 400,
                'moderate': 800,
                'detailed': 1200
            }
            max_completion_tokens = max_completion_tokens_map.get(settings.get('summaryLength', 'moderate'), 800)

            logging.info(f"Processing batch AI request for {files_changed} files, {total_changes} changes")

            response = self._retry_with_backoff(
                self._invoke_model,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                max_completion_tokens=max_completion_tokens,
                temperature=self._get_temperature(cfg.OPENAI_TEMPERATURES.get("batch_summary", 0.3))
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error generating batch AI summary: {str(e)}"

    def _build_batch_system_prompt(self, settings):
        """Build a system prompt optimized for batch processing."""
        writing_style = settings.get('writingStyle', 'technical')
        summary_length = settings.get('summaryLength', 'moderate')
        include_metrics = settings.get('includeMetrics', True)

        # Load format configuration
        format_config = self._load_format_config()

        # Get style and length instructions
        style_instruction = format_config.get('style_variations', {}).get(
            writing_style,
            'Use precise technical language and include technical details.'
        )

        length_instruction = format_config.get('length_options', {}).get(
            summary_length,
            'Provide balanced summaries with good detail without being verbose.'
        )

        metrics_instruction = ''
        if include_metrics:
            metrics_instruction = 'Include relevant metrics and quantitative information where applicable.'

        # Batch-specific prompt
        batch_prompt = f"""You are an AI assistant for Obby, analyzing accumulated file changes in batch mode. {style_instruction} {length_instruction} {metrics_instruction}

IMPORTANT: Format your response for batch processing EXACTLY as follows:
**Batch Summary**: [Comprehensive overview of all changes across files]
**Key Topics**: [3-7 main topics across all changes, comma-separated]
**Key Keywords**: [5-10 important technical terms and concepts, comma-separated]
**Overall Impact**: [brief/moderate/significant - assess cumulative impact]
**Files Focus**: [Brief mention of most significantly changed files]
**Sources**: [List files used with a one-sentence rationale per file]

Focus on patterns across multiple files, cumulative impact, and development themes. Synthesize information rather than listing individual changes. Do not include additional text outside this format."""

        return batch_prompt
