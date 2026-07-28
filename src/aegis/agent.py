from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RoutedCommand:
    command: str
    args: dict = field(default_factory=dict)
    confidence: float = 1.0
    raw: str = ""

    def to_args_list(self) -> list[str]:
        parts = [self.command]
        for k, v in self.args.items():
            if k == "ns":
                parts.extend(["-n", str(v)])
            elif k == "item_id":
                parts.extend(["-i", str(v)])
            elif k == "path":
                parts.extend(["-P", str(v)])
            elif k == "passphrase":
                parts.extend(["-p", str(v)])
            elif k == "length":
                parts.extend(["-l", str(v)])
            elif k == "framework":
                parts.extend(["-f", str(v)])
            elif k == "format":
                parts.extend(["-F", str(v)])
            elif k == "user":
                parts.extend(["-u", str(v)])
            elif k == "infile":
                parts.extend(["-i", str(v)])
            elif k == "outfile":
                parts.extend(["-o", str(v)])
            elif k == "count":
                parts.extend(["-n", str(v)])
            elif k == "clip":
                if v:
                    parts.append("--clip")
            elif k == "long":
                if v:
                    parts.append("--long")
            elif k == "yes":
                if v:
                    parts.append("-y")
            elif k == "data":
                parts.extend(["--kv", str(v)])
            elif k == "kv":
                for pair in v:
                    parts.extend(["--kv", str(pair)])
        return parts


_PATTERNS: list[tuple[str, str, list[tuple[str, object]]]] = []


def _p(pattern: str, command: str, *args: tuple[str, object]):
    _PATTERNS.append((pattern, command, list(args)))


# ── list ──────────────────────────────────────────────────────────────

_p(r"(?:list|show|display|enumerate) (?:all )?(?:my )?passwords?", "list")
_p(r"(?:list|show) (?:all )?(?:my |the )?(?:entries|items|credentials|secrets)", "list")
_p(r"(?:list|show) (?:everything )?in (?:the )?vault", "list")
_p(r"what (?:do I|have I) (?:have |saved )?(?:saved|stored)?", "list")
_p(r"all (?:my )?(?:passwords|entries|items|credentials)", "list")
_p(r"vault (?:contents|entries|items)", "list")
_p(r"show (?:my )?vault", "list")

# ── save ──────────────────────────────────────────────────────────────

_p(r"save (?:my |the )?(.+) password", "save", ("item_id", 1))
_p(r"save (?:my |the )?(.+)", "save", ("item_id", 1))
_p(r"store (?:my |the )?(.+) (?:password|credential|login)", "save", ("item_id", 1))
_p(r"store (?:my |the )?(.+)", "save", ("item_id", 1))
_p(r"add (?:a )?(.+) to (?:the )?vault", "save", ("item_id", 1))
_p(r"new (?:entry|item|credential) (.+)", "save", ("item_id", 1))

# ── load ──────────────────────────────────────────────────────────────

_p(r"(?:get|show|load|retrieve|view|open|fetch|what is|what's) (?:my |the )?(.+) (?:password|credential|login)", "load", ("item_id", 1))
_p(r"(?:get|load|retrieve|view|open|fetch) (?:my |the )?(.+)", "load", ("item_id", 1))
_p(r"(?:get|show|load) (?:my |the )?(.+) password", "load", ("item_id", 1))
_p(r"what(?:'s| is) my (.+) password", "load", ("item_id", 1))
_p(r"(?:get|show) me (?:my |the )?(.+)", "load", ("item_id", 1))
_p(r"password for (.+)", "load", ("item_id", 1))

# ── canary ────────────────────────────────────────────────────────────

_p(r"(?:check|scan) (?:for )?(?:ransomware|canar(?:y|ies))", "canary check")
_p(r"(?:deploy|place|create) canar(?:y|ies)", "canary deploy")
_p(r"(?:remove|delete) canar(?:y|ies)", "canary remove")

# ── delete ────────────────────────────────────────────────────────────

_p(r"(?:delete|remove|wipe|erase) (?:my |the )?(.+) (?:password|credential|entry|item)", "delete", ("item_id", 1))
_p(r"(?:delete|remove|wipe|erase) (?:my |the )?(.+)", "delete", ("item_id", 1))

# ── verify ────────────────────────────────────────────────────────────

_p(r"(?:check|verify|validate) (?:vault )?(?:integrity|health|status)", "verify")
_p(r"(?:vault )?(?:integrity|health) check", "verify")
_p(r"is (?:my )?vault (?:safe|intact|secure|ok|fine)", "verify")

# ── generate ──────────────────────────────────────────────────────────

_p(r"(?:generate|create|make|give me) (?:a )?(?:new )?password", "generate")
_p(r"(?:generate|create|make) (?:a )?(\d+)[ -]?char(?:acter)? password", "generate", ("length", 1))
_p(r"password (?:generator|please|for me)", "generate")
_p(r"(?:I need|need|want) (?:a )?(?:new )?password", "generate")

# ── encrypt / decrypt ─────────────────────────────────────────────────

_p(r"encrypt (?:the )?file (.+)", "encrypt", ("infile", 1))
_p(r"encrypt (?:the )?folder (.+)", "encrypt", ("infile", 1))
_p(r"decrypt (?:the )?file (.+)", "decrypt", ("infile", 1))
_p(r"decrypt (?:the )?archive (.+)", "decrypt", ("infile", 1))

# ── audit ─────────────────────────────────────────────────────────────

_p(r"(?:show|view) (?:the )?audit (?:log|trail|history)", "audit show")
_p(r"audit (?:log|trail|history)", "audit show")

# ── report ────────────────────────────────────────────────────────────

_p(r"(?:generate|create|show) (?:a )?(?:compliance )?report", "report generate")
_p(r"(?:soc2|soc 2) report", "report generate", ("framework", "soc2"))
_p(r"(?:hipaa) report", "report generate", ("framework", "hipaa"))
_p(r"(?:gdpr) report", "report generate", ("framework", "gdpr"))
_p(r"(?:iso.?27001) report", "report generate", ("framework", "iso27001"))

# ── vaults ────────────────────────────────────────────────────────────

_p(r"(?:list|show) (?:registered )?vaults", "vaults list")
_p(r"(?:register|add) vault (.+)", "vaults add", ("path", 1))
_p(r"(?:remove|delete) vault (.+)", "vaults remove", ("name", 1))


def _strip_article(text: str) -> str:
    return re.sub(r"^(?:a |an |the |my )", "", text, flags=re.IGNORECASE).strip()


class SealAgent:
    """Routes natural language to Seal CLI commands.

    The agent never sees decrypted data. It maps natural language
    to structured command dicts that a caller can execute.

    Model-first: tries SmolLM2-135M-Instruct via transformers,
    then falls back to rule-based pattern matching.
    """

    _SYSTEM_PROMPT = (
        "You are a command router for Seal, an encrypted vault CLI tool.\n"
        "Given a user's natural language request, output a JSON object mapping\n"
        "it to the correct CLI command. Output ONLY valid JSON, no explanation.\n\n"
        "Available commands and their arguments:\n"
        '- save: {"command":"save","args":{"item_id":"...","ns":"...","kv":["key=val"]}}\n'
        '- load: {"command":"load","args":{"item_id":"...","ns":"..."}}\n'
        '- list: {"command":"list","args":{}}\n'
        '- delete: {"command":"delete","args":{"item_id":"...","ns":"..."}}\n'
        '- generate: {"command":"generate","args":{"length":24}}\n'
        '- verify: {"command":"verify","args":{}}\n'
        '- encrypt: {"command":"encrypt","args":{"infile":"..."}}\n'
        '- decrypt: {"command":"decrypt","args":{"infile":"..."}}\n'
        '- canary check: {"command":"canary check","args":{}}\n'
        '- canary deploy: {"command":"canary deploy","args":{}}\n'
        '- canary remove: {"command":"canary remove","args":{}}\n'
        '- audit show: {"command":"audit show","args":{}}\n'
        '- report generate: {"command":"report generate","args":{"framework":"soc2|hipaa|gdpr|iso27001"}}\n'
        '- vaults list: {"command":"vaults list","args":{}}\n'
        '- doctor: {"command":"doctor","args":{}}\n'
    )

    def __init__(self, *, model_name: str = "HuggingFaceTB/SmolLM2-135M-Instruct"):
        self._model_name = model_name
        self._model = None
        self._tokenizer = None
        self._model_loaded = False

    def _load_model(self):
        if self._model_loaded:
            return
        self._model_loaded = True
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForCausalLM.from_pretrained(self._model_name)
            self._model.eval()
        except Exception:
            self._model = None
            self._tokenizer = None

    def route(self, text: str) -> RoutedCommand:
        text = text.strip()
        if not text:
            return RoutedCommand(command="help", raw=text, confidence=0.0)

        lower = text.lower().strip()

        # 1. try LLM (model-first)
        result = self._route_llm(text)
        if result is not None:
            return result

        # 2. fallback to rule-based patterns
        result = self._route_rules(lower)
        if result is not None:
            return result

        return RoutedCommand(
            command="unknown",
            args={"input": text},
            confidence=0.0,
            raw=text,
        )

    def _route_rules(self, lower: str) -> Optional[RoutedCommand]:
        for pattern, command, extractors in _PATTERNS:
            m = re.search(pattern, lower, re.IGNORECASE)
            if not m:
                continue

            args: dict = {}
            confidence = 1.0
            for key, idx in extractors:
                if isinstance(idx, int) and idx <= len(m.groups()):
                    val = m.group(idx)
                    if val is not None:
                        val = _strip_article(val).strip()
                        if key == "length":
                            try:
                                val = int(val)
                            except (ValueError, TypeError):
                                continue
                        args[key] = val
                elif isinstance(idx, (str, int)):
                    args[key] = idx

            return RoutedCommand(
                command=command,
                args=args,
                confidence=confidence,
                raw=lower,
            )
        return None

    def _route_llm(self, text: str) -> Optional[RoutedCommand]:
        self._load_model()
        if self._model is None or self._tokenizer is None:
            return None

        try:
            import torch
            import json as _json

            messages = [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ]

            input_text = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
            inputs = self._tokenizer(input_text, return_tensors="pt")

            with torch.no_grad():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=128,
                    do_sample=False,
                    temperature=1.0,
                )

            # decode only new tokens (exclude prompt)
            new_tokens = output[0][inputs["input_ids"].shape[1]:]
            response = self._tokenizer.decode(new_tokens, skip_special_tokens=True)

            # extract JSON from response
            match = re.search(r'\{[^{}]*"command"[^{}]*\}', response, re.DOTALL)
            if not match:
                return None

            parsed = _json.loads(match.group())
            command = parsed.get("command", "unknown")
            args = parsed.get("args", {})
            return RoutedCommand(
                command=command,
                args=args,
                confidence=0.7,
                raw=text,
            )
        except Exception:
            return None

    def execute(self, text: str) -> RoutedCommand:
        """Route and return the command with a full CLI args list."""
        cmd = self.route(text)
        return cmd
