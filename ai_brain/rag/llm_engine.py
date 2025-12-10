"""
LLM Engine - Generates answers using OpenAI GPT models
"""
from typing import List, Optional
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMEngine:
    """Handles answer generation using OpenAI LLM"""
    
    def __init__(self):
        """Initialize OpenAI client with environment variables"""
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '500'))
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language from text.
        
        Args:
            text: Text to detect language from
            
        Returns:
            Language code (e.g., 'en', 'es', 'fr')
        """
        # Basic keyword detection
        common_spanish = ['qué', 'cómo', 'dónde', 'cuándo', 'por qué']
        common_french = ['qu\'est', 'comment', 'où', 'quand', 'pourquoi']
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in common_spanish):
            return 'es'
        elif any(word in text_lower for word in common_french):
            return 'fr'
        else:
            return 'en'
    
    def _build_prompt(self, question: str, chunks: List[str]) -> str:
        """
        Build the LLM prompt with context.
        
        Args:
            question: User's question
            chunks: Retrieved context chunks
            
        Returns:
            Formatted prompt string
        """
        # Format context documents
        context = "\n\n".join([
            f"[Document {i+1}]\n{chunk[:800]}"  # Limit chunk size
            for i, chunk in enumerate(chunks)
        ])
        
        prompt = f"""You are a helpful AI assistant for real estate document analysis.

Context from relevant documents:
{context}

User Question: {question}

Instructions:
- The context may contain information about multiple real estate projects
- If multiple projects are mentioned, identify which is the MAIN project being described (usually the one with the most detail, mentioned first, or most prominent)
- Answer questions about ONLY the main project unless the user specifically asks about comparisons or other projects
- Ignore portfolio/reference projects that are just listed for comparison
- Answer based ONLY on the provided context above
- Be concise, clear, and direct in a friendly, conversational tone
- If the context doesn't contain enough information, say so politely
- Use plain text without markdown formatting (no ** for bold, no - for bullets)
- For lists, use simple numbered format (1. item, 2. item) or comma-separated items
- Answer directly without mentioning "documents" or "materials" - just state the facts
- Provide specific details (project names, locations, prices, features) when available
- Keep the response natural and easy to read, as if answering from your own knowledge

Answer:"""
        
        return prompt
    
    def generate_answer(self, question: str, chunks: List[str]) -> str:
        """
        Generate answer using OpenAI GPT model.
        
        Args:
            question: User's question
            chunks: List of retrieved chunk texts
            
        Returns:
            Generated answer string
        """
        if not chunks:
            return "I don't have enough information to answer this question. Please ensure documents have been uploaded and processed for this project."
        
        # Build prompt with context
        prompt = self._build_prompt(question, chunks)
        
        try:
            # Call OpenAI Chat Completion API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly and helpful AI assistant specializing in real estate. Answer questions naturally and directly using plain text. Avoid markdown formatting. Use numbered lists or commas for multiple items. State facts directly without mentioning sources or documents - answer as if you know the information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract answer from response
            answer = response.choices[0].message.content.strip()
            
            # Add usage info (optional, for debugging)
            # tokens_used = response.usage.total_tokens
            
            return answer
            
        except Exception as e:
            # Handle API errors gracefully
            error_msg = str(e)
            
            # Check for common errors
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                return "Error: Invalid OpenAI API key. Please check your OPENAI_API_KEY in the .env file."
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                return "Error: OpenAI API quota exceeded. Please check your billing settings."
            elif "rate_limit" in error_msg.lower():
                return "Error: Rate limit exceeded. Please try again in a moment."
            else:
                return f"Error generating answer: {error_msg}"
    
    def detect_language(self, text: str) -> str:
        """
        Public method to detect language.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code
        """
        return self._detect_language(text)
