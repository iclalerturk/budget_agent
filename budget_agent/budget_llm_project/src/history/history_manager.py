import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class HistoryManager:
    def __init__(self, filepath: str = ".venv\\budget_llm_project\\src\\history\\history.jsonl"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        # Touch file if not exists
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as _:
                pass

    def append(self, question: str, instruction_json: str, result: Any, final_answer: str, extra: Optional[Dict[str, Any]] = None) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "question": question,
            "instruction": instruction_json,
            "result": result,
            "answer": final_answer,
        }
        if extra:
            record.update(extra)
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read_all(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if not os.path.exists(self.filepath):
            return items
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return items

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        items = self._read_all()
        if limit is not None:
            return items[-limit:]
        return items

    def get_last(self, n: int = 20) -> List[Dict[str, Any]]:
        return self.get_all(limit=n)


