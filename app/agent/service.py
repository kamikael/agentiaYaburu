import asyncio
import logging
import json
import uuid
from typing import Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, messages_to_dict, messages_from_dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSerializable
from sqlalchemy.ext.asyncio import AsyncSession
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
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        # Références aux tâches de fond pour éviter que le GC les détruise avant exécution
        self._background_tasks: set = set()
        # On lie les outils au modèle
        self.llm = ChatOpenAI(
            model=settings.GEMINI_MODEL,
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base=settings.OPENROUTER_URL,
            temperature=settings.GEMINI_TEMPERATURE,
            max_tokens=settings.GEMINI_MAX_TOKENS
        ).bind_tools(TOOL_LIST, tool_choice="auto")
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

    async def get_response(self, text: str, store_id: str, conversation_id: str, user_id: str, phone: str = None,
                    image: Optional[dict] = None) -> str:
        """Méthode d'entrée pour obtenir une réponse de l'agent."""
        """Alias pour invoke() pour compatibilité avec le reste de l'application."""
        return await self.invoke(text, store_id, conversation_id, user_id, phone, image)

    async def invoke(self, input_text: str, store_id: str, conversation_id: str, user_id: str, phone: str = None, image: Optional[dict] = None) -> str:
        # ContextVar pour que les outils accèdent aux infos sans paramètre LLM
        store_id_ctx.set(store_id)
        if phone:
            phone_number_ctx.set(phone)

        # 1. Chargement contexte en parallèle
        # Chaque méthode ouvre sa propre session DB indépendante (sécurité asyncio.gather)
        (user_name, store_name, yaburu_store_id), chat_history = await asyncio.gather(
            self._get_context_info(user_id, store_id),
            self._load_history(conversation_id)
        )
        if yaburu_store_id:
            yaburu_store_id_ctx.set(yaburu_store_id)

        agent_scratchpad = []
        iterations = 0
        MAX_LLM_RETRIES = 3

        while iterations < self.max_iterations:
            iterations += 1

            # Appel LLM avec retry automatique sur erreur 429 (rate limit)
            prediction = None
            for attempt in range(MAX_LLM_RETRIES):
                try:
                    prediction = await self.agent.ainvoke({
                        "input": input_text,
                        "chat_history": chat_history,
                        "agent_scratchpad": agent_scratchpad,
                        "user_name": user_name,
                        "store_name": store_name
                    })
                    break  # Succès, on sort du retry
                except Exception as e:
                    err_str = str(e)
                    is_rate_limit = "429" in err_str or "rate limit" in err_str.lower() or "provider returned error" in err_str.lower()
                    if is_rate_limit and attempt < MAX_LLM_RETRIES - 1:
                        wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s
                        logger.warning(f"⚠️ [LLM] Rate limit (429) — retry {attempt + 1}/{MAX_LLM_RETRIES - 1} dans {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Erreur définitive ou non-429
                        logger.error(f"❌ [LLM] Erreur définitive après {attempt + 1} tentative(s) : {e}")
                        return "⏳ Le service est temporairement surchargé. Veuillez réessayer dans quelques secondes."

            if prediction is None:
                return "⏳ Le service est temporairement surchargé. Veuillez réessayer dans quelques secondes."

            logger.debug(f"🤖 [Iteration {iterations}] LLM output: {prediction}")

            if not prediction.tool_calls:
                # Réponse directe du LLM (tool_choice="auto") — sauvegarder l'historique aussi
                self._schedule_history_save(conversation_id, user_id, chat_history, input_text, prediction.content)
                return prediction.content

            agent_scratchpad.append(prediction)

            # Traitement des appels d'outils
            
            # 1. Priorité au final_answer (arrêt immédiat)
            final_answer_call = next((tc for tc in prediction.tool_calls if tc["name"] == "final_answer"), None)
            if final_answer_call:
                final_text = final_answer_call["args"].get("answer", "Erreur: pas de réponse générée.")
                self._schedule_history_save(conversation_id, user_id, chat_history, input_text, final_text)
                return final_text

            # 2. Exécution parallèle de tous les autres outils pour plus de rapidité
            async def run_and_format_tool(tool_call):
                call_id = tool_call["id"]
                tool_result = await self._execute_tool(tool_call["name"], tool_call["args"])
                return ToolMessage(content=str(tool_result), tool_call_id=call_id)
            
            tool_messages = await asyncio.gather(*(run_and_format_tool(tc) for tc in prediction.tool_calls))
            agent_scratchpad.extend(tool_messages)
        return "Désolé, j'ai atteint ma limite de réflexion veillez reposer votre question de manière plus concise ou essayez de nouveau."

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

    async def _get_context_info(self, user_id, store_id):
        """Ouvre sa propre session pour être sûr avec asyncio.gather."""
        try:
            async with AsyncSessionLocal() as db:
                u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                s_id = uuid.UUID(store_id) if isinstance(store_id, str) else store_id
                
                # Exécution d'une seule requête avec JOIN pour de meilleures performances
                result = await db.execute(
                    select(User.first_name, StoreModel.store_name, StoreModel.yaburu_store_id)
                    .join(StoreModel, StoreModel.utilisateur_id == User.id)
                    .where(User.id == u_id, StoreModel.id == s_id)
                )
                row = result.first()
                if row:
                    return (
                        row.first_name if row.first_name else "Marchand",
                        row.store_name if row.store_name else "votre boutique",
                        row.yaburu_store_id
                    )
                return "Marchand", "votre boutique", None
        except Exception as e:
            logger.error(f"Error in _get_context_info: {e}")
            return "Marchand", "votre boutique", None

    async def _load_history(self, conversation_id):
        """Ouvre sa propre session pour être sûr avec asyncio.gather."""
        try:
            async with AsyncSessionLocal() as db:
                res = await db.execute(select(ConversationHistory).where(ConversationHistory.conversation_id == conversation_id))
                record = res.scalar_one_or_none()
                if record and record.full_context:
                    msgs = messages_from_dict(json.loads(record.full_context))
                    return msgs[-settings.AGENT_MAX_HISTORY:]
        except: pass
        return []

    def _schedule_history_save(self, conversation_id: str, user_id: str, chat_history: list, input_text: str, response_text: str):
        """
        Planifie la sauvegarde de l'historique en arrière-plan de manière sûre.
        Garde une référence forte à la tâche pour éviter que le GC la détruise
        avant qu'elle s'exécute (comportement documenté de asyncio.create_task).
        """
        updated_history = chat_history + [HumanMessage(content=input_text), AIMessage(content=response_text)]
        task = asyncio.create_task(self._save_history_bg(conversation_id, user_id, updated_history))
        self._background_tasks.add(task)
        # Retirer la référence automatiquement quand la tâche est terminée
        task.add_done_callback(self._background_tasks.discard)

    async def _save_history(self, db, conversation_id, user_id, messages):
        try:
            json_data = json.dumps(messages_to_dict(messages))
            res = await db.execute(select(ConversationHistory).where(ConversationHistory.conversation_id == conversation_id))
            record = res.scalar_one_or_none()
            if record:
                record.full_context = json_data
            else:
                db.add(ConversationHistory(conversation_id=conversation_id, full_context=json_data))
            await db.commit()
            logger.info(f"💾 [HISTORY] Historique sauvegardé pour conversation {conversation_id}")
        except Exception as e:
            logger.error(f"❌ [HISTORY] Erreur sauvegarde : {e}")

    async def _save_history_bg(self, conversation_id, user_id, messages):
        """
        Version background de _save_history : ouvre sa propre session DB.
        Appelée via _schedule_history_save() avec référence forte gardée.
        """
        try:
            async with AsyncSessionLocal() as db:
                await self._save_history(db, conversation_id, user_id, messages)
        except Exception as e:
            logger.error(f"❌ [HISTORY] Erreur sauvegarde en arrière-plan : {e}")

# Instance unique pour l'application
agent_service = CustomAgentExecutor()

