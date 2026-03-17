"""
BaseAgent - מחלקת בסיס לכל הסוכנים במערכת
כל סוכן יורש ממחלקה זו ומוסיף התנהגות ייחודית
"""

import os
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Callable
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BaseAgent(ABC):
    """מחלקת בסיס מופשטת לכל סוכני ה-AI במערכת הצמיגים"""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.model = MODEL
        self.system_prompt = system_prompt
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.history: list[dict] = []
        self._agent_caller: Optional[Callable[[str, str], str]] = None

    @classmethod
    def load_prompt(cls, filename: str) -> str:
        """טוען פרומפט מקובץ טקסט בתיקיית prompts/"""
        path = PROMPTS_DIR / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"קובץ פרומפט לא נמצא: {path}")

    def chat(self, user_message: str, keep_history: bool = True) -> str:
        """שולח הודעה לסוכן ומקבל תשובה, עם אפשרות לשמירת היסטוריה"""
        if keep_history:
            self.history.append({"role": "user", "content": user_message})
            messages = self.history
        else:
            messages = [{"role": "user", "content": user_message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=messages,
        )

        reply = response.content[0].text

        if keep_history:
            self.history.append({"role": "assistant", "content": reply})

        return reply

    def reset_history(self):
        """מאפס את היסטוריית השיחה"""
        self.history = []

    def ask_agent(self, agent_name: str, query: str) -> str:
        """שולח שאלה לסוכן אחר ומקבל תשובה"""
        if self._agent_caller is None:
            return f"[שגיאה: {self.name} אינו מחובר ל-Orchestrator]"
        try:
            return self._agent_caller(agent_name, query)
        except Exception as e:
            return f"[שגיאה בפנייה ל-{agent_name}: {e}]"

    @abstractmethod
    def run(self, user_input: str) -> str:
        """כל סוכן מממש את הלוגיקה הייחודית שלו כאן"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"
