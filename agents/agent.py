from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from uuid import uuid4
from typing import List, Optional
from models.a2a import (
    A2AMessage, TaskResult, TaskStatus, Artifact,
    MessagePart, MessageConfiguration
)

load_dotenv()

apikey = os.environ["GEMINI_API_KEY"]

class StudlyAgent:
    def __init__(self, ):
            self.study_contexts = {}
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=apikey,
                temperature=0.3,
                max_retries=3,
                # max_output_tokens=400  
            )
            self.prompt_template = PromptTemplate(
                input_variables=["query"],
                template=(
                    """You are Studly, a study planner. Query: {query}
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

        # Retrieve past context (if any)
        history = self.study_contexts.get(context_id, [])
        
        study_plan = self._generate_study_plan(user_text)
        # Cache this interaction
        self.study_contexts[context_id] = history + [user_text]

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

        # Combine conversation history
        full_history = messages + [response_message]

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="completed",
                message=response_message
            ),
            artifacts=artifacts,
            history=full_history
        )
        
    def _generate_study_plan(self, query: str) -> str:
        """Call Gemini model via LangChain asynchronously."""
        try:
            response = self.chain.invoke({"query": query})
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