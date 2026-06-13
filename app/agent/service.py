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
from app.models.messages import Message
from app.models.user import User
from app.models.stores import store as StoreModel
from app.models.conversations import Conversation
from sqlalchemy import select
from app.agent.context import phone_number_ctx
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
                "stores_list": lambda x: x.get("stores_list", "- Aucune boutique active"),
                "session_summary": lambda x: x.get("session_summary", "Aucun résumé précédent.")
            }
            | agent_prompt
            | self.llm
        )

    async def get_response(self, text: str, conversation_id: str, user_id: str, phone: str = None,
                    image: Optional[dict] = None) -> str:
        """Méthode d'entrée pour obtenir une réponse de l'agent."""
        """Alias pour invoke() pour compatibilité avec le reste de l'application."""
        return await self.invoke(text, conversation_id, user_id, phone, image)

    async def invoke(self, input_text: str, conversation_id: str, user_id: str, phone: str = None, image: Optional[dict] = None) -> str:
        if phone:
            phone_number_ctx.set(phone)

        # 1. Chargement contexte en parallèle
        # Chaque méthode ouvre sa propre session DB indépendante (sécurité asyncio.gather)
        (user_name, stores_list), chat_history, session_summary = await asyncio.gather(
            self._get_context_info(user_id),
            self._load_history(conversation_id),
            self._get_session_summary(conversation_id)
        )

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
                        "stores_list": stores_list,
                        "session_summary": session_summary
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

    async def _get_context_info(self, user_id):
        """Ouvre sa propre session pour récupérer l'utilisateur et ses boutiques."""
        try:
            async with AsyncSessionLocal() as db:
                u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                
                result = await db.execute(select(User).where(User.id == u_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return "Marchand", "- Aucune boutique"
                
                stores_res = await db.execute(select(StoreModel).where(StoreModel.utilisateur_id == u_id))
                stores = stores_res.scalars().all()
                
                if not stores:
                    stores_list = "- Aucune boutique active"
                else:
                    stores_list = "\n".join([f"- Nom: {s.store_name} (yaburu_boutique_id: {s.yaburu_store_id})" for s in stores])
                    
                return (user.first_name if user.first_name else "Marchand", stores_list)
        except Exception as e:
            logger.error(f"Error in _get_context_info: {e}")
            return "Marchand", "- Erreur de chargement"

    async def generate_summary(self, conversation_id: str) -> str:
        """Génère un résumé d'une conversation en utilisant le LLM"""
        try:
            msgs = await self._load_history(conversation_id)
            if not msgs:
                return "Aucun résumé (conversation vide)."
            
            # Construire un prompt simple
            formatted_history = "\n".join([f"{'Marchand' if isinstance(m, HumanMessage) else 'Anna'}: {m.content}" for m in msgs])
            prompt = (
                "Voici l'historique de notre dernière conversation.\n"
                "Fais un résumé ultra-concis (max 3-4 lignes) des points importants (ce que le marchand a fait, "
                "ce qu'il a demandé, ce qui était en cours, les commandes traitées ou produits ajoutés). "
                "Ne réponds qu'avec le résumé, sans fioritures.\n\n"
                f"HISTORIQUE:\n{formatted_history}"
            )
            
            # Appel direct au LLM
            from langchain_core.messages import SystemMessage
            response = await self.llm.ainvoke([SystemMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"❌ Erreur generate_summary: {e}")
            return "Erreur lors de la génération du résumé."

    async def _get_session_summary(self, conversation_id):
        """Récupère le résumé stocké dans la table Conversation"""
        try:
            async with AsyncSessionLocal() as db:
                c_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
                res = await db.execute(select(Conversation).where(Conversation.id == c_id))
                conv = res.scalar_one_or_none()
                if conv and conv.resume_precedent:
                    return conv.resume_precedent
        except Exception as e:
            logger.error(f"❌ Erreur _get_session_summary: {e}")
        return "Aucun résumé précédent."

    async def _load_history(self, conversation_id):
        """Charge les N derniers messages depuis la table Message."""
        try:
            async with AsyncSessionLocal() as db:
                c_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
                res = await db.execute(
                    select(Message)
                    .where(Message.conversation_id == c_id)
                    .order_by(Message.date_creation.asc())
                )
                records = res.scalars().all()
                msgs = []
                for r in records[-settings.AGENT_MAX_HISTORY:]:
                    if r.role == "humain":
                        msgs.append(HumanMessage(content=r.contenu))
                    elif r.role == "agent":
                        msgs.append(AIMessage(content=r.contenu))
                return msgs
        except Exception as e:
            logger.error(f"❌ Erreur _load_history: {e}")
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
        # Ne sauvegarder que les 2 derniers messages pour éviter les doublons avec ce qui est déjà en DB
        new_messages = messages[-2:]
        try:
            c_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
            for msg in new_messages:
                role = "humain" if isinstance(msg, HumanMessage) else "agent"
                db.add(Message(conversation_id=c_id, role=role, contenu=msg.content))
            await db.commit()
            logger.info(f"💾 [HISTORY] 2 messages ajoutés à la conversation {conversation_id}")
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

