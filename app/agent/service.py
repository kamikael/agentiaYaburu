import logging
import json
import uuid
from typing import Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, messages_to_dict, messages_from_dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSerializable

from app.agent.tools import AVAILABLE_TOOLS, TOOL_LIST
from config import settings
from app.db import AsyncSessionLocal
from app.models.conversationHistory import ConversationHistory
from app.models.user import User
from app.models.stores import store as StoreModel
from sqlalchemy import select
from app.agent.context import store_id_ctx, phone_number_ctx, yaburu_store_id_ctx
from app.agent.prompts import agent_prompt

logger = logging.getLogger(__name__)

class CustomAgentExecutor:
    """
    Exécuteur d'agent robuste avec gestion dynamique des outils.
    """
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        # On lie les outils au modèle
        self.llm = ChatOpenAI(
            model=settings.GEMINI_MODEL,
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base=settings.OPENROUTER_URL,
            temperature=settings.GEMINI_TEMPERATURE
        ).bind_tools(TOOL_LIST, tool_choice="any")
#         self.llm = ChatGoogleGenerativeAI(
#     model=settings.GEMINI_MODEL,
#     google_api_key=settings.GEMINI_API_KEY,
#     temperature=settings.GEMINI_TEMPERATURE,
# ).bind_tools(
#     TOOL_LIST,
#     tool_choice="any"
# )

        # Construction de la chaine
        self.agent: RunnableSerializable = (
            {
                "input": lambda x: x["input"],
                "chat_history": lambda x: x["chat_history"],
                "agent_scratchpad": lambda x: x.get("agent_scratchpad", []),
                "user_name": lambda x: x.get("user_name", "Marchand"),
                "store_name": lambda x: x.get("store_name", "votre boutique")
            }
            | agent_prompt
            | self.llm
        )

    async def get_response(self, text: str, store_id: str, conversation_id: str, user_id: str, phone: str = None) -> str:
        """Alias pour invoke() pour compatibilité avec le reste de l'application."""
        return await self.invoke(text, store_id, conversation_id, user_id, phone)

    async def invoke(self, input_text: str, store_id: str, conversation_id: str, user_id: str, phone: str = None) -> str:
        # ContextVar pour que les outils accèdent aux infos sans paramètre LLM
        store_id_ctx.set(store_id)
        if phone:
            phone_number_ctx.set(phone)
        
        async with AsyncSessionLocal() as db:
            # 1. Chargement contexte (User, store, History)
            user_name, store_name, yaburu_store_id = await self._get_context_info(db, user_id, store_id)
            if yaburu_store_id:
                yaburu_store_id_ctx.set(yaburu_store_id)
            
            chat_history = await self._load_history(db, conversation_id, user_id)
            
            agent_scratchpad = []
            iterations = 0
            
            while iterations < self.max_iterations:
                iterations += 1
                
                # Appeler le LLM
                prediction = await self.agent.ainvoke({
                    "input": input_text,
                    "chat_history": chat_history,
                    "agent_scratchpad": agent_scratchpad,
                    "user_name": user_name,
                    "store_name": store_name
                })
                
                logger.debug(f"🤖 [Iteration {iterations}] LLM output: {prediction}")

                if not prediction.tool_calls:
                    # Sécurité si tool_choice="any" n'est pas respecté
                    return prediction.content

                agent_scratchpad.append(prediction)
                
                # Traitement des appels d'outils
                for tool_call in prediction.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["args"]
                    call_id = tool_call["id"]
                    
                    # Détection Arrêt : final_answer
                    if name == "final_answer":
                        final_text = args.get("answer", "Erreur: pas de réponse générée.")
                        # Persistance finale
                        chat_history.extend([HumanMessage(content=input_text), AIMessage(content=final_text)])
                        await self._save_history(db, conversation_id, user_id, chat_history)
                        return final_text
                    
                    # Exécution dynamique
                    tool_result = await self._execute_tool(name, args)
                    
                    # Injection du résultat dans le scratchpad
                    agent_scratchpad.append(ToolMessage(
                        content=str(tool_result),
                        tool_call_id=call_id
                    ))
            return "Désolé, j'ai atteint ma limite de réflexion sans trouver de réponse."

    async def _execute_tool(self, name: str, args: dict) -> str:
        """Exécute un outil par son nom avec gestion d'erreurs."""
        if name not in AVAILABLE_TOOLS:
            return f"Erreur: L'outil '{name}' n'existe pas."
        
        try:
            logger.info(f"🛠️ Exécution tool: {name}({args})")
            tool_func = AVAILABLE_TOOLS[name]
            
            if hasattr(tool_func, "ainvoke"):
                result = await tool_func.ainvoke(args)
            else:
                result = tool_func.invoke(args)
            return result
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'exécution de {name}: {e}")
            return f"Erreur lors de l'exécution de l'outil {name}: {str(e)}"

    async def _get_context_info(self, db, user_id, store_id):
        try:
            u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            s_id = uuid.UUID(store_id) if isinstance(store_id, str) else store_id
            
            user = (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none()
            store = (await db.execute(select(StoreModel).where(StoreModel.id == s_id))).scalar_one_or_none()
            
            return (
                user.first_name if user and user.first_name else "Marchand",
                store.store_name if store and store.store_name else "votre boutique",
                store.yaburu_store_id if store else None
            )
        except:
            return "Marchand", "votre boutique", None

    async def _load_history(self, db, conversation_id, user_id):
        try:
            res = await db.execute(select(ConversationHistory).where(ConversationHistory.conversation_id == conversation_id))
            record = res.scalar_one_or_none()
            if record and record.full_context:
                msgs = messages_from_dict(json.loads(record.full_context))
                return msgs[-settings.AGENT_MAX_HISTORY:]
        except: pass
        return []

    async def _save_history(self, db, conversation_id, user_id, messages):
        try:
            json_data = json.dumps(messages_to_dict(messages))
            res = await db.execute(select(ConversationHistory).where(ConversationHistory.conversation_id == conversation_id))
            record = res.scalar_one_or_none()
            if record: record.full_context = json_data
            else: db.add(ConversationHistory(conversation_id=conversation_id, user_id=user_id, full_context=json_data))
            await db.commit()
        except Exception as e:
            logger.error(f"Error saving history: {e}")

# Instance unique pour l'application
agent_service = CustomAgentExecutor()

