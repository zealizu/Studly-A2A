from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from uuid import uuid4
import asyncio
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
    
    async def process_messages(
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
            raise ValueError("User input is empty")

        # Retrieve past context (if any)
        history = self.study_contexts.get(context_id, [])
        # Call Gemini asynchronously
        study_plan = await self._generate_study_plan(user_text)
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
        
    async def _generate_study_plan(self, query: str) -> str:
        """Call Gemini model via LangChain asynchronously."""
        try:
            prompt_template = PromptTemplate(
                input_variables=["query"],
                template=(
                    "You are Studly, an intelligent study planner. The user says:\n"
                    "\"{query}\"\n\n"
                    "Based on this, create a structured study plan with:\n"
                    "- Total duration (days or weeks)\n"
                    "- Daily goals or milestones\n"
                    "- Estimated time per day\n"
                    "- Motivational advice at the end.\n"
                    "If the user asks something unrelated to study planning, "
                    "politely decline and suggest they ask for a study plan instead.\n\n"
                    "Format response with markdown headers for clarity."
                    
                )
            )

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=apikey,
                temperature=0.5,
                max_retries=3
            )

            chain = prompt_template | llm

            # Run Gemini generation asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, chain.invoke, {"query": query})

            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            print(f"Gemini error: {e}")
            return "I encountered an issue generating the study plan. Please try again."