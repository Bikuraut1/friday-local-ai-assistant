"""
Open WebUI Tool: FRIDAY Memory Bridge

Import this file in Open WebUI's Tools area after the bridge is running.
It calls the local Phase 3 memory API at http://localhost:8765.
"""

import requests


class Tools:
    def __init__(self):
        self.base_url = "http://host.docker.internal:8765"

    def remember(self, fact: str, category: str = "PREFERENCES") -> str:
        """
        Store a durable user memory.
        Categories: USER_PROFILE, GOALS, PROJECTS, PREFERENCES, RELATIONSHIPS,
        DECISIONS_MADE, FOLLOW_UPS.
        """
        response = requests.post(
            f"{self.base_url}/memory",
            json={"text": fact, "category": category, "source": "open-webui-tool", "infer": False},
            timeout=30,
        )
        response.raise_for_status()
        return "Memory stored."

    def recall(self, query: str, category: str = "") -> str:
        """
        Search durable user memory.
        """
        payload = {"query": query, "top_k": 5}
        if category:
            payload["category"] = category
        response = requests.post(f"{self.base_url}/memory/search", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return "No matching memory found."
        return "\n".join(str(item.get("memory") or item.get("text") or item) for item in results)
