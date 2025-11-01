from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from uuid import uuid4
from typing import List, Optional, Dict
from models.a2a import (
    A2AMessage, TaskResult, TaskStatus, Artifact,
    MessagePart, MessageConfiguration
)
from config import (
    ENABLE_SUMMARIZATION, SUMMARY_THRESHOLD, 
    ENABLE_HISTORY_CACHE, HISTORY_CAP_MESSAGES
)

load_dotenv()

apikey = os.environ.get("GEMINI_API_KEY", "test-key-for-testing")

class StudlyAgent:
    def __init__(self, ):
            self.study_contexts = {}
            # Cache for conversation summaries per context_id
            self.context_summaries: Dict[str, str] = {}
            # Cache for last messages per context_id to avoid rebuilding
            self.context_last_messages: Dict[str, List[A2AMessage]] = {}
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=apikey,
                temperature=0.3,
                max_retries=3,
                # max_output_tokens=400  
            )
            self.prompt_template = PromptTemplate(
                input_variables=["context", "query"],
                template=(
                    """You are Studly, a study planner.
                        
                        {context}
                        
                        Current Query: {query}
                        
                        Output a structured plan in markdown:
                        # Duration: [days/weeks]
                        ## Daily Goals: [list milestones]
                        ## Time Estimates: [per day]
                        # Tips: [motivational advice]
                        # Concise (under 400 words).
                        """
                    
                )
            )
            self.chain = self.prompt_template | self.llm
            
            # Summarization template
            self.summary_template = PromptTemplate(
                input_variables=["history"],
                template=(
                    """Summarize the following conversation history concisely in 2-3 sentences, 
                    focusing on the user's study goals and any key preferences mentioned:
                    
                    {history}
                    
                    Summary:"""
                )
            )
            self.summary_chain = self.summary_template | self.llm
    
    def process_messages(
        self,
        messages: List[A2AMessage],
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        config: Optional[MessageConfiguration] = None
    ) -> TaskResult:
        """Process incoming messages and return a personalized study plan."""

        # Generate IDs if not provided
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())

        # Get last user message
        user_message = messages[-1] if messages else None
        if not user_message:
            raise ValueError("No message provided")

        # Extract text input
        user_text = ""
        for part in user_message.parts:
            if part.kind == "text":
                user_text = part.text.strip()
                break

        if not user_text:
            # Log empty case
            print(f"Debug - Task {task_id}: Empty user input - parts: {len(user_message.parts or [])} items, kinds: {[p.kind for p in user_message.parts or []]}")
            return self._build_fallback_response(task_id, context_id, "I didn't catch that—could you rephrase your study request?")

        # Prepare context for LLM (summary or recent history)
        context_text = self._prepare_context(messages, context_id)
        
        study_plan = self._generate_study_plan(user_text, context_text)
        
        # Cache messages if enabled
        if ENABLE_HISTORY_CACHE:
            self.context_last_messages[context_id] = messages

        # Build response
        response_message = A2AMessage(
            role="agent",
            parts=[MessagePart(kind="text", text=study_plan)],
            taskId=task_id
        )

        # Artifacts (optional structured output)
        artifacts = [
            Artifact(
                name="study_plan",
                parts=[MessagePart(kind="text", text=study_plan)]
            )
        ]

        # Combine conversation history (capped)
        full_history = messages + [response_message]
        # Keep only recent history in returned result
        capped_history = full_history[-HISTORY_CAP_MESSAGES:] if len(full_history) > HISTORY_CAP_MESSAGES else full_history

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="completed",
                message=response_message
            ),
            artifacts=artifacts,
            history=capped_history
        )
        
    def _prepare_context(self, messages: List[A2AMessage], context_id: str) -> str:
        """
        Prepare context for LLM - either recent history or summary.
        
        Args:
            messages: Current message history (already capped by normalizer)
            context_id: Context ID for summary lookup
            
        Returns:
            Context string to include in prompt
        """
        # Exclude the last message (current query) from context
        history_messages = messages[:-1] if len(messages) > 1 else []
        
        # If no history, return empty context
        if not history_messages:
            return "No previous conversation history."
        
        # Check if we should use summarization
        if ENABLE_SUMMARIZATION and len(history_messages) >= SUMMARY_THRESHOLD:
            # Check if we have a cached summary
            if context_id in self.context_summaries:
                summary = self.context_summaries[context_id]
                print(f"Debug - Using cached summary for context {context_id}")
            else:
                # Generate new summary
                summary = self._generate_summary(history_messages)
                self.context_summaries[context_id] = summary
                print(f"Debug - Generated new summary for context {context_id}")
            
            return f"Previous conversation summary: {summary}"
        else:
            # Use recent raw history
            history_text = "\n".join([
                f"{msg.role}: {msg.parts[0].text if msg.parts and msg.parts[0].kind == 'text' else '[non-text]'}"
                for msg in history_messages
            ])
            return f"Recent conversation history:\n{history_text}"
    
    def _generate_summary(self, messages: List[A2AMessage]) -> str:
        """
        Generate a summary of conversation history.
        
        Args:
            messages: List of messages to summarize
            
        Returns:
            Summary text
        """
        try:
            # Format history for summarization
            history_text = "\n".join([
                f"{msg.role}: {msg.parts[0].text if msg.parts and msg.parts[0].kind == 'text' else '[non-text]'}"
                for msg in messages
            ])
            
            response = self.summary_chain.invoke({"history": history_text})
            summary = response.content if hasattr(response, "content") else str(response)
            return summary.strip()
        except Exception as e:
            print(f"Summarization error: {e}")
            # Fallback: just use a simple truncated history
            return "Previous conversation about study planning."
    
    def _generate_study_plan(self, query: str, context: str = "") -> str:
        """Call Gemini model via LangChain."""
        try:
            response = self.chain.invoke({"query": query, "context": context})
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            print(f"Gemini error: {e}")
            return "I encountered an issue generating the study plan. Please try again."

    def _build_fallback_response(self, task_id: str, context_id: str, message_text: str) -> TaskResult:
        response_message = A2AMessage(
            role="agent",
            parts=[MessagePart(kind="text", text=message_text)],
            taskId=task_id
        )
        artifacts = [Artifact(name="clarification", parts=[MessagePart(kind="text", text=message_text)])]
        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="completed", message=response_message),
            artifacts=artifacts,
            history=[response_message]  # Minimal history
        )